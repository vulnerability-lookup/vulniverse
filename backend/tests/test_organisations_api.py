"""/auth/me's organisations, switching the current one, and the instance
admins' organisation API. One client per test (see insert_record in
test_records_api.py for why)."""

from __future__ import annotations

from conftest import logged_in_client, make_user
from test_records_api import create_draft, insert_record

from vulniverse_api.extensions import db
from vulniverse_api.models import Membership, VulnerabilityRecord

# --- /auth/me and switching ---------------------------------------------


def test_me_lists_the_organisations_and_the_current_one(client, organisation) -> None:
    body = client.get("/api/v1/auth/me").get_json()

    assert body["organisations"] == [
        {"id": organisation.id, "name": "Acme", "role": "editor"}
    ]
    assert body["currentOrganisationId"] == organisation.id


def test_me_without_an_organisation(app) -> None:
    lonely_client = logged_in_client(app, make_user(app, "lonely@example.com", None))

    body = lonely_client.get("/api/v1/auth/me").get_json()

    assert body["organisations"] == []
    assert body["currentOrganisationId"] is None


def test_switching_changes_where_new_records_go(
    app, organisation, other_organisation
) -> None:
    user = make_user(app, "both@example.com", organisation)
    with app.app_context():
        db.session.add(
            Membership(
                user_id=user.id, organisation_id=other_organisation.id, role="editor"
            )
        )
        db.session.commit()
    both_client = logged_in_client(app, user)

    response = both_client.post(
        "/api/v1/auth/organisation", json={"id": other_organisation.id}
    )

    assert response.status_code == 200
    assert response.get_json()["currentOrganisationId"] == other_organisation.id
    assert (
        create_draft(both_client, "CVE-2026-02001").get_json()["organisation"]["name"]
        == "Other"
    )


def test_switching_to_an_organisation_one_isnt_in_is_refused(
    client, other_organisation
) -> None:
    response = client.post(
        "/api/v1/auth/organisation", json={"id": other_organisation.id}
    )

    assert response.status_code == 403


def test_switching_needs_an_integer_id(client) -> None:
    assert client.post("/api/v1/auth/organisation", json={"id": "1"}).status_code == 400
    assert (
        client.post("/api/v1/auth/organisation", json={"id": True}).status_code == 400
    )


# --- Instance admins: organisations ---------------------------------------


def test_organisation_admin_api_needs_a_login(anon_client) -> None:
    assert anon_client.get("/api/v1/admin/organisations").status_code == 401


def test_organisation_admin_api_needs_an_instance_admin(client) -> None:
    assert client.get("/api/v1/admin/organisations").status_code == 403
    assert (
        client.post("/api/v1/admin/organisations", json={"name": "Mine"}).status_code
        == 403
    )


def test_admin_creates_an_organisation_with_a_derived_slug(admin_client) -> None:
    response = admin_client.post(
        "/api/v1/admin/organisations", json={"name": " Acme Security, Inc. "}
    )

    assert response.status_code == 201
    assert response.get_json() | {"id": 0, "createdAt": ""} == {
        "id": 0,
        "name": "Acme Security, Inc.",
        "slug": "acme-security-inc",
        "createdAt": "",
        "memberCount": 0,
    }


def test_admin_lists_organisations_with_member_counts(
    admin_client, test_user, other_user
) -> None:
    body = admin_client.get("/api/v1/admin/organisations").get_json()

    # Acme: test_user and admin_user; Other: other_user.
    assert [(o["name"], o["memberCount"]) for o in body["organisations"]] == [
        ("Acme", 2),
        ("Other", 1),
    ]


def test_slugs_are_unique_and_well_formed(admin_client, organisation) -> None:
    assert (
        admin_client.post(
            "/api/v1/admin/organisations", json={"name": "Acme 2", "slug": "acme"}
        ).status_code
        == 409
    )
    assert (
        admin_client.post(
            "/api/v1/admin/organisations", json={"name": "X", "slug": "Not OK"}
        ).status_code
        == 400
    )
    assert (
        admin_client.post(
            "/api/v1/admin/organisations", json={"name": "  "}
        ).status_code
        == 400
    )
    assert (
        admin_client.post(
            "/api/v1/admin/organisations", json={"name": "!!!"}
        ).status_code
        == 400
    )


def test_names_are_unique_ignoring_case(
    admin_client, organisation, other_organisation
) -> None:
    create = admin_client.post("/api/v1/admin/organisations", json={"name": "ACME"})
    rename = admin_client.patch(
        f"/api/v1/admin/organisations/{other_organisation.id}", json={"name": "acme"}
    )
    keep = admin_client.patch(
        f"/api/v1/admin/organisations/{organisation.id}", json={"name": "ACME"}
    )

    assert (create.status_code, rename.status_code) == (409, 409)
    assert "name already exists" in create.get_json()["message"]
    # Its own name, in another case, is fine.
    assert keep.status_code == 200


def test_admin_renames_an_organisation(admin_client, organisation) -> None:
    response = admin_client.patch(
        f"/api/v1/admin/organisations/{organisation.id}", json={"name": "Acme CNA"}
    )

    assert response.status_code == 200
    assert (response.get_json()["name"], response.get_json()["slug"]) == (
        "Acme CNA",
        "acme",
    )


def test_renaming_an_unknown_organisation_is_404(admin_client) -> None:
    assert (
        admin_client.patch(
            "/api/v1/admin/organisations/999", json={"name": "X"}
        ).status_code
        == 404
    )


# --- Instance admins: members ---------------------------------------------


def test_admin_adds_a_member_and_changes_their_role(
    app, admin_client, other_user, organisation
) -> None:
    url = f"/api/v1/admin/organisations/{organisation.id}/members/{other_user.id}"

    added = admin_client.put(url, json={"role": "editor"})
    changed = admin_client.put(url, json={"role": "admin"})

    assert added.status_code == 201
    assert changed.status_code == 200
    assert changed.get_json() == {
        "userId": other_user.id,
        "email": "other@example.com",
        "isActive": True,
        "role": "admin",
    }


def test_admin_lists_members_by_email(admin_client, test_user, organisation) -> None:
    body = admin_client.get(
        f"/api/v1/admin/organisations/{organisation.id}/members"
    ).get_json()

    assert [(m["email"], m["role"]) for m in body["members"]] == [
        ("admin@example.com", "admin"),
        ("test@example.com", "editor"),
    ]


def test_member_changes_need_a_valid_role_and_existing_ids(
    admin_client, test_user, organisation
) -> None:
    base = f"/api/v1/admin/organisations/{organisation.id}/members"

    assert (
        admin_client.put(f"{base}/{test_user.id}", json={"role": "owner"}).status_code
        == 400
    )
    assert admin_client.put(f"{base}/999", json={"role": "editor"}).status_code == 404
    assert (
        admin_client.put(
            f"/api/v1/admin/organisations/999/members/{test_user.id}",
            json={"role": "editor"},
        ).status_code
        == 404
    )


def test_removing_a_member_ends_their_access_but_keeps_the_records(
    app, admin_client, test_user, organisation
) -> None:
    rid = insert_record(app, "CVE-2026-02002", test_user.id, is_draft=True)

    response = admin_client.delete(
        f"/api/v1/admin/organisations/{organisation.id}/members/{test_user.id}"
    )

    assert response.status_code == 200
    with app.app_context():
        assert Membership.query.filter_by(user_id=test_user.id).count() == 0
        record = db.session.get(VulnerabilityRecord, rid)
        assert record is not None
        assert record.organisation_id == organisation.id


def test_removing_a_non_member_is_404(admin_client, other_user, organisation) -> None:
    assert (
        admin_client.delete(
            f"/api/v1/admin/organisations/{organisation.id}/members/{other_user.id}"
        ).status_code
        == 404
    )
