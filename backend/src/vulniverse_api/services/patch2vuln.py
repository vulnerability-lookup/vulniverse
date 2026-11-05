from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import httpx

from ..app_config import CONFIG_PATH, SAMPLE_CONFIG_PATH

ADVISORIES_PATH = "/api/v1/advisories"


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


def run_patch2vuln(
    sources: list[str],
    patches: list[bytes],
    context: dict[str, str],
) -> dict[str, Any]:
    config = get_patch2vuln_config()

    if not config.enabled:
        raise RuntimeError("Patch2Vuln is disabled")

    if not sources and not patches:
        raise ValueError("No patch inputs provided")

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

    headers = {}

    if config.api_token:
        headers["Authorization"] = f"Bearer {config.api_token}"

    try:
        response = httpx.post(
            f"{config.api_url}{ADVISORIES_PATH}",
            json=body,
            headers=headers,
            timeout=config.timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("Patch2Vuln analysis timed out") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the Patch2Vuln service") from exc

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
