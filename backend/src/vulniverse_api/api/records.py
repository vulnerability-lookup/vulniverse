"""CRUD endpoints for vulnerability records.

Records are addressed by their database ``id``. The vulnerability identifier
(CVE/GCVE/OSV id) is read from the document according to its profile, and is
NULL for a draft that doesn't have one yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import request
from flask_login import current_user
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import CnaPublication, VulnerabilityRecord
from ..services.identifiers import extract_identifier, normalize_id_case
from ..services.profiles import known_profiles
from ..services.record_validation import validate_record
from . import api_bp

type ApiResponse = tuple[dict[str, Any], int]
DEFAULT_PROFILE = "cve-5.2.0"


@dataclass(frozen=True)
class RecordInput:
    """Validated fields accepted by the create and update endpoints."""

    document: dict[str, Any]
    profile: str
    is_draft: bool


# ---------------------------------------------------------------------------
# Request and publication validation
# ---------------------------------------------------------------------------


def read_record_input(
    *,
    default_profile: str = DEFAULT_PROFILE,
    default_is_draft: bool = True,
) -> RecordInput | ApiResponse:
    """Parse a record request or return a (JSON body, HTTP status) error."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    document = payload.get("record")
    profile = payload.get("profile", default_profile)
    is_draft = payload.get("isDraft", default_is_draft)

    if not isinstance(document, dict):
        return {"message": "A record object is required."}, 400
    if not isinstance(profile, str) or profile not in known_profiles():
        return {"message": f"Unknown profile: {profile!r}"}, 400
    if not isinstance(is_draft, bool):
        return {"message": "isDraft must be a boolean."}, 400

    # Before the identifier is read from it, so both get the same spelling.
    normalize_id_case(document)

    return RecordInput(document=document, profile=profile, is_draft=is_draft)


def publication_error(data: RecordInput) -> ApiResponse | None:
    """Only published records must pass full schema/semantic validation."""
    if data.is_draft:
        return None

    errors = validate_record(data.document, data.profile)
    if any(error.get("severity", "error") == "error" for error in errors):
        return {"message": "The record is not publishable.", "errors": errors}, 422

    return None


# ---------------------------------------------------------------------------
# Identifier handling
# ---------------------------------------------------------------------------


def record_identifier_taken(
    identifier: str,
    *,
    exclude_id: int | None = None,
) -> bool:
    query = VulnerabilityRecord.query.filter(
        func.lower(VulnerabilityRecord.identifier) == identifier.lower(),
    )
    if exclude_id is not None:
        query = query.filter(VulnerabilityRecord.id != exclude_id)

    return bool(db.session.query(query.exists()).scalar())


def identifier_error(
    identifier: str | None,
    *,
    is_draft: bool,
    existing_record: VulnerabilityRecord | None = None,
) -> ApiResponse | None:
    """Check assignment, uniqueness, and immutability in one place.

    A new record (or a draft without one yet) may acquire its first
    identifier. Once assigned, it cannot change, even while still a draft.
    """
    if not identifier and not is_draft:
        return {"message": "A record identifier is required before publication."}, 400

    if existing_record is not None and existing_record.identifier is not None:
        if (
            not identifier
            or identifier.casefold() != existing_record.identifier.casefold()
        ):
            return {"message": "The record identifier cannot be changed."}, 400
        return None

    if identifier and record_identifier_taken(
        identifier,
        exclude_id=existing_record.id if existing_record is not None else None,
    ):
        return {"message": "The record already exists."}, 409

    return None


# ---------------------------------------------------------------------------
# Access checks and API serialization
# ---------------------------------------------------------------------------


def is_owner(record: VulnerabilityRecord) -> bool:
    return (
        record.created_by_id is not None
        and record.created_by_id == current_user.id
    )


def can_read_record(record: VulnerabilityRecord) -> bool:
    """Published records are readable; drafts belong to their owner/admin."""
    return not record.is_draft or current_user.is_admin or is_owner(record)


def can_modify_record(record: VulnerabilityRecord) -> bool:
    """Only the owner or an administrator may change or delete a record."""
    return current_user.is_admin or is_owner(record)


def find_record(record_id: int) -> VulnerabilityRecord | None:
    """The record, or None if it doesn't exist or this user may not read it."""
    record = db.session.get(VulnerabilityRecord, record_id)
    return record if record is not None and can_read_record(record) else None


def record_response(record: VulnerabilityRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "identifier": record.identifier,
        "profile": record.profile,
        "record": record.document,
        "isDraft": record.is_draft,
    }


# ---------------------------------------------------------------------------
# Record endpoints
# ---------------------------------------------------------------------------


@api_bp.get("/records")
def list_records() -> ApiResponse:
    query = VulnerabilityRecord.query
    if not current_user.is_admin:
        query = query.filter(
            or_(
                VulnerabilityRecord.is_draft.is_(False),
                VulnerabilityRecord.created_by_id == current_user.id,
            ),
        )

    records = query.order_by(
        VulnerabilityRecord.updated_at.desc(),
        VulnerabilityRecord.id.desc(),  # Stable order for equal timestamps.
    ).all()

    return {
        "records": [
            {
                "id": record.id,
                "identifier": record.identifier,
                "profile": record.profile,
                "isDraft": record.is_draft,
                "updatedAt": record.updated_at.isoformat(),
                "createdBy": record.created_by.email if record.created_by else None,
            }
            for record in records
        ],
    }, 200


@api_bp.get("/records/<int:record_id>")
def get_record(record_id: int) -> ApiResponse:
    record = find_record(record_id)
    if record is None:
        return {"message": "Record not found."}, 404

    return record_response(record), 200


@api_bp.post("/records")
def create_record() -> ApiResponse:
    data = read_record_input()
    if isinstance(data, tuple):
        return data

    identifier = extract_identifier(data.document, data.profile)
    error = identifier_error(identifier, is_draft=data.is_draft)
    if error is not None:
        return error

    error = publication_error(data)
    if error is not None:
        return error

    record = VulnerabilityRecord(
        identifier=identifier,
        profile=data.profile,
        document=data.document,
        is_draft=data.is_draft,
        created_by_id=current_user.id,
    )
    db.session.add(record)
    error = commit_or_conflict()
    if error is not None:
        return error
    return record_response(record), 201


def commit_or_conflict() -> ApiResponse | None:
    """identifier_error checks uniqueness first, but two requests can pass
    that check at the same time; the database's case-insensitive unique
    index then rejects the second one.
    """
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"message": "The record already exists."}, 409

    return None


@api_bp.put("/records/<int:record_id>")
def update_record(record_id: int) -> ApiResponse:
    record = find_record(record_id)
    if record is None:
        return {"message": "Record not found."}, 404
    if not can_modify_record(record):
        return {"message": "You cannot modify this record."}, 403

    data = read_record_input(
        default_profile=record.profile,
        default_is_draft=record.is_draft,
    )
    if isinstance(data, tuple):
        return data

    # Reject a format change before modifying the record or publications.
    if data.profile != record.profile:
        return {"message": "The record profile cannot be changed."}, 400

    document_identifier = extract_identifier(data.document, record.profile)
    error = identifier_error(
        document_identifier,
        is_draft=data.is_draft,
        existing_record=record,
    )
    if error is not None:
        return error

    error = publication_error(data)
    if error is not None:
        return error

    # No mutations occur until all validation has succeeded. Past
    # identifier_error, the document's identifier is either the first
    # one or the stored one in a different case (e.g. a lowercased GCVE
    # ID corrected by hand), which may update the stored spelling.
    if document_identifier:
        record.identifier = document_identifier

    record.document = data.document
    record.is_draft = data.is_draft
    error = commit_or_conflict()
    if error is not None:
        return error

    return record_response(record), 200


@api_bp.delete("/records/<int:record_id>")
def delete_record(record_id: int) -> ApiResponse:
    record = find_record(record_id)
    if record is None:
        return {"message": "Record not found."}, 404
    if not can_modify_record(record):
        return {"message": "You cannot modify this record."}, 403

    CnaPublication.query.filter_by(record_id=record.id).delete(
        synchronize_session=False,
    )
    db.session.delete(record)
    db.session.commit()
    return {"id": record_id}, 200
