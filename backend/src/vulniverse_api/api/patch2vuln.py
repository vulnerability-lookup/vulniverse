from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from flask import Response, current_app, request
from flask_login import current_user
from itsdangerous import BadSignature, URLSafeSerializer

from ..services.patch2vuln import (
    get_job_result,
    get_job_status,
    get_patch2vuln_config,
    stream_job_status,
    submit_job,
)
from . import api_bp, require_panel

MAX_PATCH_BYTES = 4 * 1024 * 1024
MAX_INPUTS = 5

# Salts the signed job token below (see _encode_job_token) — scopes it to
# this one purpose so it can never be replayed as a token meant for some
# other itsdangerous use of the same SECRET_KEY.
TOKEN_SALT = "patch2vuln-job"

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


def _serializer() -> URLSafeSerializer:
    secret_key = current_app.secret_key
    assert secret_key is not None, "SECRET_KEY must be configured"

    return URLSafeSerializer(secret_key, salt=TOKEN_SALT)


def _encode_job_token(job_id: str, owner_id: str) -> str:
    """Patch2Vuln's own job id, signed together with the submitting user's
    id. This is the "jobId" the frontend ever sees — it's opaque to it
    either way. Ownership (one user can't poll/read another's job) is
    enforced by verifying this signature rather than by looking anything
    up in shared storage, which is what let Redis/RQ's per-job metadata
    be retired along with the queue itself: nothing here needs state
    shared across the two gunicorn worker processes.
    """
    return _serializer().dumps({"id": job_id, "owner": owner_id})


def _decode_job_token(token: str) -> str:
    """Verify the token belongs to the current user and return the real
    patch2vuln job id. Raises LookupError — on a bad signature, a
    tampered owner, or simply someone else's valid token — so callers
    treat a forged/foreign token exactly like "job not found" and never
    confirm whether a given id is real.
    """
    try:
        payload = _serializer().loads(token)
    except BadSignature as exc:
        raise LookupError("Job not found") from exc

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("id"), str)
        or payload.get("owner") != str(current_user.get_id())
    ):
        raise LookupError("Job not found")

    return payload["id"]


@api_bp.post("/patch2vuln/jobs")
@require_panel("patch2vuln")
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

    try:
        job = submit_job(sources, patches, context)
    except ValueError as exc:
        return {"message": str(exc)}, 400
    except RuntimeError as exc:
        return {"message": str(exc)}, 502

    token = _encode_job_token(job["jobId"], str(current_user.get_id()))

    return {
        "jobId": token,
        "status": job["status"],
    }, 202


@api_bp.get("/patch2vuln/jobs/<string:token>")
@require_panel("patch2vuln")
def get_patch2vuln_job(token: str):
    try:
        job_id = _decode_job_token(token)
    except LookupError:
        return {"message": "Job not found"}, 404

    try:
        status = get_job_status(job_id)["status"]
    except LookupError:
        return {"message": "Job not found"}, 404
    except RuntimeError as exc:
        return {"message": str(exc)}, 502

    if status == "completed":
        try:
            result = get_job_result(job_id)
        except LookupError:
            return {"message": "Job not found"}, 404
        except (RuntimeError, TypeError):
            # The job itself succeeded, but relaying its result failed —
            # surface it the same way an analysis failure would be, since
            # the frontend only ever distinguishes "failed" from a result.
            return {
                "jobId": token,
                "status": "failed",
                "error": "Patch analysis failed",
            }, 200

        return {
            "jobId": token,
            "status": "completed",
            "result": result,
        }, 200

    if status == "failed":
        return {
            "jobId": token,
            "status": "failed",
            "error": "Patch analysis failed",
        }, 200

    return {
        "jobId": token,
        "status": status,
    }, 200


@api_bp.get("/patch2vuln/jobs/<string:token>/events")
@require_panel("patch2vuln")
def stream_patch2vuln_job_events(token: str):
    """Stream status updates for a patch2vuln job. Polls patch2vuln's own
    job status directly — there's no background worker process left to
    push notifications, so this is the relay instead.
    """
    try:
        job_id = _decode_job_token(token)
    except LookupError:
        return {"message": "Job not found"}, 404

    return Response(
        stream_job_status(token, job_id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
