from __future__ import annotations

import uuid
from typing import Any

from flask import request
from flask_login import current_user
from sqlalchemy import func, or_

from ..extensions import db
from ..models import CnaPublication, VulnerabilityRecord
from ..services.record_validation import (
    find_x_gcve_occurrences,
    known_profiles,
    validate_record,
)
from . import api_bp


def has_blocking_errors(errors: list[dict[str, Any]]) -> bool:
    return any(
        error.get("severity", "error") == "error"
        for error in errors
    )


def gcve_vuln_id(document: dict[str, Any]) -> str | None:
    """The real GCVE-BCP-05 identifier, read from wherever x_gcve
    actually appears in the document
    """
    occurrences = find_x_gcve_occurrences(document)

    if not occurrences:
        return None

    _path, extensions = occurrences[0]

    if not isinstance(extensions, list) or not extensions:
        return None

    first = extensions[0]
    vuln_id = first.get("vulnId") if isinstance(first, dict) else None

    return vuln_id if isinstance(vuln_id, str) else None


def is_gcve_profile(profile: str) -> bool:
    return profile.startswith("gcve-")


def extract_identifier(
    document: dict[str, Any],
    profile: str,
) -> str | None:
    """Mirrors PreviewSection.vue's primaryIdentifier exactly: for a
    gcve-* profile, the real GCVE-BCP-05 x_gcve[].vulnId (or its
    non-standard cveMetadata.vulnId stand-in) wins over cveId; for any
    other profile, cveId wins — a plain cve-5.2.0 draft can carry a
    stray x_gcve key (drafts skip schema validation), and that
    shouldn't out-rank its actual cveId just because it happens to be
    present.
    """
    metadata = document.get("cveMetadata")
    cve_metadata = metadata if isinstance(metadata, dict) else {}

    vuln_id = gcve_vuln_id(document) or cve_metadata.get("vulnId")
    cve_id = cve_metadata.get("cveId")

    identifier = vuln_id if is_gcve_profile(profile) and vuln_id else (cve_id or vuln_id)

    return identifier if isinstance(identifier, str) else None


def identifier_still_present(
    document: dict[str, Any],
    identifier: str,
) -> bool:
    """A record's identifier, once assigned at creation, is pinned to
    this row forever
    """
    metadata = document.get("cveMetadata")
    cve_metadata = metadata if isinstance(metadata, dict) else {}

    candidates = (
        gcve_vuln_id(document),
        cve_metadata.get("vulnId"),
        cve_metadata.get("cveId"),
    )

    # Case-insensitive: CVE/GCVE identifiers are conventionally
    # uppercase, but a hand-typed or externally-sourced one may not be
    # — "GCVE-1-2026-1" and "gcve-1-2026-1" are the same identifier, not
    # a fabricated identity change.
    identifier_lower = identifier.lower()

    return any(
        isinstance(candidate, str) and candidate.lower() == identifier_lower
        for candidate in candidates
    )


def find_record_by_identifier(identifier: str) -> VulnerabilityRecord | None:
    """Case-insensitive lookup — see identifier_still_present()."""
    return VulnerabilityRecord.query.filter(
        func.lower(VulnerabilityRecord.identifier) == identifier.lower(),
    ).first()


def record_identifier_taken(
    identifier: str,
    *,
    exclude_id: int | None = None,
) -> bool:
    """Case-insensitive "does another record already use this
    identifier" check — see identifier_still_present()."""
    query = VulnerabilityRecord.query.filter(
        func.lower(VulnerabilityRecord.identifier) == identifier.lower(),
    )

    if exclude_id is not None:
        query = query.filter(VulnerabilityRecord.id != exclude_id)

    return db.session.query(query.exists()).scalar()


PLACEHOLDER_PREFIX = "draft-"


def is_placeholder_identifier(identifier: str) -> bool:
    """True for the "draft-<id>" placeholder create_record() assigns
    when a record is saved with no vulnId/cveId yet — a real CVE/GCVE
    identifier can never start with this (their formats are fixed:
    "CVE-YYYY-NNNN", "GCVE-N-YYYY-NNNNN"), so it's unambiguous. Plain
    letters/digits/hyphens only — deliberately not e.g. a "#" prefix,
    which would need percent-encoding in every URL it appears in and
    breaks outright if any call site (including a test, as one did
    here) forgets to.
    """
    return identifier.startswith(PLACEHOLDER_PREFIX)


def reassign_identifier(record: VulnerabilityRecord, new_identifier: str) -> None:
    """Moves a record off its "draft-<id>" placeholder onto a real
    identifier — the one-time transition from "created with no ID"
    to "has an ID" (see create_record()). Also re-keys any
    CnaPublication rows filed under the placeholder (e.g. from
    reserving a CVE ID before ever typing one in) so a reservation
    made before this moment isn't silently orphaned. Skips a
    particular (target) re-key only in the pathological case where a
    row already exists under the new identifier for that target —
    exceedingly unlikely, but safer than crashing on the unique
    constraint.
    """
    old_identifier = record.identifier
    record.identifier = new_identifier

    for publication in CnaPublication.query.filter_by(
        record_identifier=old_identifier,
    ).all():
        conflict = CnaPublication.query.filter_by(
            record_identifier=new_identifier,
            target=publication.target,
        ).first()

        if conflict is None:
            publication.record_identifier = new_identifier


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
    record = find_record_by_identifier(identifier)

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

    identifier = extract_identifier(document, profile)

    if not identifier and not is_draft:
        return {
            "message": "A record needs a CVE/GCVE identifier before it can be published.",
        }, 400

    if identifier and record_identifier_taken(identifier):
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
        # A globally-unique placeholder, temporary only within this
        # transaction — reassign_identifier() (via the PLACEHOLDER_PREFIX
        # scheme) replaces it below once the row has a real id to build
        # that from. Random, not "", so two concurrent identifier-less
        # creates can never collide on the unique constraint before
        # either gets its real placeholder assigned.
        identifier=identifier or f"{PLACEHOLDER_PREFIX}pending-{uuid.uuid4().hex}",
        profile=profile,
        document=document,
        is_draft=is_draft,
        created_by_id=current_user.id,
    )

    db.session.add(record)

    if not identifier:
        db.session.flush()
        record.identifier = f"{PLACEHOLDER_PREFIX}{record.id}"

    db.session.commit()

    return {
        "identifier": record.identifier,
        "profile": profile,
        "record": document,
        "isDraft": is_draft,
    }, 201


@api_bp.put("/records/<string:identifier>")
def update_record(identifier: str) -> tuple[dict, int]:
    record = find_record_by_identifier(identifier)

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

    is_placeholder = is_placeholder_identifier(identifier)
    # Only meaningful while is_placeholder — extract_identifier() looks
    # at vulnId/cveId directly, unlike identifier_still_present()'s
    # "did the pinned one survive" check used once a real one exists.
    real_identifier = extract_identifier(document, profile) if is_placeholder else None

    if is_placeholder:
        # Not pinned to anything real yet — the first real vulnId/cveId
        # the document picks up (if any) becomes the record's identifier
        # for good, exactly as if it had been supplied at creation.
        if real_identifier and record_identifier_taken(
            real_identifier,
            exclude_id=record.id,
        ):
            return {"message": "The record already exists."}, 409
        elif not is_draft:
            return {
                "message": "A record needs a CVE/GCVE identifier before it can be published.",
            }, 400
    elif not identifier_still_present(document, identifier):
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

    if real_identifier:
        reassign_identifier(record, real_identifier)

    record.profile = profile
    record.document = document
    record.is_draft = is_draft

    db.session.commit()

    return {
        "identifier": record.identifier,
        "profile": profile,
        "record": document,
        "isDraft": is_draft,
    }, 200


@api_bp.delete("/records/<string:identifier>")
def delete_record(identifier: str) -> tuple[dict, int]:
    record = find_record_by_identifier(identifier)

    if record is None or not is_visible(record):
        return {"message": "Record not found."}, 404

    db.session.delete(record)
    db.session.commit()

    return {"identifier": identifier}, 200
