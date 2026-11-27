from __future__ import annotations

from typing import Any

from flask import request

from ..services.ml_gateway import (
    MlGatewayBusy,
    classify_attack_techniques,
    classify_severity,
    get_ml_gateway_config,
)
from . import api_bp, require_panel

MAX_DESCRIPTION_LENGTH = 20_000
MAX_TOP_K = 20


def _read_description() -> str | tuple[dict[str, str], int]:
    body = request.get_json(silent=True)
    description = body.get("description") if isinstance(body, dict) else None

    if not isinstance(description, str) or not description.strip():
        return {"message": "description must be a non-empty string"}, 400

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return {"message": "description is too long"}, 413

    return description


def _run(call: Any, *args: Any) -> Any:
    if not get_ml_gateway_config().enabled:
        return {"message": "The ML gateway is not configured"}, 403

    try:
        return call(*args)
    except MlGatewayBusy as exc:
        return {"message": str(exc)}, 503
    except RuntimeError as exc:
        return {"message": str(exc)}, 502


@api_bp.post("/ml-gateway/severity")
@require_panel("ml-gateway")
def ml_gateway_severity():
    description = _read_description()

    if isinstance(description, tuple):
        return description

    return _run(classify_severity, description)


@api_bp.post("/ml-gateway/attack-techniques")
@require_panel("ml-gateway")
def ml_gateway_attack_techniques():
    description = _read_description()

    if isinstance(description, tuple):
        return description

    top_k = request.get_json(silent=True).get("topK", 10)

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or not 1 <= top_k <= MAX_TOP_K
    ):
        return {"message": f"topK must be an integer from 1 to {MAX_TOP_K}"}, 400

    return _run(classify_attack_techniques, description, top_k)
