from __future__ import annotations

from typing import Any

from flask import request

from . import api_bp
from ..extensions import db
from ..models import VulnerabilityRecord
from ..services.record_validation import known_profiles, validate_record


def has_blocking_errors(errors: list[dict[str, Any]]) -> bool:
    return any(
        error.get("severity", "error") == "error"
        for error in errors
    )


def extract_identifier(
    document: dict[str, Any],
) -> str | None:
    metadata = document.get("cveMetadata")

    if not isinstance(metadata, dict):
        return None

    identifier = (
        metadata.get("vulnId")
        or metadata.get("cveId")
    )

    return identifier if isinstance(identifier, str) else None


@api_bp.get("/records/<string:identifier>")
def get_record(identifier: str) -> tuple[dict, int]:
    record = VulnerabilityRecord.query.filter_by(
        identifier=identifier,
    ).first()

    if record is None:
        return {"message": "Record not found."}, 404

    return {
        "identifier": record.identifier,
        "profile": record.profile,
        "record": record.document,
        "isDraft": record.is_draft,
    }, 200


@api_bp.post("/records")
def create_record() -> tuple[dict, int]:
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    document = payload.get("record")
    profile = payload.get("profile", "cve-5.2.0")
    is_draft = bool(payload.get("isDraft", True))

    if not isinstance(document, dict):
        return {"message": "A record object is required."}, 400

    if profile not in known_profiles():
        return {"message": f"Unknown profile: {profile!r}"}, 400

    identifier = extract_identifier(document)

    if not identifier:
        return {"message": "The record has no identifier."}, 400

    existing = VulnerabilityRecord.query.filter_by(
        identifier=identifier,
    ).first()

    if existing:
        return {"message": "The record already exists."}, 409

    # Incomplete drafts should be saveable.
    if not is_draft:
        errors = validate_record(document, profile)

        if has_blocking_errors(errors):
            return {
                "message": "The record is not publishable.",
                "errors": errors,
            }, 422

    record = VulnerabilityRecord(
        identifier=identifier,
        profile=profile,
        document=document,
        is_draft=is_draft,
    )

    db.session.add(record)
    db.session.commit()

    return {
        "identifier": identifier,
        "profile": profile,
        "record": document,
        "isDraft": is_draft,
    }, 201


@api_bp.put("/records/<string:identifier>")
def update_record(identifier: str) -> tuple[dict, int]:
    record = VulnerabilityRecord.query.filter_by(
        identifier=identifier,
    ).first()

    if record is None:
        return {"message": "Record not found."}, 404

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    document = payload.get("record")
    profile = payload.get("profile", record.profile)
    is_draft = bool(payload.get("isDraft", record.is_draft))

    if not isinstance(document, dict):
        return {"message": "A record object is required."}, 400

    if profile not in known_profiles():
        return {"message": f"Unknown profile: {profile!r}"}, 400

    document_identifier = extract_identifier(document)

    if (
        document_identifier
        and document_identifier != identifier
    ):
        return {
            "message": "The record identifier cannot be changed.",
        }, 400

    if not is_draft:
        errors = validate_record(document, profile)

        if has_blocking_errors(errors):
            return {
                "message": "The record is not publishable.",
                "errors": errors,
            }, 422

    record.profile = profile
    record.document = document
    record.is_draft = is_draft

    db.session.commit()

    return {
        "identifier": identifier,
        "profile": profile,
        "record": document,
        "isDraft": is_draft,
    }, 200
