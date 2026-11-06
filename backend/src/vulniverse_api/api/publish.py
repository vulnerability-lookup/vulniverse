from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from flask import request
from flask_login import current_user

from ..app_config import load_app_config
from ..models import CnaPublication
from ..services.cna_credentials import is_credential_configured
from ..services.cna_publication import (
    KNOWN_TARGETS,
    CnaPublicationService,
    IntegrationNotConfiguredError,
)
from . import api_bp


def _serialize(
    publication: CnaPublication,
) -> dict[str, Any]:
    return {
        "id": publication.id,
        "recordIdentifier": publication.record_identifier,
        "target": publication.target,
        "status": publication.status,
        "cveId": publication.cve_id,
        "reservedAt": publication.reserved_at.isoformat() if publication.reserved_at else None,
        "publishedAt": publication.published_at.isoformat() if publication.published_at else None,
        "rejectedAt": publication.rejected_at.isoformat() if publication.rejected_at else None,
        "lastError": publication.last_error,
        "createdAt": publication.created_at.isoformat(),
        "updatedAt": publication.updated_at.isoformat(),
    }


def _resolve_service(
    target: str,
) -> tuple[CnaPublicationService, None] | tuple[None, tuple[dict, int]]:
    if target not in KNOWN_TARGETS:
        return None, ({"message": f"Unknown publication target: {target!r}"}, 404)

    # target doubles as the panel id ("vl"/"cve-program") -- see
    # config/vulniverse.toml.sample's [panels.vl]/[panels.cve-program].
    if not load_app_config()["panels"].get(target, True):
        return None, ({"message": f"The {target!r} panel is disabled."}, 404)

    try:
        return CnaPublicationService(current_user.id, target), None
    except IntegrationNotConfiguredError as exc:
        return None, ({"message": str(exc)}, 409)


def _upstream_error_response(
    service: CnaPublicationService,
    record_identifier: str,
) -> tuple[dict, int]:
    return {
        "message": "The upstream request failed.",
        "publication": _serialize(service.get_or_create(record_identifier)),
    }, 502


@api_bp.get("/publish/targets")
def publish_targets() -> tuple[dict, int]:
    panels = load_app_config()["panels"]

    return {
        target: {"configured": is_credential_configured(current_user.id, target)}
        for target in KNOWN_TARGETS
        if panels.get(target, True)
    }, 200


@api_bp.get("/publish/<string:target>/<string:record_identifier>")
def get_publication(
    target: str,
    record_identifier: str,
) -> tuple[dict, int]:
    service, error = _resolve_service(target)

    if error:
        return error

    assert service is not None

    return _serialize(service.get_or_create(record_identifier)), 200


@api_bp.post("/publish/<string:target>/<string:record_identifier>/reserve")
def reserve_cve_id(
    target: str,
    record_identifier: str,
) -> tuple[dict, int]:
    service, error = _resolve_service(target)

    if error:
        return error

    assert service is not None

    payload = request.get_json(silent=True) or {}
    year = payload.get("year", datetime.now(UTC).year)

    if not isinstance(year, int):
        return {"message": "'year' must be an integer."}, 400

    try:
        publication = service.reserve_cve_id(record_identifier, year)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_identifier)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


@api_bp.post("/publish/<string:target>/<string:record_identifier>/publish")
def publish_record(
    target: str,
    record_identifier: str,
) -> tuple[dict, int]:
    service, error = _resolve_service(target)

    if error:
        return error

    assert service is not None

    try:
        publication = service.publish(record_identifier)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_identifier)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


@api_bp.post("/publish/<string:target>/<string:record_identifier>/reject")
def reject_record(
    target: str,
    record_identifier: str,
) -> tuple[dict, int]:
    service, error = _resolve_service(target)

    if error:
        return error

    assert service is not None

    payload = request.get_json(silent=True) or {}
    reason = payload.get("reason")

    if not isinstance(reason, str) or not reason.strip():
        return {"message": "A non-empty 'reason' is required."}, 400

    try:
        publication = service.reject(record_identifier, reason)
    except httpx.HTTPError:
        return _upstream_error_response(service, record_identifier)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200


@api_bp.post("/publish/<string:target>/<string:record_identifier>/abort")
def abort_publication(
    target: str,
    record_identifier: str,
) -> tuple[dict, int]:
    service, error = _resolve_service(target)

    if error:
        return error

    assert service is not None

    try:
        publication = service.abort(record_identifier)
    except ValueError as exc:
        return {"message": str(exc)}, 400

    return _serialize(publication), 200
