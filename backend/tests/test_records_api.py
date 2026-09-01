from __future__ import annotations

from typing import Any


def minimal_cve_record(cve_id: str) -> dict[str, Any]:
    return {
        "dataType": "CVE_RECORD",
        "dataVersion": "5.2.0",
        "cveMetadata": {
            "cveId": cve_id,
            "assignerOrgId": "11111111-1111-4111-9111-111111111111",
            "state": "PUBLISHED",
        },
        "containers": {
            "cna": {
                "providerMetadata": {
                    "orgId": "11111111-1111-4111-9111-111111111111",
                },
                "descriptions": [
                    {"lang": "en", "value": "A test vulnerability description."},
                ],
                "affected": [
                    {
                        "vendor": "Acme",
                        "product": "Widget",
                        "defaultStatus": "affected",
                    },
                ],
                "references": [{"url": "https://example.com/advisory"}],
            },
        },
    }


def create_draft(client, cve_id: str, profile: str = "cve-5.2.0"):
    return client.post(
        "/api/v1/records",
        json={
            "record": minimal_cve_record(cve_id),
            "profile": profile,
            "isDraft": True,
        },
    )


def test_list_records_is_empty_with_no_records(client) -> None:
    response = client.get("/api/v1/records")

    assert response.status_code == 200
    assert response.get_json() == {"records": []}


def test_list_records_returns_created_records(client) -> None:
    create_draft(client, "CVE-2026-00001")
    create_draft(client, "CVE-2026-00002", profile="gcve-bcp-05-1.7")

    response = client.get("/api/v1/records")

    assert response.status_code == 200

    records = response.get_json()["records"]
    identifiers = {record["identifier"] for record in records}

    assert identifiers == {"CVE-2026-00001", "CVE-2026-00002"}

    by_identifier = {record["identifier"]: record for record in records}

    assert by_identifier["CVE-2026-00002"]["profile"] == "gcve-bcp-05-1.7"
    assert by_identifier["CVE-2026-00001"]["isDraft"] is True
    assert "updatedAt" in by_identifier["CVE-2026-00001"]

    # The list is summary data only — it must not embed the full
    # record document (fetched separately via GET /records/<id>).
    assert "record" not in by_identifier["CVE-2026-00001"]


def test_list_records_orders_most_recently_updated_first(client) -> None:
    create_draft(client, "CVE-2026-00001")
    create_draft(client, "CVE-2026-00002")

    response = client.get("/api/v1/records")
    identifiers = [
        record["identifier"] for record in response.get_json()["records"]
    ]

    assert identifiers == ["CVE-2026-00002", "CVE-2026-00001"]


def test_delete_record_removes_it(client) -> None:
    create_draft(client, "CVE-2026-00001")

    response = client.delete("/api/v1/records/CVE-2026-00001")

    assert response.status_code == 200

    remaining = client.get("/api/v1/records").get_json()["records"]

    assert remaining == []


def test_delete_unknown_record_returns_404(client) -> None:
    response = client.delete("/api/v1/records/CVE-2026-00001")

    assert response.status_code == 404


def test_update_record_allows_adding_vulnid_alongside_existing_cveid(client) -> None:
    create_draft(client, "CVE-2026-00001")

    document = minimal_cve_record("CVE-2026-00001")
    document["cveMetadata"]["vulnId"] = "GCVE-0-2026-00001"

    response = client.put(
        "/api/v1/records/CVE-2026-00001",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 200
    assert response.get_json()["record"]["cveMetadata"]["vulnId"] == "GCVE-0-2026-00001"


def test_update_record_allows_removing_vulnid_when_cveid_still_matches(client) -> None:
    # Record is created (and thus identified) via cveId alone — adding a
    # vulnId later, then removing it again, must not disturb that.
    create_draft(client, "CVE-2026-00002")

    document = minimal_cve_record("CVE-2026-00002")
    document["cveMetadata"]["vulnId"] = "GCVE-0-2026-00002"

    client.put(
        "/api/v1/records/CVE-2026-00002",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    del document["cveMetadata"]["vulnId"]

    response = client.put(
        "/api/v1/records/CVE-2026-00002",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 200
    assert "vulnId" not in response.get_json()["record"]["cveMetadata"]


def test_update_record_rejects_real_identifier_change(client) -> None:
    create_draft(client, "CVE-2026-00003")

    document = minimal_cve_record("CVE-2026-99999")

    response = client.put(
        "/api/v1/records/CVE-2026-00003",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 400
    assert "cannot be changed" in response.get_json()["message"]


def test_update_record_rejects_when_all_identifying_fields_removed(client) -> None:
    create_draft(client, "CVE-2026-00004")

    document = minimal_cve_record("CVE-2026-00004")
    del document["cveMetadata"]["cveId"]

    response = client.put(
        "/api/v1/records/CVE-2026-00004",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 400
    assert "cannot be changed" in response.get_json()["message"]
