"""CRUD endpoints for vulnerability records.

Records are addressed by their database ``id``. The vulnerability identifier
(CVE/GCVE/OSV id) is read from the document according to its profile, and is
NULL for a draft that doesn't have one yet; it is unique within the record's
organisation. Who may read and change a record: auth/organisations.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from flask import request
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from ..auth.organisations import (
    can_modify_record,
    can_read_record,
    current_organisation,
)
from ..extensions import db
from ..models import CnaPublication, Patch2VulnCandidate, VulnerabilityRecord
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

    return validation_failure(data.document, data.profile)


def validation_failure(document: dict[str, Any], profile: str) -> ApiResponse | None:
    """422 with the errors (the editor marks the fields) unless the
    document passes full validation; warnings don't count."""
    errors = validate_record(document, profile)
    if any(error.get("severity", "error") == "error" for error in errors):
        return {"message": "The record is not publishable.", "errors": errors}, 422

    return None


# ---------------------------------------------------------------------------
# Identifier handling
# ---------------------------------------------------------------------------


def record_with_identifier(
    identifier: str,
    organisation_id: int,
    *,
    exclude_id: int | None = None,
) -> VulnerabilityRecord | None:
    """The organisation's record with this ID, if any. Other
    organisations' records don't count (and mustn't be revealed)."""
    query = VulnerabilityRecord.query.filter(
        VulnerabilityRecord.organisation_id == organisation_id,
        func.lower(VulnerabilityRecord.identifier) == identifier.lower(),
    )
    if exclude_id is not None:
        query = query.filter(VulnerabilityRecord.id != exclude_id)

    return query.first()


def id_taken_message(identifier: str, holder: VulnerabilityRecord) -> str:
    """Which record already has the ID: its title, as the ID is the same."""
    cna = (holder.document.get("containers") or {}).get("cna")
    title = cna.get("title") if isinstance(cna, dict) else None
    named = f' ("{title}")' if isinstance(title, str) and title.strip() else ""
    state = "draft" if holder.is_draft else "record"
    return (
        f"Another {state} in this organisation already has the ID {identifier}{named}."
    )


def identifier_error(
    identifier: str | None,
    organisation_id: int,
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

    holder = (
        record_with_identifier(
            identifier,
            organisation_id,
            exclude_id=existing_record.id if existing_record is not None else None,
        )
        if identifier
        else None
    )
    if identifier and holder is not None:
        return {"message": id_taken_message(identifier, holder)}, 409

    return None


# ---------------------------------------------------------------------------
# Access checks and API serialization
# ---------------------------------------------------------------------------


def find_record(record_id: int) -> VulnerabilityRecord | None:
    """The record, or None if it doesn't exist or this user may not read it."""
    record = db.session.get(VulnerabilityRecord, record_id)
    return record if record is not None and can_read_record(record) else None


def organisation_response(record: VulnerabilityRecord) -> dict[str, Any]:
    return {"id": record.organisation.id, "name": record.organisation.name}


def record_response(record: VulnerabilityRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "identifier": record.identifier,
        "profile": record.profile,
        "record": record.document,
        "isDraft": record.is_draft,
        "version": record.version,
        "organisation": organisation_response(record),
    }


# ---------------------------------------------------------------------------
# Record endpoints
# ---------------------------------------------------------------------------


@api_bp.get("/records")
def list_records() -> ApiResponse:
    """The current organisation's records. Instance admins see every
    organisation's, or one's with ?organisation=<id>. Other organisations'
    published records stay readable by link, they just aren't listed."""
    query = VulnerabilityRecord.query

    if current_user.is_admin:
        organisation_id = request.args.get("organisation", type=int)
        if organisation_id is not None:
            query = query.filter(VulnerabilityRecord.organisation_id == organisation_id)
    else:
        organisation = current_organisation()
        if organisation is None:
            return {"records": []}, 200
        query = query.filter(VulnerabilityRecord.organisation_id == organisation.id)

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
                "organisation": organisation_response(record),
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
    organisation = current_organisation()
    if organisation is None:
        return {
            "message": "You are not a member of any organisation yet."
            " Ask an administrator to add you to one.",
        }, 403

    data = read_record_input()
    if isinstance(data, tuple):
        return data

    identifier = extract_identifier(data.document, data.profile)
    error = identifier_error(identifier, organisation.id, is_draft=data.is_draft)
    if error is not None:
        return error

    error = publication_error(data)
    if error is not None:
        return error

    candidate: Patch2VulnCandidate | None = None
    candidate_id = (request.get_json(silent=True) or {}).get("candidateId")
    if candidate_id is not None:
        found = review_candidate(candidate_id, organisation.id)
        if isinstance(found, tuple):
            return found
        candidate = found

    record = VulnerabilityRecord(
        identifier=identifier,
        profile=data.profile,
        document=data.document,
        is_draft=data.is_draft,
        organisation_id=organisation.id,
        created_by_id=current_user.id,
    )
    db.session.add(record)
    if candidate is not None:
        # In the same commit, so a candidate never gets two records.
        db.session.flush()
        candidate.record_id = record.id
        candidate.dismissed = False
    error = commit_or_conflict()
    if error is not None:
        return error
    return record_response(record), 201


def review_candidate(
    candidate_id: Any,
    organisation_id: int,
) -> Patch2VulnCandidate | ApiResponse:
    """The Patch2Vuln candidate a new record is created from: one of the
    organisation's, without a record yet."""
    # bool is an int subclass; True isn't an id.
    if not isinstance(candidate_id, int) or isinstance(candidate_id, bool):
        return {"message": "candidateId must be an integer."}, 400

    candidate = db.session.get(Patch2VulnCandidate, candidate_id)
    if candidate is None or candidate.batch.organisation_id != organisation_id:
        return {"message": "Candidate not found."}, 404
    if candidate.record_id is not None:
        return {
            "message": "A record was already created from this candidate.",
            "recordId": candidate.record_id,
        }, 409

    return candidate


CHANGED_MEANWHILE: ApiResponse = (
    {
        "code": "CHANGED_MEANWHILE",
        "message": "Someone else saved this record after you opened it."
        " Reload to see their version (copy your changes first,"
        " e.g. from Advanced JSON, if you need them).",
    },
    409,
)


def commit_or_conflict() -> ApiResponse | None:
    """identifier_error checks uniqueness first, but two requests can pass
    that check at the same time; the database's per-organisation,
    case-insensitive unique index then rejects the second one. Likewise
    for two saves of one record: the version guard (see the model)."""
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"message": "The record already exists."}, 409
    except StaleDataError:
        db.session.rollback()
        return CHANGED_MEANWHILE

    return None


def stale_version_error(record: VulnerabilityRecord) -> ApiResponse | None:
    """A save names the version it was based on; another one since means
    someone else saved in between. Without one (API clients and scripts
    from before versions), the save goes through as before."""
    payload = request.get_json(silent=True)
    expected = payload.get("version") if isinstance(payload, dict) else None

    if expected is None:
        return None
    # bool is an int subclass; True isn't a version.
    if not isinstance(expected, int) or isinstance(expected, bool):
        return {"message": "version must be an integer."}, 400
    if expected != record.version:
        return CHANGED_MEANWHILE

    return None


@api_bp.put("/records/<int:record_id>")
def update_record(record_id: int) -> ApiResponse:
    record = find_record(record_id)
    if record is None:
        return {"message": "Record not found."}, 404
    if not can_modify_record(record):
        return {"message": "You cannot modify this record."}, 403

    error = stale_version_error(record)
    if error is not None:
        return error

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
        record.organisation_id,
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
    record.version += 1
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
    # Its candidate can be reviewed again.
    Patch2VulnCandidate.query.filter_by(record_id=record.id).update(
        {"record_id": None},
        synchronize_session=False,
    )
    db.session.delete(record)
    db.session.commit()
    return {"id": record_id}, 200
