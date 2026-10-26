from flask import request

from ..services.record_quality import (
    score_record_quality,
)
from . import api_bp

PROFILES = {"cve-5.2.0", "gcve-bcp-05-1.7"}


@api_bp.post("/record-quality")
def record_quality():
    payload = request.get_json()
    profile = payload.get("profile")
    if profile not in PROFILES:
        return {
            "message":
                "Record quality scoring is not "
                "supported for this profile.",
        }, 400

    record = payload.get("record")

    if not isinstance(record, dict):
        return {
            "message":
                "record must be an object.",
        }, 400

    return score_record_quality(
        record,
    ), 200
