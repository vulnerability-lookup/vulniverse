from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from flask import request
from flask_login import current_user

from ..app_config import load_app_config
from ..auth.organisations import can_modify_record, can_read_record
from ..extensions import db
from ..models import CnaPublication, VulnerabilityRecord
from ..services.cna_credentials import is_credential_configured
from ..services.cna_publication import (
    KNOWN_TARGETS,
    CnaPublicationService,
    IntegrationNotConfiguredError,
    LinkedElsewhereError,
)
from ..services.identifiers import canonical_id
from . import api_bp
from .records import (
    find_record,
    id_taken_message,
    record_with_identifier,
    stale_version_error,
    validation_failure,
)


def _serialize(
    publication: CnaPublication,
) -> dict[str, Any]:
    return {
        "id": publication.id,
        "recordId": publication.record_id,
        "target": publication.target,
        "status": publication.status,
        "cveId": publication.cve_id,
        "reservedAt": publication.reserved_at.isoformat()
        if publication.reserved_at
        else None,
        "publishedAt": publication.published_at.isoformat()
        if publication.published_at
        else None,
        "rejectedAt": publication.rejected_at.isoformat()
        if publication.rejected_at
        else None,
        "lastSentAt": publication.last_sent_at.isoformat()
        if publication.last_sent_at
        else None,
        "lastError": publication.last_error,
        "createdAt": publication.created_at.isoformat(),
        "updatedAt": publication.updated_at.isoformat(),
    }


def _resolve_service(
    target: str,
    record_id: int,
    *,
    modify: bool = False,
) -> tuple[CnaPublicationService, None] | tuple[None, tuple[dict, int]]:
    if target not in KNOWN_TARGETS:
        return None, ({"message": f"Unknown publication target: {target!r}"}, 404)

    # target doubles as the panel id ("vl"/"cve-program") -- see
    # config/vulniverse.toml.sample's [panels.vl]/[panels.cve-program].
    if not load_app_config()["panels"].get(target, True):
        return None, ({"message": f"The {target!r} panel is disabled."}, 404)

    # Same access rules as the record itself (see api/records.py).
    record = find_record(record_id)

    if record is None:
        return None, ({"message": "Record not found."}, 404)

    if modify and not can_modify_record(record):
        return None, ({"message": "You cannot modify this record."}, 403)

    try:
        return CnaPublicationService(current_user.id, target), None
    except IntegrationNotConfiguredError as exc:
        return None, ({"message": str(exc)}, 409)


def _upstream_error_response(
    service: CnaPublicationService,
    record_id: int,
) -> tuple[dict, int]:
    return {
        "message": "The upstream request failed.",
        "publication": _serialize(service.get_or_create(record_id)),
    }, 502


@api_bp.get("/publish/targets")
def publish_targets() -> tuple[dict, int]:
    panels = load_app_config()["panels"]

    return {
        target: {"configured": is_credential_configured(current_user.id, target)}
        for target in KNOWN_TARGETS
        if panels.get(target, True)
    }, 200


@api_bp.get("/publish/<string:target>/<int:record_id>")
def get_publication(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    service, error = _resolve_service(target, record_id)

    if error:
        return error

    assert service is not None

    return _serialize(service.get_or_create(record_id)), 200


@api_bp.post("/publish/<string:target>/<int:record_id>/reserve")
def reserve_cve_id(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    payload = request.get_json(silent=True) or {}
    year = payload.get("year", datetime.now(UTC).year)

    if not isinstance(year, int):
        return {"message": "'year' must be an integer."}, 400

    try:
        publication = service.reserve_cve_id(record_id, year)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_id)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


@api_bp.post("/publish/<string:target>/<int:record_id>/pull")
def pull_from_upstream(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    """{"cveId"}: link the record to that upstream ID and take over its
    state. Answers {"publication", "record"}, the upstream record being
    null while the ID is only reserved."""
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    payload = request.get_json(silent=True)
    cve_id = payload.get("cveId") if isinstance(payload, dict) else None

    if not isinstance(cve_id, str) or not cve_id.strip():
        return {"message": "A 'cveId' is required."}, 400

    # The ID may already be another record's own ID (in its content) even
    # without a link, e.g. after Stop tracking there: linking it here
    # would leave this record unable to take the ID.
    linking = find_record(record_id)
    assert linking is not None
    holder = record_with_identifier(
        canonical_id(cve_id.strip()), linking.organisation_id, exclude_id=record_id
    )
    if holder is not None:
        return {
            "message": id_taken_message(canonical_id(cve_id.strip()), holder)
            + " Link that record instead, or remove the ID from it first."
        }, 400

    try:
        publication, record = service.pull(record_id, cve_id)
    except LinkedElsewhereError as exc:
        return linked_elsewhere(exc), 400
    except LookupError as exc:
        return {"message": str(exc)}, 404
    except ValueError as exc:
        return {"message": str(exc)}, 400
    except httpx.HTTPError as exc:
        # The key travels in headers, which httpx errors don't include.
        return {"message": f"Upstream didn't answer: {exc}"}, 502

    return {"publication": _serialize(publication), "record": record}, 200


@api_bp.post("/publish/<string:target>/<int:record_id>/publish")
def publish_record(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    """{"version"}: the record version the editor shows, so exactly that
    goes out; without it (older clients), the stored one does."""
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    # What's sent is the stored record: it must be the version the user
    # saw, and valid (drafts are saved unvalidated). Nothing leaves the
    # server otherwise.
    record = find_record(record_id)
    assert record is not None
    refusal = stale_version_error(record) or validation_failure(
        record.document, record.profile
    )
    if refusal is not None:
        return refusal

    try:
        publication = service.publish(record_id)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_id)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


def linked_elsewhere(error: LinkedElsewhereError) -> dict[str, Any]:
    """Names the other record if the user may see it; drafts of other
    organisations stay unnamed."""
    other = db.session.get(VulnerabilityRecord, error.record_id)
    if other is None or not can_read_record(other):
        return {
            "message": f"{error.cve_id} is already linked to a record you can't see."
        }

    name = other.identifier or f"record #{other.id}"
    return {
        "message": f"{error.cve_id} is already linked to {name}. Stop tracking it"
        " there first, or link this record to another ID."
    }


@api_bp.delete("/publish/<string:target>/<int:record_id>")
def unlink_record(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    """Stop tracking: remove the link to upstream (the ID stays there)."""
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    return _serialize(service.unlink(record_id)), 200


@api_bp.post("/publish/<string:target>/<int:record_id>/reject")
def reject_record(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    payload = request.get_json(silent=True) or {}
    reason = payload.get("reason")

    if not isinstance(reason, str) or not reason.strip():
        return {"message": "A non-empty 'reason' is required."}, 400

    try:
        publication = service.reject(record_id, reason)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_id)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


@api_bp.post("/publish/<string:target>/<int:record_id>/abort")
def abort_publication(
    target: str,
    record_id: int,
) -> tuple[dict, int]:
    service, error = _resolve_service(target, record_id, modify=True)

    if error:
        return error

    assert service is not None

    try:
        publication = service.abort(record_id)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200
