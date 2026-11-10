from __future__ import annotations

from typing import Any

import httpx
import pytest
from flask import Flask
from flask.testing import FlaskClient

from vulniverse_api.api import publish as publish_module
from vulniverse_api.extensions import db
from vulniverse_api.models import VulnerabilityRecord
from vulniverse_api.services import cna_publication as service_module
from vulniverse_api.services.cna_credentials import set_credential


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request, json=self._payload),
            )

    def json(self) -> Any:
        return self._payload

    @property
    def text(self) -> str:
        return str(self._payload)


@pytest.fixture
def configured_vl(app: Flask, test_user) -> None:
    set_credential(test_user.id, "vl", {
        "cve_url": "http://test/api/cna",
        "short_name": "test-cna",
        "org_id": "TEST-ORG",
        "cve_api_org": "TEST-ORG",
        "cve_api_user": "tester@example.com",
        "cve_api_key": "key123",
    })


@pytest.fixture
def record(client: FlaskClient) -> int:
    """A record owned by the logged-in test user; publications attach to its id."""
    response = client.post(
        "/api/v1/records",
        json={
            "record": {"containers": {"cna": {"descriptions": [{"lang": "en", "value": "bug"}]}}},
            "profile": "gcve-bcp-05-1.7",
            "isDraft": True,
        },
    )
    return response.get_json()["id"]


def test_targets_endpoint_reports_configured(
    client: FlaskClient, configured_vl: None,
) -> None:
    response = client.get("/api/v1/publish/targets")

    assert response.status_code == 200
    body = response.get_json()
    assert body["vl"] == {"configured": True}
    assert body["cve-program"] == {"configured": False}


def test_unknown_target_is_404(client: FlaskClient, record: int) -> None:
    response = client.get(f"/api/v1/publish/not-a-real-target/{record}")

    assert response.status_code == 404


def test_disabled_panel_target_is_404(
    client: FlaskClient, record: int, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_load_app_config = publish_module.load_app_config

    def patched() -> dict:
        config = dict(real_load_app_config())
        config["panels"] = {**config["panels"], "vl": False}
        return config

    monkeypatch.setattr(publish_module, "load_app_config", patched)

    response = client.get(f"/api/v1/publish/vl/{record}")

    assert response.status_code == 404


def test_unconfigured_target_is_409(
    client: FlaskClient, record: int, configured_vl: None,
) -> None:
    response = client.get(f"/api/v1/publish/cve-program/{record}")

    assert response.status_code == 409


def test_get_publication_creates_local_only(
    client: FlaskClient, record: int, configured_vl: None,
) -> None:
    response = client.get(f"/api/v1/publish/vl/{record}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "LOCAL_ONLY"
    assert body["recordId"] == record
    assert body["target"] == "vl"


def test_reserve_rejects_non_integer_year(
    client: FlaskClient, record: int, configured_vl: None,
) -> None:
    response = client.post(
        f"/api/v1/publish/vl/{record}/reserve",
        json={"year": "2026"},
    )

    assert response.status_code == 400


def test_reject_requires_reason(
    client: FlaskClient, record: int, configured_vl: None,
) -> None:
    response = client.post(
        f"/api/v1/publish/vl/{record}/reject",
        json={},
    )

    assert response.status_code == 400


def test_reserve_publish_reject_happy_path(
    client: FlaskClient, record: int, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00005"}]})
        if url.endswith("/reject"):
            return FakeResponse({"state": "REJECTED"})
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    reserve_response = client.post(
        f"/api/v1/publish/vl/{record}/reserve",
        json={"year": 2026},
    )
    assert reserve_response.status_code == 200
    assert reserve_response.get_json()["status"] == "RESERVED"
    assert reserve_response.get_json()["cveId"] == "CVE-2026-00005"

    publish_response = client.post(f"/api/v1/publish/vl/{record}/publish")
    assert publish_response.status_code == 200
    assert publish_response.get_json()["status"] == "PUBLISHED"

    reject_response = client.post(
        f"/api/v1/publish/vl/{record}/reject",
        json={"reason": "duplicate of CVE-2020-0001"},
    )
    assert reject_response.status_code == 200
    assert reject_response.get_json()["status"] == "REJECTED"


def test_upstream_failure_returns_502_with_publication_state(
    client: FlaskClient, record: int, configured_vl: None, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"message": "nope"}, status_code=500)

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    response = client.post(
        f"/api/v1/publish/vl/{record}/reserve",
        json={"year": 2026},
    )

    assert response.status_code == 502
    body = response.get_json()
    assert body["publication"]["status"] == "RESERVATION_PENDING"


def test_unknown_record_is_404(client: FlaskClient, configured_vl: None) -> None:
    response = client.get("/api/v1/publish/vl/999")

    assert response.status_code == 404


def test_non_owner_cannot_act_on_a_published_record(
    app: Flask, test_user, other_client: FlaskClient,
) -> None:
    with app.app_context():
        published = VulnerabilityRecord(
            identifier="CVE-2026-00007",
            profile="cve-5.2.0",
            document={"containers": {"cna": {}}},
            is_draft=False,
            created_by_id=test_user.id,
        )
        db.session.add(published)
        db.session.commit()
        rid = published.id

    response = other_client.post(f"/api/v1/publish/vl/{rid}/reserve", json={"year": 2026})

    assert response.status_code == 403
