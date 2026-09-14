from __future__ import annotations

from typing import Any

from vulniverse_api.extensions import db
from vulniverse_api.models import VulnerabilityRecord


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


def create_published(client, cve_id: str, profile: str = "cve-5.2.0"):
    return client.post(
        "/api/v1/records",
        json={
            "record": minimal_cve_record(cve_id),
            "profile": profile,
            "isDraft": False,
        },
    )


def insert_record(
    app,
    cve_id: str,
    owner_id: int,
    is_draft: bool,
    profile: str = "cve-5.2.0",
) -> None:
    """Inserts a record directly via the ORM rather than through an
    authenticated HTTP request. Cross-user visibility tests need two
    distinct identities, but two different logged-in test_client()s
    each making a real request within one test share the app
    fixture's single ambient app context — Flask reuses it rather
    than pushing a fresh one per request, so flask_login's
    g-scoped current_user caching leaks the *first* request's
    identity into the second. Only ever making one live authenticated
    request per test (here, none — the "other" side's data is
    inserted directly) sidesteps that entirely.
    """
    with app.app_context():
        record = VulnerabilityRecord(
            identifier=cve_id,
            profile=profile,
            document=minimal_cve_record(cve_id),
            is_draft=is_draft,
            created_by_id=owner_id,
        )
        db.session.add(record)
        db.session.commit()


def test_list_records_is_empty_with_no_records(client) -> None:
    response = client.get("/api/v1/records")

    assert response.status_code == 200
    assert response.get_json() == {"records": []}


def test_list_records_returns_created_records(client, test_user) -> None:
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
    assert by_identifier["CVE-2026-00001"]["createdBy"] == test_user.email

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


def test_draft_is_hidden_from_list_for_non_owner(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00010", test_user.id, is_draft=True)

    response = other_client.get("/api/v1/records")

    assert response.get_json()["records"] == []


def test_draft_is_visible_in_list_for_its_owner(app, test_user, client) -> None:
    insert_record(app, "CVE-2026-00011", test_user.id, is_draft=True)

    response = client.get("/api/v1/records")
    identifiers = {record["identifier"] for record in response.get_json()["records"]}

    assert "CVE-2026-00011" in identifiers


def test_published_record_is_visible_to_everyone(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00012", test_user.id, is_draft=False)

    response = other_client.get("/api/v1/records")
    identifiers = {record["identifier"] for record in response.get_json()["records"]}

    assert "CVE-2026-00012" in identifiers


def test_admin_sees_others_drafts_in_list(app, test_user, admin_client) -> None:
    insert_record(app, "CVE-2026-00013", test_user.id, is_draft=True)

    response = admin_client.get("/api/v1/records")
    identifiers = {record["identifier"] for record in response.get_json()["records"]}

    assert "CVE-2026-00013" in identifiers


def test_get_others_draft_is_404_for_non_owner(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00014", test_user.id, is_draft=True)

    response = other_client.get("/api/v1/records/CVE-2026-00014")

    assert response.status_code == 404


def test_get_others_draft_succeeds_for_admin(app, test_user, admin_client) -> None:
    insert_record(app, "CVE-2026-00015", test_user.id, is_draft=True)

    response = admin_client.get("/api/v1/records/CVE-2026-00015")

    assert response.status_code == 200


def test_get_published_record_succeeds_for_non_owner(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00016", test_user.id, is_draft=False)

    response = other_client.get("/api/v1/records/CVE-2026-00016")

    assert response.status_code == 200


def test_update_others_draft_is_404_for_non_owner(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00017", test_user.id, is_draft=True)

    response = other_client.put(
        "/api/v1/records/CVE-2026-00017",
        json={
            "record": minimal_cve_record("CVE-2026-00017"),
            "profile": "cve-5.2.0",
            "isDraft": True,
        },
    )

    assert response.status_code == 404


def test_delete_others_draft_is_404_for_non_owner(app, test_user, other_client) -> None:
    insert_record(app, "CVE-2026-00018", test_user.id, is_draft=True)

    response = other_client.delete("/api/v1/records/CVE-2026-00018")

    assert response.status_code == 404
