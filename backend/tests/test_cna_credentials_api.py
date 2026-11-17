from __future__ import annotations

from flask import Flask

from vulniverse_api.app_config import publish_instances_problem
from vulniverse_api.models import User
from vulniverse_api.services.cna_credentials import get_credential

VALID_PAYLOAD = {
    "instance": "test",
    "shortName": "test-cna",
    "orgId": "TEST-ORG",
    "cveApiOrg": "TEST-ORG",
    "cveApiUser": "tester@example.com",
    "cveApiKey": "super-secret-key",
}


def test_get_credentials_starts_empty(client) -> None:
    response = client.get("/api/v1/cna-credentials")

    assert response.status_code == 200
    assert response.get_json() == {}


def test_put_unknown_target_is_404(client) -> None:
    response = client.put(
        "/api/v1/cna-credentials/not-a-real-target", json=VALID_PAYLOAD
    )

    assert response.status_code == 404


def test_put_rejects_incomplete_payload(client) -> None:
    incomplete = dict(VALID_PAYLOAD)
    del incomplete["cveApiKey"]

    response = client.put("/api/v1/cna-credentials/vl", json=incomplete)

    assert response.status_code == 400


def test_put_then_get_does_not_leak_api_key(client) -> None:
    put_response = client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)
    assert put_response.status_code == 200
    assert "cveApiKey" not in put_response.get_json()

    get_response = client.get("/api/v1/cna-credentials")
    body = get_response.get_json()

    assert "vl" in body
    assert body["vl"]["shortName"] == "test-cna"
    assert "cveApiKey" not in body["vl"]


def test_put_overwrites_existing_credential(client) -> None:
    client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)

    updated = dict(VALID_PAYLOAD, shortName="renamed-cna")
    response = client.put("/api/v1/cna-credentials/vl", json=updated)

    assert response.status_code == 200
    assert response.get_json()["shortName"] == "renamed-cna"


def test_delete_credential(client) -> None:
    client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)

    delete_response = client.delete("/api/v1/cna-credentials/vl")
    assert delete_response.status_code == 200

    get_response = client.get("/api/v1/cna-credentials")
    assert get_response.get_json() == {}


def test_delete_unconfigured_target_is_404(client) -> None:
    response = client.delete("/api/v1/cna-credentials/vl")

    assert response.status_code == 404


def test_update_without_key_keeps_existing_key(
    app: Flask,
    client,
    test_user: User,
) -> None:
    client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)

    updated = dict(VALID_PAYLOAD, shortName="renamed-cna", cveApiKey="")
    response = client.put("/api/v1/cna-credentials/vl", json=updated)

    assert response.status_code == 200
    assert response.get_json()["shortName"] == "renamed-cna"

    credential = get_credential(test_user.id, "vl")

    assert credential is not None
    assert credential["cve_api_key"] == VALID_PAYLOAD["cveApiKey"]


def test_credentials_require_login(anon_client) -> None:
    response = anon_client.get("/api/v1/cna-credentials")

    assert response.status_code == 401


# --- Instances: only the operator chooses where publishing goes ---------------


def two_instances(app: Flask) -> None:
    app.config["VULNIVERSE_PUBLISH_INSTANCES"] = {
        "vl": [
            {"id": "test", "name": "Test VL", "api_url": "http://test/api/cna"},
            {"id": "other", "name": "Other VL", "api_url": "https://other/api/cna"},
        ]
    }


def test_instances_lists_what_the_operator_configured(app, client) -> None:
    two_instances(app)

    body = client.get("/api/v1/cna-credentials/instances").get_json()

    assert body["vl"] == [
        {"id": "test", "name": "Test VL", "url": "http://test/api/cna"},
        {"id": "other", "name": "Other VL", "url": "https://other/api/cna"},
    ]
    assert body["cve-program"] == []


def test_an_instance_not_configured_is_refused(client) -> None:
    response = client.put(
        "/api/v1/cna-credentials/vl",
        json=dict(VALID_PAYLOAD, instance="http://169.254.169.254"),
    )

    assert response.status_code == 400
    assert "Unknown instance" in response.get_json()["message"]


def test_changing_the_instance_needs_the_key_again(app, client, test_user) -> None:
    two_instances(app)
    client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)
    without_key = {k: v for k, v in VALID_PAYLOAD.items() if k != "cveApiKey"}

    moved = client.put(
        "/api/v1/cna-credentials/vl", json=dict(without_key, instance="other")
    )
    assert moved.status_code == 400
    assert get_credential(test_user.id, "vl")["instance"] == "test"  # type: ignore[index]

    rekeyed = client.put(
        "/api/v1/cna-credentials/vl",
        json=dict(VALID_PAYLOAD, instance="other", cveApiKey="other-key"),
    )
    assert rekeyed.status_code == 200
    assert get_credential(test_user.id, "vl")["cve_api_key"] == "other-key"  # type: ignore[index]


def test_an_instance_removed_from_the_config_stops_publishing(
    app, client, test_user
) -> None:
    client.put("/api/v1/cna-credentials/vl", json=VALID_PAYLOAD)
    record = client.post(
        "/api/v1/records",
        json={"record": {}, "profile": "gcve-bcp-05-1.7", "isDraft": True},
    ).get_json()["id"]
    app.config["VULNIVERSE_PUBLISH_INSTANCES"] = {"vl": []}

    response = client.get(f"/api/v1/publish/vl/{record}")

    assert response.status_code == 409
    assert "isn't offered" in response.get_json()["message"]


def test_the_config_check_catches_bad_instances() -> None:
    def problem(entries: list) -> str | None:
        return publish_instances_problem({"vl": entries})

    good = {"id": "a", "name": "A", "api_url": "https://a/api"}
    assert problem([good]) is None
    assert "id, name and api_url" in str(problem([{"id": "a", "name": "A"}]))
    assert "http(s)" in str(problem([dict(good, api_url="file:///etc/passwd")]))
    assert "used twice" in str(problem([good, good]))
