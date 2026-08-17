from flask import request

from . import api_bp
from ..services.record_validation import known_profiles, validate_record


@api_bp.post("/validate")
def validate() -> tuple[dict, int]:
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    record = payload.get("record")
    profile = payload.get("profile", "cve-5.2.0")

    if not isinstance(record, dict):
        return {
            "message": "The 'record' property must be an object."
        }, 400

    if profile not in known_profiles():
        return {"message": f"Unknown profile: {profile!r}"}, 400

    errors = validate_record(record, profile)

    valid = not any(
        error.get("severity", "error") == "error"
        for error in errors
    )

    return {
        "valid": valid,
        "profile": profile,
        "errors": errors,
    }, 200
