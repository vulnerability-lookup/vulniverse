"""Proxy to an ML-Gateway instance (github.com/vulnerability-lookup/ML-Gateway).

The gateway's classify endpoints are unauthenticated and it must not be
exposed publicly, so the browser never calls it: these functions run
behind Vulniverse's login and return only the fields the editor shows.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx

from ..app_config import CONFIG_PATH, SAMPLE_CONFIG_PATH


@dataclass(frozen=True)
class MlGatewayConfig:
    enabled: bool
    api_url: str
    timeout_seconds: int


@lru_cache(maxsize=1)
def get_ml_gateway_config() -> MlGatewayConfig:
    path = CONFIG_PATH if CONFIG_PATH.exists() else SAMPLE_CONFIG_PATH

    with path.open("rb") as file:
        config = tomllib.load(file)

    settings = config.get("panels", {}).get("ml-gateway", {})
    api_url = str(settings.get("api_url", "")).rstrip("/")

    return MlGatewayConfig(
        # Off unless configured: the gateway is a service the server owner
        # has to run, unlike the panels that work out of the box.
        enabled=isinstance(settings, dict)
        and bool(settings.get("enabled", False))
        and bool(api_url),
        api_url=api_url,
        timeout_seconds=int(settings.get("timeout_seconds", 30)),
    )


class MlGatewayBusy(RuntimeError):
    """The gateway's inference queue is full (its 503); worth retrying."""


def _call(path: str, body: dict[str, Any]) -> dict[str, Any]:
    config = get_ml_gateway_config()

    if not config.enabled:
        raise RuntimeError("The ML gateway is disabled")

    try:
        response = httpx.post(
            f"{config.api_url}{path}",
            json=body,
            timeout=config.timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("The ML gateway did not respond in time") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Could not reach the ML gateway") from exc

    if response.status_code == 503:
        raise MlGatewayBusy("The ML gateway is busy, try again shortly")

    if response.status_code != 200:
        raise RuntimeError(
            f"The ML gateway request failed with status {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError("The ML gateway returned an invalid response") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("The ML gateway returned an invalid response")  # noqa: TRY004

    # Model errors come back as 200 with a message in "error".
    if payload.get("error"):
        raise RuntimeError(f"The ML gateway failed: {payload['error']}")

    return payload


def classify_severity(description: str) -> dict[str, Any]:
    payload = _call("/classify/severity", {"description": description})

    severity = payload.get("severity")
    confidence = payload.get("confidence")

    if not isinstance(severity, str) or not isinstance(confidence, (int, float)):
        raise RuntimeError("The ML gateway returned an invalid response")  # noqa: TRY004

    return {
        "severity": severity,
        "confidence": float(confidence),
        "model": payload.get("model"),
    }


def classify_attack_techniques(description: str, top_k: int) -> dict[str, Any]:
    payload = _call(
        "/classify/attack-techniques",
        {"description": description, "top_k": top_k},
    )

    techniques = payload.get("techniques")

    if not isinstance(techniques, list):
        raise RuntimeError("The ML gateway returned an invalid response")  # noqa: TRY004

    results = []

    for item in techniques:
        if not (
            isinstance(item, dict)
            and isinstance(item.get("technique"), str)
            and isinstance(item.get("score"), (int, float))
        ):
            raise RuntimeError("The ML gateway returned an invalid response")  # noqa: TRY004

        results.append(
            {
                "id": item["technique"],
                "name": item.get("name") if isinstance(item.get("name"), str) else "",
                "score": float(item["score"]),
                "predicted": bool(item.get("predicted", item["score"] >= 0.5)),
            }
        )

    return {"techniques": results, "model": payload.get("model")}
