from __future__ import annotations

from flask import Flask

from vulniverse_api.models import User
from vulniverse_api.services.cna_credentials import get_credential

VALID_PAYLOAD = {
    "cveUrl": "http://test/api/cna",
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
    response = client.put("/api/v1/cna-credentials/not-a-real-target", json=VALID_PAYLOAD)

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
    app: Flask, client, test_user: User,
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
