from __future__ import annotations

from typing import Any

from flask import request
from flask_login import current_user
from sqlalchemy import or_

from ..extensions import db
from ..models import VulnerabilityRecord
from ..services.record_validation import known_profiles, validate_record
from . import api_bp


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


def identifier_still_present(
    document: dict[str, Any],
    identifier: str,
) -> bool:
    """A record's identifier, once assigned at creation, is pinned to
    this row forever — but which of vulnId/cveId originally produced it
    doesn't matter after that. A record legitimately accumulates a
    second identifying field over its life (a GCVE record later gets an
    official cveId, or a cveId record picks up a vulnId when reserving
    through a GNA target), so update_record checks containment here
    rather than re-deriving "the" identifier via extract_identifier's
    vulnId-first preference — which would reject that entirely
    legitimate case as a fabricated identity change.
    """
    metadata = document.get("cveMetadata")

    if not isinstance(metadata, dict):
        return False

    return identifier in (metadata.get("vulnId"), metadata.get("cveId"))


def is_visible(record: VulnerabilityRecord) -> bool:
    """A draft is visible only to its own owner (or an admin); a
    published record is visible to any logged-in user, exactly like
    today's flat access model. Enforced on every read/write route
    below, not just the list — otherwise a non-owner who somehow
    knew/guessed an identifier could still reach a draft that isn't
    supposed to be visible to them at all.
    """
    if not record.is_draft:
        return True

    return current_user.is_admin or record.created_by_id == current_user.id


@api_bp.get("/records")
def list_records() -> tuple[dict, int]:
    query = VulnerabilityRecord.query

    if not current_user.is_admin:
        query = query.filter(
            or_(
                VulnerabilityRecord.is_draft.is_(False),
                VulnerabilityRecord.created_by_id == current_user.id,
            ),
        )

    # id DESC as a tiebreak: sqlite's CURRENT_TIMESTAMP only has
    # second-level precision, so two records created within the
    # same second would otherwise sort ambiguously.
    records = query.order_by(
        VulnerabilityRecord.updated_at.desc(),
        VulnerabilityRecord.id.desc(),
    ).all()

    return {
        "records": [
            {
                "identifier": record.identifier,
                "profile": record.profile,
                "isDraft": record.is_draft,
                "updatedAt": record.updated_at.isoformat(),
                "createdBy": record.created_by.email if record.created_by else None,
            }
            for record in records
        ],
    }, 200


@api_bp.get("/records/<string:identifier>")
def get_record(identifier: str) -> tuple[dict, int]:
    record = VulnerabilityRecord.query.filter_by(
        identifier=identifier,
    ).first()

    if record is None or not is_visible(record):
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
        created_by_id=current_user.id,
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

    if record is None or not is_visible(record):
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

    if not identifier_still_present(document, identifier):
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


@api_bp.delete("/records/<string:identifier>")
def delete_record(identifier: str) -> tuple[dict, int]:
    record = VulnerabilityRecord.query.filter_by(
        identifier=identifier,
    ).first()

    if record is None or not is_visible(record):
        return {"message": "Record not found."}, 404

    db.session.delete(record)
    db.session.commit()

    return {"identifier": identifier}, 200
