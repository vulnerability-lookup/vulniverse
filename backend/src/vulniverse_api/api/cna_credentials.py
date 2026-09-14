from __future__ import annotations

from flask import request
from flask_login import current_user

from ..services.cna_credentials import (
    delete_credential,
    list_credentials,
    set_credential,
)
from ..services.cna_publication import KNOWN_TARGETS
from . import api_bp


@api_bp.get("/cna-credentials")
def get_cna_credentials() -> tuple[dict, int]:
    return list_credentials(current_user.id), 200


@api_bp.put("/cna-credentials/<string:target>")
def put_cna_credential(target: str) -> tuple[dict, int]:
    if target not in KNOWN_TARGETS:
        return {"message": f"Unknown publication target: {target!r}"}, 404

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    fields = {
        "cve_url": payload.get("cveUrl"),
        "short_name": payload.get("shortName"),
        "org_id": payload.get("orgId"),
        "cve_api_org": payload.get("cveApiOrg"),
        "cve_api_user": payload.get("cveApiUser"),
        "cve_api_key": payload.get("cveApiKey"),
    }

    try:
        set_credential(current_user.id, target, fields)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return list_credentials(current_user.id)[target], 200


@api_bp.delete("/cna-credentials/<string:target>")
def delete_cna_credential(target: str) -> tuple[dict, int]:
    if not delete_credential(current_user.id, target):
        return {"message": f"No credential configured for {target!r}."}, 404

    return {"message": "Deleted."}, 200
