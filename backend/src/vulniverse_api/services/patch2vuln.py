from __future__ import annotations

import json
import os
import time
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

from ..app_config import CONFIG_PATH, SAMPLE_CONFIG_PATH

JOBS_PATH = "/api/v1/jobs"

# Submitting a job and polling its status are small, fast calls against
# patch2vuln's own queue, regardless of how long the analysis itself takes
# — these should never block for long. Only fetching a result after
# patch2vuln reports the job succeeded could plausibly be slow (a large
# generated record), so it alone uses the full configured timeout.
REQUEST_TIMEOUT_SECONDS = 10

TERMINAL_STATUSES = {"completed", "failed"}
POLL_INTERVAL_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 15

# patch2vuln's own job-status vocabulary, mapped to the one Vulniverse's
# frontend already speaks (see contracts.ts's BackgroundJobStatus).
STATUS_MAP = {
    "queued": "queued",
    "running": "running",
    "succeeded": "completed",
    "failed": "failed",
    "canceled": "failed",
}


@dataclass(frozen=True)
class Patch2VulnConfig:
    enabled: bool
    api_url: str
    api_token: str | None
    timeout_seconds: int
    models: tuple[str, ...] = field(default_factory=tuple)


@lru_cache(maxsize=1)
def get_patch2vuln_config() -> Patch2VulnConfig:
    path = CONFIG_PATH if CONFIG_PATH.exists() else SAMPLE_CONFIG_PATH

    with path.open("rb") as file:
        config = tomllib.load(file)

    settings = config.get("panels", {}).get("patch2vuln", {})

    models = settings.get("models", [])

    return Patch2VulnConfig(
        enabled=bool(settings.get("enabled", False)),
        api_url=str(settings.get("api_url", "")).rstrip("/"),
        # A secret: prefer an env var over the committed/shared TOML file,
        # same override pattern the old `executable` key used for its own
        # (non-secret) deployment-specific path.
        api_token=os.environ.get(
            "PATCH2VULN_API_TOKEN",
            settings.get("api_token") or None,
        ),
        timeout_seconds=int(settings.get("timeout_seconds", 300)),
        models=tuple(models) if isinstance(models, list) else (),
    )


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None

    message = None

    if isinstance(payload, dict):
        error = payload.get("error")

        if isinstance(error, dict):
            message = error.get("message")

    if isinstance(message, str) and message:
        return message

    return f"patch2vuln request failed with status {response.status_code}"


def _auth_headers(config: Patch2VulnConfig) -> dict[str, str]:
    if config.api_token:
        return {"Authorization": f"Bearer {config.api_token}"}

    return {}


def _build_job_body(
    sources: list[str],
    patches: list[bytes],
    context: dict[str, str],
    config: Patch2VulnConfig,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "patches": [patch.decode("utf-8") for patch in patches],
        "urls": sources,
    }

    # Maps Vulniverse's own camelCase context keys (see api/patch2vuln.py)
    # to the web service's snake_case ones. versionType has no equivalent
    # on the web service's side (not in its documented request schema),
    # so it's deliberately dropped rather than forwarded — the service
    # rejects unknown JSON properties outright.
    field_names = {
        "vendor": "vendor",
        "product": "product",
        "affectedVersion": "affected_version",
        "fixedVersion": "fixed_version",
    }

    for context_key, remote_key in field_names.items():
        value = context.get(context_key)

        if value:
            body[remote_key] = value

    if config.models:
        body["models"] = list(config.models)

    return body


def submit_job(
    sources: list[str],
    patches: list[bytes],
    context: dict[str, str],
) -> dict[str, Any]:
    """Queue a patch2vuln analysis job.

    Returns {"jobId": <patch2vuln's own id>, "status": "queued"}. Callers
    are responsible for mapping the real job id to whatever identifier
    they hand back to their own client (see api/patch2vuln.py's signed
    token, which keeps per-user ownership without any shared storage).
    """
    config = get_patch2vuln_config()

    if not config.enabled:
        raise RuntimeError("Patch2Vuln is disabled")

    if not sources and not patches:
        raise ValueError("No patch inputs provided")

    body = _build_job_body(sources, patches, context, config)

    try:
        response = httpx.post(
            f"{config.api_url}{JOBS_PATH}",
            json=body,
            headers=_auth_headers(config),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Patch2Vuln did not respond in time") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the Patch2Vuln service") from exc

    if response.status_code != 202:
        raise RuntimeError(_error_message(response))

    payload = response.json()
    job_id = payload.get("id")

    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError("Patch2Vuln did not return a job id")

    return {
        "jobId": job_id,
        "status": STATUS_MAP.get(payload.get("status"), "queued"),
    }


def get_job_status(job_id: str) -> dict[str, Any]:
    """Poll a patch2vuln job's status. Returns {"status": ...}."""
    config = get_patch2vuln_config()

    try:
        response = httpx.get(
            f"{config.api_url}{JOBS_PATH}/{job_id}",
            headers=_auth_headers(config),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Patch2Vuln did not respond in time") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the Patch2Vuln service") from exc

    if response.status_code == 404:
        raise LookupError("Patch2Vuln job not found")

    if response.status_code != 200:
        raise RuntimeError(_error_message(response))

    payload = response.json()

    return {"status": STATUS_MAP.get(payload.get("status"), "failed")}


def get_job_result(job_id: str) -> dict[str, Any]:
    """Fetch a succeeded patch2vuln job's result, reshaped to
    {"record": ..., "analysis": ...}, same validation the old synchronous
    call used to apply to its single response.
    """
    config = get_patch2vuln_config()

    try:
        response = httpx.get(
            f"{config.api_url}{JOBS_PATH}/{job_id}/result",
            headers=_auth_headers(config),
            timeout=config.timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Patch2Vuln did not respond in time") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the Patch2Vuln service") from exc

    if response.status_code == 404:
        raise LookupError("Patch2Vuln job not found")

    if response.status_code != 200:
        raise RuntimeError(_error_message(response))

    payload = response.json()
    records = payload.get("records")

    if not isinstance(records, dict):
        raise TypeError("Patch2Vuln response did not include any records")

    record = records.get("cve")

    if (
        not isinstance(record, dict)
        or record.get("dataType") != "CVE_RECORD"
        or record.get("dataVersion") != "5.2"
        or not isinstance(record.get("containers"), dict)
        or not isinstance(record["containers"].get("cna"), dict)
    ):
        raise RuntimeError("Invalid Patch2Vuln record")

    return {
        "record": record,
        "analysis": records.get("analysis"),
    }


def _format_status_event(job_id: str, status: str) -> str:
    payload = json.dumps({"jobId": job_id, "status": status})
    return f"event: status\ndata: {payload}\n\n"


def stream_job_status(token: str, job_id: str) -> Iterator[str]:
    """Poll patch2vuln's job status and relay changes as SSE events, keyed
    by the caller-facing token rather than the real patch2vuln job id
    (which never reaches the frontend). Replaces the old Redis-pubsub
    relay now that patch2vuln owns the job state — there's no worker
    process left to notify anyone of a change, so this polls instead.
    """
    yield "retry: 3000\n\n"

    try:
        status = get_job_status(job_id)["status"]
    except (RuntimeError, LookupError):
        status = "failed"

    yield _format_status_event(token, status)

    if status in TERMINAL_STATUSES:
        return

    last_status = status
    last_heartbeat = time.monotonic()

    while True:
        time.sleep(POLL_INTERVAL_SECONDS)

        try:
            status = get_job_status(job_id)["status"]
        except LookupError:
            status = "failed"
        except RuntimeError:
            # Transient — keep the connection open and retry on the next
            # tick rather than tearing down the stream over a blip.
            now = time.monotonic()

            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                yield ": heartbeat\n\n"
                last_heartbeat = now

            continue

        now = time.monotonic()

        if status != last_status:
            yield _format_status_event(token, status)
            last_status = status
            last_heartbeat = now
        elif now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            yield ": heartbeat\n\n"
            last_heartbeat = now

        if status in TERMINAL_STATUSES:
            return
