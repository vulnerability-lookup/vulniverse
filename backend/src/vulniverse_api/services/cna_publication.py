from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import httpx
from sqlalchemy import func

from ..extensions import db
from ..models import CnaPublication, VulnerabilityRecord
from .cna_credentials import find_instance, get_credential
from .identifiers import (
    canonical_id,
    extract_cve_identifier,
    extract_gcve_identifier,
)

REQUEST_TIMEOUT_SECONDS = 30.0

# "vl" and "cve-program" speak the identical CVE Services API-shaped
# protocol (see https://vulnerability-lookup.github.io/vulniverse/docs/embedding/vl/ and VL's own website/web/api/v1/cna.py)
# — the only difference is which per-user UserCnaCredential row supplies
# the base URL and credentials.
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
    PublicationStatus.RESERVED: frozenset(
        {
            PublicationStatus.LOCAL_ONLY,
            PublicationStatus.RESERVATION_PENDING,
        }
    ),
    PublicationStatus.PUBLISHED: frozenset(
        {
            PublicationStatus.RESERVED,
            PublicationStatus.PUBLICATION_PENDING,
            PublicationStatus.PUBLISHED,
            PublicationStatus.REJECTED,
        }
    ),
    PublicationStatus.REJECTED: frozenset(
        {
            PublicationStatus.RESERVED,
            PublicationStatus.PUBLISHED,
            PublicationStatus.REJECTION_PENDING,
        }
    ),
    PublicationStatus.ABORTED: frozenset(PublicationStatus)
    - {PublicationStatus.ABORTED},
}


class IntegrationNotConfiguredError(ValueError):
    pass


class LinkedElsewhereError(ValueError):
    """The upstream ID is already linked to another record; the API names
    it if the user may see it."""

    def __init__(self, cve_id: str, record_id: int) -> None:
        super().__init__(f"{cve_id} is already linked to another record.")
        self.cve_id = cve_id
        self.record_id = record_id


# An upstream ID's states (CVE Services' get-cve-id response).
UPSTREAM_STATES = ("RESERVED", "PUBLISHED", "REJECTED")


def _record_id_like(document: dict[str, Any], linked_id: str) -> str | None:
    """The record's own ID of the linked ID's kind, where the panel puts
    it: a GCVE ID in the advisory x_gcve entry, others in cveMetadata."""
    if linked_id.upper().startswith("GCVE-"):
        return extract_gcve_identifier(document)
    return extract_cve_identifier(document)


def _timestamp(value: Any) -> datetime | None:
    """An upstream ISO 8601 time, or None if absent or unreadable."""
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class CnaPublicationService:
    """Reserve/publish/reject a CVE against one CVE Services API-shaped
    target ("vl" or "cve-program"). Both targets are the same protocol at a
    different base_url with different credentials, so one implementation
    serves both — see KNOWN_TARGETS above.
    """

    def __init__(self, user_id: int, target: str) -> None:
        credentials = get_credential(user_id, target)

        if credentials is None:
            raise IntegrationNotConfiguredError(
                f"No CNA credentials configured for {target!r}. Set them "
                "up under your account's CNA credentials.",
            )

        instance = find_instance(target, credentials["instance"])

        if instance is None:
            raise IntegrationNotConfiguredError(
                f"The {target!r} instance in your CNA credentials isn't offered"
                " on this server (anymore); choose one under CNA credentials.",
            )

        self.target = target
        # Only operator-configured URLs (see app_config.py), never one a
        # user typed: the server mustn't be sent to arbitrary addresses.
        # httpx doesn't follow redirects either (its default); keep it so.
        self.base_url = instance["api_url"].rstrip("/")
        # Empty only where optional (Vulnerability-Lookup): then it's sent
        # nowhere (see OPTIONAL_FIELDS in cna_credentials.py).
        self.short_name = credentials["short_name"]
        self.org_id = credentials["org_id"]
        self._api_key = credentials["cve_api_key"]
        self._headers = {
            "CVE-API-ORG": credentials["cve_api_org"],
            "CVE-API-USER": credentials["cve_api_user"],
            "CVE-API-KEY": credentials["cve_api_key"],
        }

    # ----- lookups -----

    def get_or_create(self, record_id: int) -> CnaPublication:
        publication = CnaPublication.query.filter_by(
            record_id=record_id,
            target=self.target,
        ).first()

        if publication is not None:
            return publication

        publication = CnaPublication(
            record_id=record_id,
            target=self.target,
            status=PublicationStatus.LOCAL_ONLY.value,
        )

        db.session.add(publication)
        db.session.commit()

        return publication

    # ----- actions -----

    def reserve_cve_id(
        self,
        record_id: int,
        year: int,
    ) -> CnaPublication:
        publication = self.get_or_create(record_id)
        self._assert_can_transition(publication, PublicationStatus.RESERVED)

        params = {
            "cve_year": year,
            "amount": 1,
            "batch_type": "sequential",
        }
        # Without one, VL reserves the ID without an owning CNA.
        if self.short_name:
            params["short_name"] = self.short_name

        response = self._do_request(
            publication,
            PublicationStatus.RESERVATION_PENDING,
            "POST",
            f"{self.base_url}/cve-id",
            params=params,
        )

        data = response.json()

        try:
            # The real CVE Services API always populates cve_id. VL's own
            # GNA-shaped implementation of this same protocol reserves a
            # GCVE identifier instead — it returns cve_id: "" (no official
            # CVE assigned yet) with the real id under vuln_id — so fall
            # back to that when cve_id is empty, rather than treating an
            # empty string as a successfully reserved (blank) identifier.
            entry = data["cve_ids"][0]
            reserved_id = entry.get("cve_id") or entry["vuln_id"]

            if not reserved_id:
                raise KeyError("cve_id/vuln_id")
        except (KeyError, IndexError, TypeError) as exc:
            publication.status = PublicationStatus.RESERVATION_PENDING.value
            publication.last_response = self._scrub(json.dumps(data))
            publication.last_error = self._scrub(
                f"Unexpected response shape, no cve_ids[0].cve_id/vuln_id: {json.dumps(data)}",
            )
            self._save(publication)
            raise ValueError("Upstream returned no reserved identifier.") from exc

        publication.status = PublicationStatus.RESERVED.value
        # VL hands out its GCVE IDs lowercased (its internal key form).
        publication.cve_id = canonical_id(reserved_id)
        publication.reserved_at = datetime.now(UTC)
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def publish(self, record_id: int) -> CnaPublication:
        publication = self.get_or_create(record_id)
        self._assert_can_transition(publication, PublicationStatus.PUBLISHED)

        if not publication.cve_id:
            raise ValueError("Reserve a CVE ID before publishing.")

        record = db.session.get(VulnerabilityRecord, record_id)

        if record is None:
            raise ValueError(f"Unknown record: {record_id}")

        # The upstream ID comes from the link, the one users see from the
        # record: they must agree, or the record goes out under an ID it
        # doesn't show (e.g. its vulnId was edited after linking).
        in_record = _record_id_like(record.document, publication.cve_id)
        if (in_record or "").lower() != publication.cve_id.lower():
            raise ValueError(
                f"This record is linked to {publication.cve_id}, but its ID is"
                f" {in_record or 'missing'}. Set it to {publication.cve_id}"
                " before publishing."
            )

        cna_container = (record.document.get("containers") or {}).get("cna")

        if not isinstance(cna_container, dict):
            # A malformed/incomplete record, not a caller type error.
            raise ValueError("Record has no containers.cna to publish.")  # noqa: TRY004

        cna_container = self._with_default_provider_metadata(cna_container)

        body = {"cnaContainer": cna_container}
        method = "PUT" if publication.posted else "POST"

        response = self._do_request(
            publication,
            PublicationStatus.PUBLICATION_PENDING,
            method,
            f"{self.base_url}/cve/{publication.cve_id}/cna",
            json_body=body,
        )

        data = response.json()

        now = datetime.now(UTC)
        publication.status = PublicationStatus.PUBLISHED.value
        publication.posted = True
        # First publication; later ones are updates (last_sent_at).
        publication.published_at = publication.published_at or now
        publication.last_sent_at = now
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def reject(self, record_id: int, reason: str) -> CnaPublication:
        if not reason.strip():
            raise ValueError("A rejection reason is required.")

        publication = self.get_or_create(record_id)
        self._assert_can_transition(publication, PublicationStatus.REJECTED)

        if not publication.cve_id:
            raise ValueError("Publication has no reserved CVE ID.")

        # providerMetadata as in publish(): the CVE schema's rejected
        # container requires it, and VL's reject handler fails without it.
        body = {
            "cnaContainer": self._with_default_provider_metadata(
                {"rejectedReasons": [{"lang": "en", "value": reason.strip()}]}
            ),
        }
        method = "PUT" if publication.posted else "POST"

        response = self._do_request(
            publication,
            PublicationStatus.REJECTION_PENDING,
            method,
            f"{self.base_url}/cve/{publication.cve_id}/reject",
            json_body=body,
        )

        data = response.json()

        now = datetime.now(UTC)
        publication.status = PublicationStatus.REJECTED.value
        publication.posted = True
        publication.rejected_at = now
        publication.last_sent_at = now
        publication.last_response = self._scrub(json.dumps(data))
        publication.last_error = None
        self._save(publication)

        return publication

    def unlink(self, record_id: int) -> CnaPublication:
        """Forget the link to upstream entirely (the ID stays there): the
        record is back to LOCAL_ONLY and can reserve or pull anew. Unlike
        abort(), which keeps the link as ABORTED for good."""
        CnaPublication.query.filter_by(record_id=record_id, target=self.target).delete()
        db.session.commit()

        return self.get_or_create(record_id)

    def abort(self, record_id: int) -> CnaPublication:
        publication = self.get_or_create(record_id)
        self._assert_can_transition(publication, PublicationStatus.ABORTED)

        publication.status = PublicationStatus.ABORTED.value
        self._save(publication)

        return publication

    def pull(
        self, record_id: int, cve_id: str
    ) -> tuple[CnaPublication, dict[str, Any] | None]:
        """Link the record to an existing upstream ID and take over its
        state (RESERVED/PUBLISHED/REJECTED): after a lost link (e.g. the
        record was deleted and recreated), an uncertain *_PENDING state,
        or to import a record made elsewhere. Returns the upstream record
        too, unless only reserved; the caller decides what to do with it
        (the editor shows it as unsaved changes). Who owns the ID upstream
        isn't checked: the instance is one the operator configured and
        the credentials are for."""
        cve_id = canonical_id(cve_id.strip())
        publication = self.get_or_create(record_id)

        if publication.cve_id and publication.cve_id.lower() != cve_id.lower():
            raise ValueError(
                f"This record is linked to {publication.cve_id};"
                " pull that one, or use another record."
            )

        elsewhere = CnaPublication.query.filter(
            CnaPublication.target == self.target,
            func.lower(CnaPublication.cve_id) == cve_id.lower(),
            CnaPublication.record_id != record_id,
        ).first()
        if elsewhere is not None:
            raise LinkedElsewhereError(cve_id, elsewhere.record_id)

        entry = self._get(f"/cve-id/{cve_id}")
        state = entry.get("state")
        if state not in UPSTREAM_STATES:
            raise ValueError(
                f"Upstream reports an unknown state for {cve_id}: {state!r}."
            )

        record = None if state == "RESERVED" else self._get(f"/cve/{cve_id}")
        metadata = (record or {}).get("cveMetadata") or {}

        publication.cve_id = cve_id
        publication.status = state
        publication.reserved_at = (
            _timestamp(entry.get("reserved")) or publication.reserved_at
        )
        # Upstream's dates win: it's the record of what happened there.
        # Published or rejected, upstream has the record: next is a PUT.
        publication.posted = state != "RESERVED"
        published = _timestamp(metadata.get("datePublished"))
        if state == "PUBLISHED":
            publication.published_at = (
                published or publication.published_at or datetime.now(UTC)
            )
        else:
            # A rejected ID may never have been published.
            publication.published_at = published
        if state == "REJECTED":
            publication.rejected_at = (
                _timestamp(metadata.get("dateRejected"))
                or publication.rejected_at
                or datetime.now(UTC)
            )
        publication.last_sent_at = (
            _timestamp(metadata.get("dateUpdated"))
            or publication.rejected_at
            or publication.published_at
            if state != "RESERVED"
            else None
        )
        publication.last_response = self._scrub(json.dumps(entry))
        publication.last_error = None
        self._save(publication)

        return publication, record

    def upstream_record(self, record_id: int) -> dict[str, Any]:
        """The record upstream has for the linked ID, to compare with the
        local one. Read only: no status or date changes."""
        publication = self.get_or_create(record_id)

        if not publication.cve_id:
            raise ValueError("This record isn't linked to an upstream ID.")

        return self._get(f"/cve/{publication.cve_id}")

    # ----- internals -----

    def _get(self, path: str) -> dict[str, Any]:
        """A read from the configured instance; LookupError on 404."""
        response = httpx.get(
            f"{self.base_url}{path}",
            headers=self._headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            raise LookupError(f"{path.rsplit('/', 1)[-1]} wasn't found upstream.")
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            # A bad upstream answer, not a caller type error.
            raise ValueError("Upstream answered with something unexpected.")  # noqa: TRY004
        return data

    def _with_default_provider_metadata(
        self,
        cna_container: dict[str, Any],
    ) -> dict[str, Any]:
        """The target's publish endpoint requires providerMetadata.orgId
        (a plain CVE Record Format requirement — see
        definitions.providerMetadata in the upstream schema) and rejects
        the request outright without it. Default it from this target's
        own configured credentials when the record doesn't already
        supply one, rather than failing publish over a field most
        records won't think to set by hand. Applied to the outgoing
        request only — never persisted back into the stored record, so
        the record you're editing is untouched either way.
        """
        provider_metadata = cna_container.get("providerMetadata")

        if isinstance(provider_metadata, dict) and provider_metadata.get("orgId"):
            return cna_container

        return {
            **cna_container,
            "providerMetadata": {
                **(provider_metadata if isinstance(provider_metadata, dict) else {}),
                # Optional for Vulnerability-Lookup: only what's configured
                # (VL needs providerMetadata itself, even empty).
                **({"orgId": self.org_id} if self.org_id else {}),
                **({"shortName": self.short_name} if self.short_name else {}),
            },
        }

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
