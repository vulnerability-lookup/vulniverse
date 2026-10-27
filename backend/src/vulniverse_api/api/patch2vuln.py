from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from flask import request
from flask_login import current_user
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job

from ..jobs.queue import get_queue, get_redis
from ..services.patch2vuln import get_patch2vuln_config, run_patch2vuln
from . import api_bp

MAX_PATCH_BYTES = 4 * 1024 * 1024
MAX_INPUTS = 5

COMMIT_PATH = re.compile(
    r"^/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)"
    r"/commit/([0-9a-fA-F]{7,64})(?:\.patch)?/?$"
)


def normalize_commit_url(value: str) -> str:
    url = urlsplit(value.strip())

    if (
        url.scheme != "https"
        or url.hostname != "github.com"
        or url.port is not None
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
    ):
        raise ValueError("Only GitHub commit URLs are supported")

    match = COMMIT_PATH.fullmatch(url.path)

    if match is None:
        raise ValueError("Invalid GitHub commit URL")

    owner, repo, commit = match.groups()

    return (
        f"https://github.com/{owner}/{repo}"
        f"/commit/{commit}.patch"
    )


@api_bp.post("/patch2vuln/jobs")
def create_patch2vuln_job():
    config = get_patch2vuln_config()

    if not config.enabled:
        return {"message": "Patch2Vuln is disabled"}, 403

    if (
        request.content_length is not None
        and request.content_length > MAX_PATCH_BYTES + 65536
    ):
        return {"message": "Request too large"}, 413

    try:
        commit_urls = json.loads(
            request.form.get("commitUrls", "[]")
        )
    except json.JSONDecodeError:
        return {"message": "Invalid commitUrls"}, 400

    if (
        not isinstance(commit_urls, list)
        or not all(isinstance(url, str) for url in commit_urls)
    ):
        return {"message": "commitUrls must be an array of strings"}, 400

    try:
        sources = [
            normalize_commit_url(url)
            for url in commit_urls
        ]
    except ValueError as exc:
        return {"message": str(exc)}, 400

    uploads = request.files.getlist("files")

    if len(sources) + len(uploads) == 0:
        return {"message": "At least one patch is required"}, 400

    if len(sources) + len(uploads) > MAX_INPUTS:
        return {"message": "Too many patch inputs"}, 400

    patches = []
    total_size = 0

    for uploaded in uploads:
        filename = uploaded.filename or ""

        if not filename.lower().endswith((".patch", ".diff")):
            return {"message": "Only .patch and .diff files are allowed"}, 400

        remaining = MAX_PATCH_BYTES - total_size
        content = uploaded.stream.read(remaining + 1)

        total_size += len(content)

        if total_size > MAX_PATCH_BYTES:
            return {"message": "Patch files too large"}, 413

        if not content:
            return {"message": "Empty patch file"}, 400

        patches.append(content)

    context = {}

    for field in (
        "vendor",
        "product",
        "affectedVersion",
        "fixedVersion",
        "versionType",
    ):
        value = request.form.get(field, "").strip()

        if len(value) > 200:
            return {"message": f"{field} is too long"}, 400

        if value:
            context[field] = value

    queue = get_queue("patch2vuln")

    try:
        job = queue.enqueue(
            run_patch2vuln,
            sources,
            patches,
            context,
            job_timeout=config.timeout_seconds + 60,
            result_ttl=86400,
            failure_ttl=3600,
            meta={
                "owner_id": str(current_user.get_id()),
            },
        )
    except RedisError:
        return {"message": "Analysis queue unavailable"}, 503

    return {
        "jobId": job.id,
        "status": "queued",
    }, 202


@api_bp.get("/patch2vuln/jobs/<string:job_id>")
def get_patch2vuln_job(job_id: str):
    try:
        job = Job.fetch(
            job_id,
            connection=get_redis(),
        )
    except NoSuchJobError:
        return {"message": "Job not found"}, 404
    except RedisError:
        return {"message": "Analysis queue unavailable"}, 503

    if job.meta.get("owner_id") != str(current_user.get_id()):
        return {"message": "Job not found"}, 404

    status = job.get_status(refresh=True)

    if status == "finished":
        return {
            "jobId": job.id,
            "status": "completed",
            "result": job.return_value(),
        }, 200

    if status == "failed":
        return {
            "jobId": job.id,
            "status": "failed",
            "error": "Patch analysis failed",
        }, 200

    if status == "started":
        return {
            "jobId": job.id,
            "status": "running",
        }, 200

    if status in ("canceled", "stopped"):
        return {
            "jobId": job.id,
            "status": "failed",
            "error": "Patch analysis was canceled",
        }, 200

    return {
        "jobId": job.id,
        "status": "queued",
    }, 200
