from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.exc import IntegrityError

from vulniverse_api.extensions import db
from vulniverse_api.models import CnaPublication, VulnerabilityRecord


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


def minimal_gcve_record(vuln_id: str) -> dict[str, Any]:
    """The GCVE identifier lives in the advisory x_gcve entry
    (see services/identifiers.py), not in cveMetadata."""
    return {
        "cveMetadata": {},
        "containers": {
            "cna": {"x_gcve": [{"vulnId": vuln_id, "recordType": "advisory"}]},
        },
    }


def record_id(response) -> int:
    return response.get_json()["id"]


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
) -> int:
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
        return record.id


def test_list_records_is_empty_with_no_records(client) -> None:
    response = client.get("/api/v1/records")

    assert response.status_code == 200
    assert response.get_json() == {"records": []}


def test_list_records_returns_created_records(client, test_user) -> None:
    cve_id = record_id(create_draft(client, "CVE-2026-00001"))
    gcve_id = record_id(client.post(
        "/api/v1/records",
        json={
            "record": minimal_gcve_record("GCVE-0-2026-00002"),
            "profile": "gcve-bcp-05-1.7",
            "isDraft": True,
        },
    ))

    response = client.get("/api/v1/records")

    assert response.status_code == 200

    by_id = {record["id"]: record for record in response.get_json()["records"]}

    assert set(by_id) == {cve_id, gcve_id}
    assert by_id[cve_id]["identifier"] == "CVE-2026-00001"
    assert by_id[gcve_id]["identifier"] == "GCVE-0-2026-00002"
    assert by_id[gcve_id]["profile"] == "gcve-bcp-05-1.7"
    assert by_id[cve_id]["isDraft"] is True
    assert "updatedAt" in by_id[cve_id]
    assert by_id[cve_id]["createdBy"] == test_user.email

    # The list is summary data only — it must not embed the full
    # record document (fetched separately via GET /records/<id>).
    assert "record" not in by_id[cve_id]


def test_list_records_orders_most_recently_updated_first(client) -> None:
    create_draft(client, "CVE-2026-00001")
    create_draft(client, "CVE-2026-00002")

    response = client.get("/api/v1/records")
    identifiers = [
        record["identifier"] for record in response.get_json()["records"]
    ]

    assert identifiers == ["CVE-2026-00002", "CVE-2026-00001"]


def test_get_record_by_id(client) -> None:
    created = create_draft(client, "CVE-2026-00001")

    response = client.get(f"/api/v1/records/{record_id(created)}")

    assert response.status_code == 200
    assert response.get_json()["id"] == record_id(created)
    assert response.get_json()["identifier"] == "CVE-2026-00001"


def test_delete_record_removes_it(client) -> None:
    created = create_draft(client, "CVE-2026-00001")

    response = client.delete(f"/api/v1/records/{record_id(created)}")

    assert response.status_code == 200

    remaining = client.get("/api/v1/records").get_json()["records"]

    assert remaining == []


def test_delete_unknown_record_returns_404(client) -> None:
    response = client.delete("/api/v1/records/999")

    assert response.status_code == 404


def test_delete_record_cleans_up_its_cna_publication_rows(app, client) -> None:
    rid = record_id(create_draft(client, "CVE-2026-00001"))

    with app.app_context():
        db.session.add_all([
            CnaPublication(
                record_id=rid,
                target="vl",
                status="RESERVED",
                cve_id="GCVE-0-2026-00001",
            ),
            CnaPublication(
                record_id=rid,
                target="cve-program",
                status="LOCAL_ONLY",
            ),
        ])
        db.session.commit()

    response = client.delete(f"/api/v1/records/{rid}")

    assert response.status_code == 200

    with app.app_context():
        assert CnaPublication.query.filter_by(record_id=rid).all() == []


def test_delete_record_only_removes_its_own_publication_rows(app, client) -> None:
    first = record_id(create_draft(client, "CVE-2026-00001"))
    second = record_id(create_draft(client, "CVE-2026-00002"))

    with app.app_context():
        db.session.add(
            CnaPublication(
                record_id=second,
                target="vl",
                status="RESERVED",
                cve_id="GCVE-0-2026-00002",
            ),
        )
        db.session.commit()

    response = client.delete(f"/api/v1/records/{first}")

    assert response.status_code == 200

    with app.app_context():
        assert len(CnaPublication.query.filter_by(record_id=second).all()) == 1


def test_update_record_allows_adding_vulnid_alongside_existing_cveid(client) -> None:
    rid = record_id(create_draft(client, "CVE-2026-00001"))

    document = minimal_cve_record("CVE-2026-00001")
    document["cveMetadata"]["vulnId"] = "GCVE-0-2026-00001"

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 200
    assert response.get_json()["record"]["cveMetadata"]["vulnId"] == "GCVE-0-2026-00001"


def test_update_record_allows_removing_vulnid_when_cveid_still_matches(client) -> None:
    # Record is created (and thus identified) via cveId alone — adding a
    # vulnId later, then removing it again, must not disturb that.
    rid = record_id(create_draft(client, "CVE-2026-00002"))

    document = minimal_cve_record("CVE-2026-00002")
    document["cveMetadata"]["vulnId"] = "GCVE-0-2026-00002"

    client.put(
        f"/api/v1/records/{rid}",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    del document["cveMetadata"]["vulnId"]

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": document, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 200
    assert "vulnId" not in response.get_json()["record"]["cveMetadata"]


def test_typed_lowercase_gcve_id_is_saved_with_uppercase_prefix(client) -> None:
    rid = create_identifierless_draft(client, profile="gcve-bcp-05-1.7")

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_gcve_record("gcve-65535-2026-20128"), "profile": "gcve-bcp-05-1.7", "isDraft": True},
    )

    body = response.get_json()
    assert response.status_code == 200
    assert body["identifier"] == "GCVE-65535-2026-20128"
    assert body["record"]["containers"]["cna"]["x_gcve"][0]["vulnId"] == "GCVE-65535-2026-20128"


def test_typed_lowercase_cve_id_is_saved_with_uppercase_prefix(client) -> None:
    response = create_draft(client, "cve-2026-0042")

    body = response.get_json()
    assert body["identifier"] == "CVE-2026-0042"
    assert body["record"]["cveMetadata"]["cveId"] == "CVE-2026-0042"


def test_osv_ids_keep_their_case(client) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": minimal_osv_record("GHSA-q7jr-4jmj-7c77"), "profile": "osv-1.9.2", "isDraft": True},
    )

    assert response.get_json()["identifier"] == "GHSA-q7jr-4jmj-7c77"


def test_database_rejects_an_identifier_differing_only_in_case(app, test_user) -> None:
    """The app checks first; this is the backstop for two saves racing."""
    insert_record(app, "GCVE-1-2026-0001", test_user.id, is_draft=True, profile="gcve-bcp-05-1.7")

    with pytest.raises(IntegrityError):
        insert_record(app, "gcve-1-2026-0001", test_user.id, is_draft=True, profile="gcve-bcp-05-1.7")


def test_several_identifierless_drafts_pass_the_case_insensitive_index(client) -> None:
    assert create_identifierless_draft(client) != create_identifierless_draft(client)


def test_update_record_rejects_real_identifier_change(client) -> None:
    rid = record_id(create_draft(client, "CVE-2026-00003"))

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_cve_record("CVE-2026-99999"), "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 400
    assert "cannot be changed" in response.get_json()["message"]


def test_update_record_rejects_when_all_identifying_fields_removed(client) -> None:
    rid = record_id(create_draft(client, "CVE-2026-00004"))

    document = minimal_cve_record("CVE-2026-00004")
    del document["cveMetadata"]["cveId"]

    response = client.put(
        f"/api/v1/records/{rid}",
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
    rid = insert_record(app, "CVE-2026-00014", test_user.id, is_draft=True)

    response = other_client.get(f"/api/v1/records/{rid}")

    assert response.status_code == 404


def test_get_others_draft_succeeds_for_admin(app, test_user, admin_client) -> None:
    rid = insert_record(app, "CVE-2026-00015", test_user.id, is_draft=True)

    response = admin_client.get(f"/api/v1/records/{rid}")

    assert response.status_code == 200


def test_get_published_record_succeeds_for_non_owner(app, test_user, other_client) -> None:
    rid = insert_record(app, "CVE-2026-00016", test_user.id, is_draft=False)

    response = other_client.get(f"/api/v1/records/{rid}")

    assert response.status_code == 200


def test_update_others_draft_is_404_for_non_owner(app, test_user, other_client) -> None:
    rid = insert_record(app, "CVE-2026-00017", test_user.id, is_draft=True)

    response = other_client.put(
        f"/api/v1/records/{rid}",
        json={
            "record": minimal_cve_record("CVE-2026-00017"),
            "profile": "cve-5.2.0",
            "isDraft": True,
        },
    )

    assert response.status_code == 404


def test_delete_others_draft_is_404_for_non_owner(app, test_user, other_client) -> None:
    rid = insert_record(app, "CVE-2026-00018", test_user.id, is_draft=True)

    response = other_client.delete(f"/api/v1/records/{rid}")

    assert response.status_code == 404


def create_identifierless_draft(client, profile: str = "cve-5.2.0") -> int:
    response = client.post(
        "/api/v1/records",
        json={"record": {}, "profile": profile, "isDraft": True},
    )
    assert response.status_code == 201
    return record_id(response)


def test_create_record_without_identifier_stores_null(client) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": {}, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 201
    assert response.get_json()["identifier"] is None
    assert isinstance(response.get_json()["id"], int)


def test_create_record_without_identifier_rejects_publish(client) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": {}, "profile": "cve-5.2.0", "isDraft": False},
    )

    assert response.status_code == 400


def test_several_drafts_without_identifier_can_coexist(client) -> None:
    first = create_identifierless_draft(client)
    second = create_identifierless_draft(client)

    assert first != second


def test_identifierless_draft_is_listed_and_fetchable(client) -> None:
    rid = create_identifierless_draft(client)

    listed = {r["id"]: r for r in client.get("/api/v1/records").get_json()["records"]}
    assert listed[rid]["identifier"] is None

    get_response = client.get(f"/api/v1/records/{rid}")
    assert get_response.status_code == 200
    assert get_response.get_json()["identifier"] is None


def test_updating_identifierless_draft_without_an_identifier_keeps_it_null(client) -> None:
    rid = create_identifierless_draft(client)

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": {"dataType": "CVE_RECORD"}, "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 200
    assert response.get_json()["identifier"] is None


def test_first_real_identifier_is_assigned_without_changing_the_id(client) -> None:
    rid = create_identifierless_draft(client, profile="gcve-bcp-05-1.7")

    response = client.put(
        f"/api/v1/records/{rid}",
        json={
            "record": minimal_gcve_record("GCVE-0-2026-00042"),
            "profile": "gcve-bcp-05-1.7",
            "isDraft": True,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == rid
    assert response.get_json()["identifier"] == "GCVE-0-2026-00042"
    assert client.get(f"/api/v1/records/{rid}").get_json()["identifier"] == "GCVE-0-2026-00042"


def test_updating_identifierless_draft_rejects_publish_without_identifier(client) -> None:
    rid = create_identifierless_draft(client)

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": {}, "profile": "cve-5.2.0", "isDraft": False},
    )

    assert response.status_code == 400


def test_identifierless_draft_publishes_with_a_real_identifier_in_one_save(client) -> None:
    rid = create_identifierless_draft(client)

    response = client.put(
        f"/api/v1/records/{rid}",
        json={
            "record": minimal_cve_record("CVE-2026-00043"),
            "profile": "cve-5.2.0",
            "isDraft": False,
        },
    )

    assert response.status_code == 200
    assert response.get_json()["identifier"] == "CVE-2026-00043"
    assert response.get_json()["isDraft"] is False


def test_assigning_an_identifier_conflicts_when_already_taken(client) -> None:
    create_draft(client, "CVE-2026-00020")
    rid = create_identifierless_draft(client)

    response = client.put(
        f"/api/v1/records/{rid}",
        json={"record": minimal_cve_record("CVE-2026-00020"), "profile": "cve-5.2.0", "isDraft": True},
    )

    assert response.status_code == 409


def test_publication_rows_stay_attached_when_an_identifier_is_assigned(app, client) -> None:
    rid = create_identifierless_draft(client, profile="gcve-bcp-05-1.7")

    with app.app_context():
        db.session.add(
            CnaPublication(
                record_id=rid,
                target="vl",
                status="RESERVED",
                cve_id="GCVE-0-2026-00099",
            ),
        )
        db.session.commit()

    response = client.put(
        f"/api/v1/records/{rid}",
        json={
            "record": minimal_gcve_record("GCVE-0-2026-00099"),
            "profile": "gcve-bcp-05-1.7",
            "isDraft": True,
        },
    )
    assert response.status_code == 200

    with app.app_context():
        publication = CnaPublication.query.filter_by(record_id=rid).one()
        assert publication.status == "RESERVED"


def minimal_osv_record(osv_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.9.2",
        "id": osv_id,
        "modified": "2026-11-09T10:00:00Z",
        "affected": [
            {"package": {"ecosystem": "PyPI", "name": "widget"}, "versions": ["1.0.0"]},
        ],
    }


def test_osv_record_is_published_with_its_id_as_identifier(client) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": minimal_osv_record("PYSEC-2026-1"), "profile": "osv-1.9.2", "isDraft": False},
    )

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["identifier"] == "PYSEC-2026-1"


def test_osv_record_that_breaks_the_schema_is_not_published(client) -> None:
    document = minimal_osv_record("PYSEC-2026-2")
    del document["modified"]

    response = client.post(
        "/api/v1/records",
        json={"record": document, "profile": "osv-1.9.2", "isDraft": False},
    )

    assert response.status_code == 422
