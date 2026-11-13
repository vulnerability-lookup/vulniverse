from typing import Any

from flask import request

from ..services.csaf_convert import csaf_from_cve
from ..services.osv_convert import osv_from_cve
from . import api_bp

# Profiles whose records can be converted.
CVE_PROFILES = {"cve-5.2.0", "gcve-bcp-05-1.7"}

# Target format -> profile of the drafted record.
TARGET_PROFILES = {"csaf": "csaf-2.1", "osv": "osv-1.9.2"}


@api_bp.post("/convert/<string:target>")
def convert_record(target: str) -> tuple[dict, int]:
    """A CSAF 2.1 or OSV 1.9.2 draft from a CVE/GCVE record. Converts only,
    saves nothing: the editor creates the new record through /records.
    OSV takes an optional "ecosystem" for products without a package URL."""
    if target not in TARGET_PROFILES:
        return {"message": f"Unknown conversion target: {target!r}"}, 404

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    record = payload.get("record")
    profile = payload.get("profile")
    ecosystem = payload.get("ecosystem") or ""

    if not isinstance(record, dict):
        return {"message": "The 'record' property must be an object."}, 400

    if profile not in CVE_PROFILES:
        return {"message": f"Cannot convert a {profile!r} record."}, 400

    if not isinstance(ecosystem, str):
        return {"message": "The 'ecosystem' property must be a string."}, 400

    converted: dict[str, Any] = (
        osv_from_cve(record, ecosystem) if target == "osv" else csaf_from_cve(record)
    )

    return {"record": converted, "profile": TARGET_PROFILES[target]}, 200
