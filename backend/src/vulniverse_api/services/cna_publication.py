from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx

from ..extensions import db
from ..models import CnaPublication, VulnerabilityRecord
from .app_config import get_integration

REQUEST_TIMEOUT_SECONDS = 30.0

# "vl" and "cve-program" speak the identical CVE Services API-shaped
# protocol (see docs/embedding/vl.md and VL's own website/web/api/v1/cna.py)
# — the only difference is which [integrations.<target>] table in
# config/vulniverse.toml supplies the base URL and credentials.
KNOWN_TARGETS = frozenset({"vl", "cve-program"})


class PublicationStatus(StrEnum):
    LOCAL_ONLY = "LOCAL_ONLY"
    RESERVATION_PENDING = "RESERVATION_PENDING"
    RESERVED = "RESERVED"
    PUBLICATION_PENDING = "PUBLICATION_PENDING"
    PUBLISHED = "PUBLISHED"
    REJECTION_PENDING = "REJECTION_PENDING"
    REJECTED = "REJECTED"
    ABORTED = "ABORTED"


# Allowed prior statuses for each target status. A transition is allowed iff
# publication.status is in ALLOWED_TRANSITIONS[target_status]. Ported from
# Vulnerability-Lookup's own CNAPubService.ALLOWED_TRANSITIONS
# (website/web/services/cna_pub_service.py), which this whole service
# mirrors the shape of.
ALLOWED_TRANSITIONS: dict[PublicationStatus, frozenset[PublicationStatus]] = {
    PublicationStatus.RESERVED: frozenset({
        PublicationStatus.LOCAL_ONLY,
        PublicationStatus.RESERVATION_PENDING,
    }),
    PublicationStatus.PUBLISHED: frozenset({
        PublicationStatus.RESERVED,
        PublicationStatus.PUBLICATION_PENDING,
        PublicationStatus.PUBLISHED,
        PublicationStatus.REJECTED,
    }),
    PublicationStatus.REJECTED: frozenset({
        PublicationStatus.RESERVED,
        PublicationStatus.PUBLISHED,
        PublicationStatus.REJECTION_PENDING,
    }),
    PublicationStatus.ABORTED: frozenset(PublicationStatus) - {PublicationStatus.ABORTED},
}


class IntegrationNotConfiguredError(ValueError):
    pass


class CnaPublicationService:
    """Reserve/publish/reject a CVE against one CVE Services API-shaped
    target ("vl" or "cve-program"). Both targets are the same protocol at a
    different base_url with different credentials, so one implementation
    serves both — see KNOWN_TARGETS above.
    """

    def __init__(self, target: str) -> None:
        credentials = get_integration(target)

        if credentials is None:
            raise IntegrationNotConfiguredError(
                f"No credentials configured for {target!r}. Set "
                f"[integrations.{target}] in config/vulniverse.toml.",
            )

        self.target = target
        self.base_url = credentials["cve_url"].rstrip("/")
        self.short_name = credentials["short_name"]
        self._api_key = credentials["cve_api_key"]
        self._headers = {
            "CVE-API-ORG": credentials["cve_api_org"],
            "CVE-API-USER": credentials["cve_api_user"],
            "CVE-API-KEY": credentials["cve_api_key"],
        }

    # ----- lookups -----

    def get_or_create(self, record_identifier: str) -> CnaPublication:
        publication = CnaPublication.query.filter_by(
            record_identifier=record_identifier,
            target=self.target,
        ).first()

        if publication is not None:
            return publication

        publication = CnaPublication(
            record_identifier=record_identifier,
            target=self.target,
            status=PublicationStatus.LOCAL_ONLY.value,
        )

        db.session.add(publication)
        db.session.commit()

        return publication

    # ----- actions -----

    def reserve_cve_id(
        self,
        record_identifier: str,
        year: int,
    ) -> CnaPublication:
        publication = self.get_or_create(record_identifier)
        self._assert_can_transition(publication, PublicationStatus.RESERVED)

        params = {
            "cve_year": year,
            "amount": 1,
            "batch_type": "sequential",
            "short_name": self.short_name,
        }

        response = self._do_request(
            publication,
            PublicationStatus.RESERVATION_PENDING,
            "POST",
            f"{self.base_url}/cve-id",
            params=params,
        )

        data = response.json()

        try:
            cve_id = data["cve_ids"][0]["cve_id"]
        except (KeyError, IndexError, TypeError) as exc:
            publication.status = PublicationStatus.RESERVATION_PENDING.value
            publication.last_response = self._scrub(json.dumps(data))
            publication.last_error = self._scrub(
                f"Unexpected response shape, no cve_ids[0].cve_id: {json.dumps(data)}",
            )
            self._save(publication)
            raise ValueError("Upstream returned no CVE ID.") from exc

        publication.status = PublicationStatus.RESERVED.value
        publication.cve_id = cve_id
        publication.reserved_at = datetime.now(UTC)
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def publish(self, record_identifier: str) -> CnaPublication:
        publication = self.get_or_create(record_identifier)
        self._assert_can_transition(publication, PublicationStatus.PUBLISHED)

        if not publication.cve_id:
            raise ValueError("Reserve a CVE ID before publishing.")

        record = VulnerabilityRecord.query.filter_by(
            identifier=record_identifier,
        ).first()

        if record is None:
            raise ValueError(f"Unknown record: {record_identifier}")

        cna_container = (record.document.get("containers") or {}).get("cna")

        if not isinstance(cna_container, dict):
            # A malformed/incomplete record, not a caller type error.
            raise ValueError("Record has no containers.cna to publish.")  # noqa: TRY004

        body = {"cnaContainer": cna_container}
        use_put = publication.published_at is not None
        method = "PUT" if use_put else "POST"

        response = self._do_request(
            publication,
            PublicationStatus.PUBLICATION_PENDING,
            method,
            f"{self.base_url}/cve/{publication.cve_id}/cna",
            json_body=body,
        )

        data = response.json()

        publication.status = PublicationStatus.PUBLISHED.value
        if not use_put:
            publication.published_at = datetime.now(UTC)
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def reject(self, record_identifier: str, reason: str) -> CnaPublication:
        if not reason.strip():
            raise ValueError("A rejection reason is required.")

        publication = self.get_or_create(record_identifier)
        self._assert_can_transition(publication, PublicationStatus.REJECTED)

        if not publication.cve_id:
            raise ValueError("Publication has no reserved CVE ID.")

        body = {
            "cnaContainer": {
                "rejectedReasons": [{"lang": "en", "value": reason.strip()}],
            },
        }
        use_put = publication.published_at is not None
        method = "PUT" if use_put else "POST"

        response = self._do_request(
            publication,
            PublicationStatus.REJECTION_PENDING,
            method,
            f"{self.base_url}/cve/{publication.cve_id}/reject",
            json_body=body,
        )

        data = response.json()

        publication.status = PublicationStatus.REJECTED.value
        # published_at doubles as "has this CVE ID had any prior POST" for
        # the use_put decision above (matching the cveawg-shaped API's
        # per-CVE-ID POST-once-then-PUT semantics) — rejected_at is the
        # separate, purely informational timestamp shown in the UI.
        if not use_put:
            publication.published_at = datetime.now(UTC)
        publication.rejected_at = datetime.now(UTC)
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def abort(self, record_identifier: str) -> CnaPublication:
        publication = self.get_or_create(record_identifier)
        self._assert_can_transition(publication, PublicationStatus.ABORTED)

        publication.status = PublicationStatus.ABORTED.value
        self._save(publication)

        return publication

    # ----- internals -----

    def _assert_can_transition(
        self,
        publication: CnaPublication,
        target_status: PublicationStatus,
    ) -> None:
        allowed = ALLOWED_TRANSITIONS.get(target_status, frozenset())

        if PublicationStatus(publication.status) not in allowed:
            raise ValueError(
                f"Publication has status {publication.status} and cannot "
                f"transition to {target_status.value}.",
            )

    def _do_request(
        self,
        publication: CnaPublication,
        pending_status: PublicationStatus,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        publication.last_request = self._scrub(
            json.dumps({"params": params, "json": json_body}),
        )
        self._save(publication)

        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=self._headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            publication.status = pending_status.value
            publication.last_response = None
            publication.last_error = self._scrub(self._describe_http_status_error(exc))
            self._save(publication)
            raise
        except httpx.HTTPError as exc:
            publication.status = pending_status.value
            publication.last_response = None
            publication.last_error = self._scrub(f"{method} {url}: {exc}")
            self._save(publication)
            raise

        return response

    def _describe_http_status_error(self, exc: httpx.HTTPStatusError) -> str:
        response = exc.response

        try:
            body = json.dumps(response.json())
        except ValueError:
            body = response.text

        return f"{exc.request.method} {exc.request.url}: HTTP {response.status_code} — {body}"

    def _scrub(self, value: str) -> str:
        """Redact the configured API key from anything about to be
        persisted — an upstream error response can echo request headers
        back, so this runs on every last_error/last_request/last_response
        write. Same precedent VL states in docs/cna.md.
        """
        return value.replace(self._api_key, "[REDACTED]") if self._api_key else value

    def _save(self, publication: CnaPublication) -> None:
        db.session.add(publication)
        db.session.commit()
