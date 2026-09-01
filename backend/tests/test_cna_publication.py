from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from flask import Flask

from vulniverse_api.extensions import db
from vulniverse_api.models import VulnerabilityRecord
from vulniverse_api.services import cna_publication as service_module
from vulniverse_api.services.cna_publication import (
    CnaPublicationService,
    IntegrationNotConfiguredError,
    PublicationStatus,
)

API_KEY = "super-secret-key"


class FakeResponse:
    def __init__(
        self,
        payload: Any,
        status_code: int = 200,
        method: str = "POST",
        url: str = "http://test/cve-id",
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request(method, url)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(
                    self.status_code,
                    request=self.request,
                    json=self._payload,
                ),
            )

    def json(self) -> Any:
        return self._payload

    @property
    def text(self) -> str:
        return json.dumps(self._payload)


@pytest.fixture
def configured_vl(monkeypatch: pytest.MonkeyPatch) -> None:
    # cna_publication.py does `from .app_config import get_integration`, so
    # the name to patch is the one bound in *this* module, not the
    # originating app_config module.
    monkeypatch.setattr(
        service_module,
        "get_integration",
        lambda target: {
            "cve_url": "http://test/api/cna",
            "short_name": "test-cna",
            "org_id": "TEST-ORG",
            "cve_api_org": "TEST-ORG",
            "cve_api_user": "tester@example.com",
            "cve_api_key": API_KEY,
        }
        if target == "vl"
        else None,
    )


def test_raises_when_target_not_configured(configured_vl: None) -> None:
    with pytest.raises(IntegrationNotConfiguredError):
        CnaPublicationService("cve-program")


def test_reserve_success(app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        assert method == "POST"
        assert url == "http://test/api/cna/cve-id"
        return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00001", "reserved": "2026-01-01T00:00:00Z"}]})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")
    publication = service.reserve_cve_id("GCVE-0-2026-00001", 2026)

    assert publication.status == PublicationStatus.RESERVED.value
    assert publication.cve_id == "CVE-2026-00001"
    assert publication.reserved_at is not None
    assert publication.last_error is None


def test_reserve_falls_back_to_vuln_id_when_cve_id_blank(
    app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # VL's own GNA-shaped reservation response: no official CVE assigned
    # yet (cve_id is blank), the real identifier is the GCVE-format vuln_id.
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({
            "cve_ids": [{"cve_id": "", "vuln_id": "GCVE-0-2026-00099"}],
        })

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")
    publication = service.reserve_cve_id("GCVE-0-2026-00099", 2026)

    assert publication.status == PublicationStatus.RESERVED.value
    assert publication.cve_id == "GCVE-0-2026-00099"


def test_reserve_fails_when_neither_cve_id_nor_vuln_id_present(
    app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"cve_ids": [{"cve_id": ""}]})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")

    with pytest.raises(ValueError, match="no reserved identifier"):
        service.reserve_cve_id("GCVE-0-2026-00098", 2026)


def test_reserve_upstream_error_sets_pending_and_scrubs_key(
    app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse(
            {"message": f"bad credentials for key {API_KEY}"},
            status_code=403,
        )

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")

    with pytest.raises(httpx.HTTPStatusError):
        service.reserve_cve_id("GCVE-0-2026-00002", 2026)

    publication = service.get_or_create("GCVE-0-2026-00002")

    assert publication.status == PublicationStatus.RESERVATION_PENDING.value
    assert publication.last_error is not None
    assert API_KEY not in publication.last_error
    assert "[REDACTED]" in publication.last_error


def test_publish_before_reserve_is_blocked(app: Flask, configured_vl: None) -> None:
    # LOCAL_ONLY isn't in ALLOWED_TRANSITIONS[PUBLISHED] — the transition
    # guard rejects this before the cve_id check is ever reached.
    service = CnaPublicationService("vl")

    with pytest.raises(ValueError, match="cannot transition"):
        service.publish("GCVE-0-2026-00003")


def test_publish_success(app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch) -> None:
    record = VulnerabilityRecord(
        identifier="GCVE-0-2026-00004",
        profile="gcve-bcp-05-1.7",
        document={
            "containers": {
                "cna": {"descriptions": [{"lang": "en", "value": "A bug."}]},
            },
        },
        is_draft=False,
    )
    db.session.add(record)
    db.session.commit()

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00004"}]})

        assert url == "http://test/api/cna/cve/CVE-2026-00004/cna"
        assert kwargs["json"] == {
            "cnaContainer": {
                "descriptions": [{"lang": "en", "value": "A bug."}],
                "providerMetadata": {"orgId": "TEST-ORG", "shortName": "test-cna"},
            },
        }
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")
    service.reserve_cve_id("GCVE-0-2026-00004", 2026)
    publication = service.publish("GCVE-0-2026-00004")

    assert publication.status == PublicationStatus.PUBLISHED.value
    assert publication.published_at is not None


def test_publish_does_not_override_existing_provider_metadata(
    app: Flask, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = VulnerabilityRecord(
        identifier="GCVE-0-2026-00009",
        profile="gcve-bcp-05-1.7",
        document={
            "containers": {
                "cna": {
                    "descriptions": [{"lang": "en", "value": "A bug."}],
                    "providerMetadata": {"orgId": "real-uuid-1234", "shortName": "Acme"},
                },
            },
        },
        is_draft=False,
    )
    db.session.add(record)
    db.session.commit()

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00009"}]})

        assert kwargs["json"]["cnaContainer"]["providerMetadata"] == {
            "orgId": "real-uuid-1234",
            "shortName": "Acme",
        }
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    service = CnaPublicationService("vl")
    service.reserve_cve_id("GCVE-0-2026-00009", 2026)
    service.publish("GCVE-0-2026-00009")


def test_reject_requires_nonempty_reason(app: Flask, configured_vl: None) -> None:
    service = CnaPublicationService("vl")

    with pytest.raises(ValueError, match="rejection reason"):
        service.reject("GCVE-0-2026-00005", "   ")


def test_reject_before_reserve_is_blocked(app: Flask, configured_vl: None) -> None:
    service = CnaPublicationService("vl")

    with pytest.raises(ValueError, match="cannot transition"):
        service.reject("GCVE-0-2026-00006", "duplicate of CVE-2020-0001")


def test_abort_from_local_only(app: Flask, configured_vl: None) -> None:
    service = CnaPublicationService("vl")
    publication = service.abort("GCVE-0-2026-00007")

    assert publication.status == PublicationStatus.ABORTED.value


def test_abort_twice_is_blocked(app: Flask, configured_vl: None) -> None:
    service = CnaPublicationService("vl")
    service.abort("GCVE-0-2026-00008")

    with pytest.raises(ValueError, match="cannot transition"):
        service.abort("GCVE-0-2026-00008")
