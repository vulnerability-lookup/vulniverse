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

TERMINAL_STATUSES = {"completed", "failed", "canceled"}
POLL_INTERVAL_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 15
# An open stream holds one request thread. Past this it ends even if the
# job hasn't (e.g. patch2vuln has no worker running), and the panel falls
# back to occasional polling, so a stuck job can't pile up busy threads.
STREAM_MAX_SECONDS = 600

# patch2vuln's own job-status vocabulary, mapped to the one Vulniverse's
# frontend already speaks (see contracts.ts's BackgroundJobStatus).
STATUS_MAP = {
    "queued": "queued",
    "running": "running",
    "succeeded": "completed",
    "failed": "failed",
    "canceled": "canceled",
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
    # to the web service's snake_case ones (its AnalysisRequest model).
    # osv_ecosystem only fills in the OSV output's package ecosystem; it
    # isn't shown to the model. package_url is, so it can change the
    # analysis itself.
    field_names = {
        "vendor": "vendor",
        "product": "product",
        "affectedVersion": "affected_version",
        "fixedVersion": "fixed_version",
        "versionType": "version_type",
        "packageUrl": "package_url",
        "osvEcosystem": "osv_ecosystem",
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

    result: dict[str, Any] = {"status": STATUS_MAP.get(payload.get("status"), "failed")}

    # patch2vuln reports this for queued/running jobs: false means no
    # worker is processing its queue, so the job won't progress.
    worker_available = payload.get("workerAvailable")

    if isinstance(worker_available, bool):
        result["workerAvailable"] = worker_available

    return result


def _drop_nulls(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_nulls(item) for key, item in value.items() if item is not None}

    if isinstance(value, list):
        return [_drop_nulls(item) for item in value if item is not None]

    return value


def _without_nulls(container: dict[str, Any], keep: str) -> dict[str, Any]:
    """patch2vuln emits null for fields it has no value for (e.g.
    affected[].collectionURL), but neither the CVE nor the OSV schema
    accepts null there, so applying them would make the record invalid.
    Absent is what "no value" means. `keep` names the one free-form
    key where null is allowed and left as-is: CVE's x_gcve (the
    patch2vuln extension's commit/subject) and OSV's database_specific.
    """
    return {
        key: value if key == keep else _drop_nulls(value)
        for key, value in container.items()
        if value is not None
    }


def cancel_job(job_id: str) -> dict[str, Any]:
    """Ask patch2vuln to cancel a job. Returns {"status": ...}: a queued
    job is "canceled" at once, a running one stays "running" until its
    worker stops. cancel_only keeps a job that finished in the meantime
    (and its result) instead of deleting it.
    """
    config = get_patch2vuln_config()

    try:
        response = httpx.delete(
            f"{config.api_url}{JOBS_PATH}/{job_id}",
            params={"cancel_only": "true"},
            headers=_auth_headers(config),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Patch2Vuln did not respond in time") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the Patch2Vuln service") from exc

    if response.status_code == 404:
        raise LookupError("Patch2Vuln job not found")

    if response.status_code not in (200, 202):
        raise RuntimeError(_error_message(response))

    return {"status": STATUS_MAP.get(response.json().get("status"), "failed")}


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

    record["containers"]["cna"] = _without_nulls(record["containers"]["cna"], "x_gcve")

    # Every response carries an OSV rendering of the same analysis, used
    # by the panel for OSV records. Missing or malformed is not fatal,
    # since CVE records don't need it.
    osv = records.get("osv")

    return {
        "record": record,
        "osv": _without_nulls(osv, "database_specific") if isinstance(osv, dict) else None,
        "analysis": records.get("analysis"),
    }


def _format_status_event(
    job_id: str,
    status: str | None,
    worker_available: bool | None = None,
    *,
    expired: bool = False,
    unreachable: str | None = None,
) -> str:
    data: dict[str, Any] = {"jobId": job_id, "status": status}

    if worker_available is not None:
        data["workerAvailable"] = worker_available

    if unreachable is not None:
        # patch2vuln can't be asked right now; the status is the last one
        # known and the client should show it as unknown until the next
        # event without this flag.
        data["unreachable"] = True
        data["error"] = unreachable

    if expired:
        # The stream is ending although the job isn't finished; the
        # client should poll from now on instead of reconnecting.
        data["expired"] = True

    return f"event: status\ndata: {json.dumps(data)}\n\n"


def stream_job_status(token: str, job_id: str) -> Iterator[str]:
    """Poll patch2vuln's job status and relay changes as SSE events, keyed
    by the caller-facing token rather than the real patch2vuln job id
    (which never reaches the frontend). Replaces the old Redis-pubsub
    relay now that patch2vuln owns the job state — there's no worker
    process left to notify anyone of a change, so this polls instead.
    """
    yield "retry: 3000\n\n"

    started = time.monotonic()

    # (status, workerAvailable) last sent; None until patch2vuln answered.
    last: tuple[str, bool | None] | None = None
    # The error last reported as "unreachable"; None while patch2vuln answers.
    unreachable: str | None = None

    try:
        state = get_job_status(job_id)
    except LookupError:
        state = {"status": "failed"}
    except RuntimeError as exc:
        # patch2vuln is unreachable right now. Not a reason to call the
        # job failed: report the status as unknown and let the loop below
        # retry, so the client keeps its last known status until the real one.
        state = None
        unreachable = str(exc)
        yield _format_status_event(token, None, unreachable=unreachable)

    if state is not None:
        last = (state["status"], state.get("workerAvailable"))

        yield _format_status_event(token, *last)

        if last[0] in TERMINAL_STATUSES:
            return

    last_heartbeat = time.monotonic()

    while True:
        time.sleep(POLL_INTERVAL_SECONDS)

        now = time.monotonic()

        if now - started >= STREAM_MAX_SECONDS:
            # Status null: patch2vuln was never reached during this stream.
            yield _format_status_event(
                token, *(last or (None, None)), expired=True, unreachable=unreachable,
            )
            return

        try:
            state = get_job_status(job_id)
        except LookupError:
            state = {"status": "failed"}
        except RuntimeError as exc:
            # Transient — keep the connection open and retry on the next
            # tick rather than tearing down the stream over a blip. Say so
            # once, so the client stops presenting the status as current.
            if unreachable is None:
                unreachable = str(exc)
                yield _format_status_event(token, *(last or (None, None)), unreachable=unreachable)
                last_heartbeat = now
            elif now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                yield ": heartbeat\n\n"
                last_heartbeat = now

            continue

        current = (state["status"], state.get("workerAvailable"))

        # Back in touch: an unchanged status still needs an event, to
        # clear the client's "unreachable" state.
        if current != last or unreachable is not None:
            yield _format_status_event(token, *current)
            last = current
            unreachable = None
            last_heartbeat = now
        elif now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            yield ": heartbeat\n\n"
            last_heartbeat = now

        if current[0] in TERMINAL_STATUSES:
            return
