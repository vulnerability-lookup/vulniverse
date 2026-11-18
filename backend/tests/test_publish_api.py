from __future__ import annotations

from typing import Any

import httpx
import pytest
from flask import Flask
from flask.testing import FlaskClient
from test_record_validation import gcve_only_record, minimal_gcve_record

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
                response=httpx.Response(
                    self.status_code, request=self.request, json=self._payload
                ),
            )

    def json(self) -> Any:
        return self._payload

    @property
    def text(self) -> str:
        return str(self._payload)


@pytest.fixture
def configured_vl(app: Flask, test_user) -> None:
    set_credential(
        test_user.id,
        "vl",
        {
            "instance": "test",
            "short_name": "test-cna",
            "org_id": "TEST-ORG",
            "cve_api_org": "TEST-ORG",
            "cve_api_user": "tester@example.com",
            "cve_api_key": "key123",
        },
    )


@pytest.fixture
def record(client: FlaskClient) -> int:
    """A record owned by the logged-in test user; publications attach to its id."""
    response = client.post(
        "/api/v1/records",
        json={
            "record": {
                "containers": {
                    "cna": {"descriptions": [{"lang": "en", "value": "bug"}]}
                }
            },
            "profile": "gcve-bcp-05-1.7",
            "isDraft": True,
        },
    )
    return response.get_json()["id"]


def test_targets_endpoint_reports_configured(
    client: FlaskClient,
    configured_vl: None,
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
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
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
    client: FlaskClient,
    record: int,
    configured_vl: None,
) -> None:
    response = client.get(f"/api/v1/publish/cve-program/{record}")

    assert response.status_code == 409


def test_get_publication_creates_local_only(
    client: FlaskClient,
    record: int,
    configured_vl: None,
) -> None:
    response = client.get(f"/api/v1/publish/vl/{record}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "LOCAL_ONLY"
    assert body["recordId"] == record
    assert body["target"] == "vl"


def test_reserve_rejects_non_integer_year(
    client: FlaskClient,
    record: int,
    configured_vl: None,
) -> None:
    response = client.post(
        f"/api/v1/publish/vl/{record}/reserve",
        json={"year": "2026"},
    )

    assert response.status_code == 400


def test_reject_requires_reason(
    client: FlaskClient,
    record: int,
    configured_vl: None,
) -> None:
    response = client.post(
        f"/api/v1/publish/vl/{record}/reject",
        json={},
    )

    assert response.status_code == 400


@pytest.fixture
def valid_record(client: FlaskClient) -> dict[str, Any]:
    """A saved, fully valid record, as {id, version}."""
    response = client.post(
        "/api/v1/records",
        json={
            "record": minimal_gcve_record(recordType="advisory"),
            "profile": "gcve-bcp-05-1.7",
            "isDraft": False,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_reserve_publish_reject_happy_path(
    client: FlaskClient,
    valid_record: dict[str, Any],
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00001"}]})
        if url.endswith("/reject"):
            return FakeResponse({"state": "REJECTED"})
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)

    record = valid_record["id"]
    reserve_response = client.post(
        f"/api/v1/publish/vl/{record}/reserve",
        json={"year": 2026},
    )
    assert reserve_response.status_code == 200
    assert reserve_response.get_json()["status"] == "RESERVED"
    assert reserve_response.get_json()["cveId"] == "CVE-2026-00001"

    publish_response = client.post(
        f"/api/v1/publish/vl/{record}/publish",
        json={"version": valid_record["version"]},
    )
    assert publish_response.status_code == 200
    assert publish_response.get_json()["status"] == "PUBLISHED"

    reject_response = client.post(
        f"/api/v1/publish/vl/{record}/reject",
        json={"reason": "duplicate of CVE-2020-0001"},
    )
    assert reject_response.status_code == 200
    assert reject_response.get_json()["status"] == "REJECTED"


def test_upstream_failure_returns_502_with_publication_state(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
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
    app: Flask,
    test_user,
    organisation,
    other_client: FlaskClient,
) -> None:
    with app.app_context():
        published = VulnerabilityRecord(
            identifier="CVE-2026-00007",
            profile="cve-5.2.0",
            document={"containers": {"cna": {}}},
            is_draft=False,
            organisation_id=organisation.id,
            created_by_id=test_user.id,
        )
        db.session.add(published)
        db.session.commit()
        rid = published.id

    response = other_client.post(
        f"/api/v1/publish/vl/{rid}/reserve", json={"year": 2026}
    )

    assert response.status_code == 403


# --- What goes out: the version the user saw, and only a valid one ------------


def reserved(client: FlaskClient, record: int, monkeypatch) -> list[str]:
    """Reserve an ID; returns the list upstream calls get recorded in."""
    calls: list[str] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append(url)
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00005"}]})
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)
    client.post(f"/api/v1/publish/vl/{record}/reserve", json={"year": 2026})
    calls.clear()
    return calls


def test_publishing_an_outdated_version_is_refused(
    client: FlaskClient,
    valid_record: dict[str, Any],
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = valid_record["id"]
    calls = reserved(client, record, monkeypatch)
    # Someone saves after the editor loaded version 1.
    client.put(
        f"/api/v1/records/{record}",
        json={"record": minimal_gcve_record(recordType="advisory"), "isDraft": False},
    )

    response = client.post(
        f"/api/v1/publish/vl/{record}/publish",
        json={"version": valid_record["version"]},
    )

    assert response.status_code == 409
    assert response.get_json()["code"] == "CHANGED_MEANWHILE"
    assert calls == []


def test_an_invalid_draft_is_not_published(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = reserved(client, record, monkeypatch)

    response = client.post(f"/api/v1/publish/vl/{record}/publish")

    assert response.status_code == 422
    assert response.get_json()["errors"]
    assert calls == []


# --- Pulling an ID and its state from upstream --------------------------------


def upstream(
    monkeypatch: pytest.MonkeyPatch,
    state: str | None,
    owner: str = "test-cna",
    record: dict[str, Any] | None = None,
) -> list[str]:
    """Fake GETs: the ID in `state` (None: unknown upstream), owned by
    `owner`, with `record`. Returns the URLs asked for."""
    asked: list[str] = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        asked.append(url)
        if state is None:
            return FakeResponse({"message": "not found"}, status_code=404)
        if "/cve-id/" in url:
            return FakeResponse(
                {
                    "cve_id": "CVE-2026-0042",
                    "owning_cna": owner,
                    "state": state,
                    "reserved": "2026-01-02T03:04:05.000Z",
                }
            )
        return FakeResponse(record or {})

    monkeypatch.setattr(service_module.httpx, "get", fake_get)
    return asked


def pull(client: FlaskClient, record: int, cve_id: str = "cve-2026-0042"):
    return client.post(f"/api/v1/publish/vl/{record}/pull", json={"cveId": cve_id})


def test_pulling_a_published_id_takes_over_its_state_and_record(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream_record = {
        "cveMetadata": {"state": "PUBLISHED", "datePublished": "2026-02-03T00:00:00"},
        "containers": {"cna": {"title": "From upstream"}},
    }
    upstream(monkeypatch, "PUBLISHED", record=upstream_record)

    response = pull(client, record)

    assert response.status_code == 200
    body = response.get_json()
    assert body["record"] == upstream_record
    publication = body["publication"]
    assert publication["cveId"] == "CVE-2026-0042"
    assert publication["status"] == "PUBLISHED"
    assert publication["reservedAt"].startswith("2026-01-02T03:04:05")
    assert publication["publishedAt"].startswith("2026-02-03")

    # Upstream has it already: an update is a PUT, not a second POST.
    methods: list[str] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        methods.append(method)
        return FakeResponse({})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)
    client.post(f"/api/v1/publish/vl/{record}/reject", json={"reason": "dup"})
    assert methods == ["PUT"]


def test_pulling_a_reserved_id_does_not_fetch_a_record(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked = upstream(monkeypatch, "RESERVED")

    body = pull(client, record).get_json()

    assert body["record"] is None
    assert body["publication"]["status"] == "RESERVED"
    assert len(asked) == 1


def test_the_ids_owner_upstream_does_not_matter(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream(monkeypatch, "PUBLISHED", owner="someone-else")

    response = pull(client, record)

    assert response.status_code == 200
    assert response.get_json()["publication"]["cveId"] == "CVE-2026-0042"


def test_an_unknown_id_is_404(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream(monkeypatch, None)

    assert pull(client, record).status_code == 404


def test_a_record_keeps_its_one_link(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream(monkeypatch, "RESERVED")
    pull(client, record)

    response = pull(client, record, "CVE-2026-0099")

    assert response.status_code == 400
    assert "linked to CVE-2026-0042" in response.get_json()["message"]


def test_an_id_links_to_one_record_only(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream(monkeypatch, "RESERVED")
    pull(client, record)
    second = client.post(
        "/api/v1/records",
        json={"record": {}, "profile": "gcve-bcp-05-1.7", "isDraft": True},
    ).get_json()["id"]

    response = pull(client, second)

    assert response.status_code == 400
    # Named, as the user may see it (a draft of their own organisation).
    assert f"linked to record #{record}" in response.get_json()["message"]


def test_a_gcve_only_record_can_be_published(
    client: FlaskClient,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No CVE ID, assigner or providerMetadata: VL fills in the metadata,
    and providerMetadata comes from the credentials when sending."""
    created = client.post(
        "/api/v1/records",
        json={
            "record": gcve_only_record(),
            "profile": "gcve-bcp-05-1.7",
            "isDraft": False,
        },
    )
    assert created.status_code == 201, created.get_json()
    record = created.get_json()["id"]
    sent: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse(
                {"cve_ids": [{"cve_id": "", "vuln_id": "gcve-1-2026-0007"}]}
            )
        sent.append(kwargs["json"])
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)
    client.post(f"/api/v1/publish/vl/{record}/reserve", json={"year": 2026})

    response = client.post(f"/api/v1/publish/vl/{record}/publish")

    assert response.status_code == 200, response.get_json()
    assert sent[0]["cnaContainer"]["providerMetadata"]["orgId"] == "TEST-ORG"


def test_without_short_name_and_org_id_vl_gets_neither(
    app: Flask,
    client: FlaskClient,
    test_user,
    valid_record: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    set_credential(
        test_user.id,
        "vl",
        {
            "instance": "test",
            "short_name": "",
            "org_id": "",
            "cve_api_org": "TEST-ORG",
            "cve_api_user": "tester@example.com",
            "cve_api_key": "key123",
        },
    )
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        calls.append(kwargs)
        if url.endswith("/cve-id"):
            return FakeResponse({"cve_ids": [{"cve_id": "CVE-2026-00001"}]})
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)
    record = valid_record["id"]
    client.post(f"/api/v1/publish/vl/{record}/reserve", json={"year": 2026})
    # The record has a providerMetadata: drop it to see what's filled in.
    client.put(
        f"/api/v1/records/{record}",
        json={
            "record": {
                **minimal_gcve_record(recordType="advisory"),
                "containers": {
                    "cna": {
                        k: v
                        for k, v in minimal_gcve_record(recordType="advisory")[
                            "containers"
                        ]["cna"].items()
                        if k != "providerMetadata"
                    }
                },
            },
            "isDraft": False,
        },
    )
    client.post(f"/api/v1/publish/vl/{record}/publish")

    assert "short_name" not in calls[0]["params"]
    # VL needs providerMetadata itself, even with nothing in it.
    assert calls[1]["json"]["cnaContainer"]["providerMetadata"] == {}


# --- The record's ID must be the linked one ------------------------------------


def test_a_record_showing_another_cve_id_is_not_published(
    client: FlaskClient,
    valid_record: dict[str, Any],
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = valid_record["id"]
    calls = reserved(client, record, monkeypatch)  # links CVE-2026-00005

    response = client.post(f"/api/v1/publish/vl/{record}/publish")

    assert response.status_code == 400
    assert (
        "linked to CVE-2026-00005, but its ID is CVE-2026-00001"
        in (response.get_json()["message"])
    )
    assert calls == []


def test_a_gcve_id_changed_after_linking_is_not_published(
    client: FlaskClient,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A record's own identifier can't change once saved, but an ID of the
    other kind can: here a CVE record linked to a GCVE ID at VL."""
    document = minimal_gcve_record(vulnId="GCVE-1-2026-0007", recordType="advisory")
    record = client.post(
        "/api/v1/records",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": False},
    ).get_json()["id"]
    sent: list[str] = []

    def fake_request(method: str, url: str, **kwargs: Any) -> FakeResponse:
        if url.endswith("/cve-id"):
            return FakeResponse(
                {"cve_ids": [{"cve_id": "", "vuln_id": "gcve-1-2026-0007"}]}
            )
        sent.append(url)
        return FakeResponse({"state": "PUBLISHED"})

    monkeypatch.setattr(service_module.httpx, "request", fake_request)
    client.post(f"/api/v1/publish/vl/{record}/reserve", json={"year": 2026})
    document["containers"]["cna"]["x_gcve"][0]["vulnId"] = "GCVE-1-2026-0008"
    saved = client.put(
        f"/api/v1/records/{record}", json={"record": document, "isDraft": False}
    )
    assert saved.status_code == 200, saved.get_json()

    response = client.post(f"/api/v1/publish/vl/{record}/publish")

    assert response.status_code == 400
    assert (
        "linked to GCVE-1-2026-0007, but its ID is GCVE-1-2026-0008"
        in (response.get_json()["message"])
    )
    assert sent == []


# --- Stop tracking: the link goes, the ID stays upstream ------------------------


def test_stop_tracking_removes_the_link(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream(monkeypatch, "PUBLISHED", record={"containers": {"cna": {}}})
    pull(client, record)

    response = client.delete(f"/api/v1/publish/vl/{record}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "LOCAL_ONLY"
    assert body["cveId"] is None
    assert body["publishedAt"] is None
    # Free again: the record links anew.
    assert pull(client, record).status_code == 200


def test_stop_tracking_also_frees_an_aborted_record(
    client: FlaskClient,
    record: int,
    configured_vl: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client.post(f"/api/v1/publish/vl/{record}/abort")

    client.delete(f"/api/v1/publish/vl/{record}")

    calls = reserved(client, record, monkeypatch)
    status = client.get(f"/api/v1/publish/vl/{record}").get_json()
    assert status["status"] == "RESERVED"
    assert calls == []
