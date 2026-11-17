"""Organisation admins managing their organisation, invitation links, and
registration modes. One client per test (see insert_record in
test_records_api.py for why); invitations are made directly where a
second person would otherwise be needed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from conftest import logged_in_client, make_user
from flask import Flask
from test_records_api import insert_record

from vulniverse_api.extensions import db
from vulniverse_api.models import Invitation, Membership, Organisation, User
from vulniverse_api.services.invitations import (
    accept_invitation,
    create_invitation,
    find_invitation,
    hash_token,
)


@pytest.fixture
def org_admin_client(app: Flask, organisation):
    """An admin of Acme who isn't an instance admin."""
    return logged_in_client(
        app, make_user(app, "orgadmin@example.com", organisation, role="admin")
    )


def invite(app: Flask, organisation, role: str = "editor") -> str:
    with app.app_context():
        creator = make_user(app, f"inviter-{role}@example.com", None)
        target = db.session.get(Organisation, organisation.id)
        assert target is not None
        _, token = create_invitation(target, role, creator)
        return token


def roles(app: Flask, organisation) -> dict[str, str]:
    with app.app_context():
        memberships = Membership.query.filter_by(organisation_id=organisation.id).all()
        return {m.user.email: m.role for m in memberships}


# --- Organisation admins ---------------------------------------------------


def test_organisation_admins_manage_their_own_organisation(
    org_admin_client, organisation
) -> None:
    members = org_admin_client.get(f"/api/v1/organisations/{organisation.id}/members")
    renamed = org_admin_client.patch(
        f"/api/v1/organisations/{organisation.id}", json={"name": "Acme CNA"}
    )

    assert members.status_code == 200
    assert renamed.status_code == 200


def test_organisation_admins_see_their_organisation(
    org_admin_client, organisation
) -> None:
    body = org_admin_client.get(f"/api/v1/organisations/{organisation.id}").get_json()

    assert (body["name"], body["memberCount"]) == ("Acme", 1)


def test_organisation_admins_cannot_manage_other_organisations(
    org_admin_client, other_organisation
) -> None:
    assert (
        org_admin_client.get(
            f"/api/v1/organisations/{other_organisation.id}/members"
        ).status_code
        == 403
    )


def test_editors_cannot_manage_their_organisation(client, organisation) -> None:
    assert (
        client.get(f"/api/v1/organisations/{organisation.id}/members").status_code
        == 403
    )
    assert (
        client.post(
            f"/api/v1/organisations/{organisation.id}/invitations",
            json={"role": "editor"},
        ).status_code
        == 403
    )


def test_organisation_admins_change_roles_but_add_only_by_invitation(
    app,
    org_admin_client,
    organisation,
    test_user,
    other_user,
) -> None:
    base = f"/api/v1/organisations/{organisation.id}/members"

    assert (
        org_admin_client.put(
            f"{base}/{test_user.id}", json={"role": "admin"}
        ).status_code
        == 200
    )
    added = org_admin_client.put(f"{base}/{other_user.id}", json={"role": "editor"})

    assert added.status_code == 403
    assert "invitation link" in added.get_json()["message"]
    assert roles(app, organisation)["test@example.com"] == "admin"


def test_the_last_admin_can_be_neither_demoted_nor_removed(
    app, admin_client, admin_user, organisation
) -> None:
    url = f"/api/v1/organisations/{organisation.id}/members/{admin_user.id}"

    demoted = admin_client.put(url, json={"role": "editor"})
    removed = admin_client.delete(url)

    assert (demoted.status_code, removed.status_code) == (409, 409)
    assert "at least one admin" in demoted.get_json()["message"]
    assert roles(app, organisation)["admin@example.com"] == "admin"


def test_with_a_second_admin_the_first_may_step_down(
    app, admin_client, admin_user, test_user, organisation
) -> None:
    base = f"/api/v1/organisations/{organisation.id}/members"

    admin_client.put(f"{base}/{test_user.id}", json={"role": "admin"})

    assert (
        admin_client.put(f"{base}/{admin_user.id}", json={"role": "editor"}).status_code
        == 200
    )


# --- Invitations: creating, listing, revoking --------------------------------


def test_an_invitation_link_is_shown_once_and_stored_only_hashed(
    app, org_admin_client, organisation
) -> None:
    created = org_admin_client.post(
        f"/api/v1/organisations/{organisation.id}/invitations", json={"role": "editor"}
    )
    listed = org_admin_client.get(
        f"/api/v1/organisations/{organisation.id}/invitations"
    )

    token = created.get_json()["token"]
    assert created.status_code == 201
    assert created.get_json()["state"] == "valid"
    assert "token" not in listed.get_json()["invitations"][0]
    with app.app_context():
        stored = Invitation.query.one()
        assert stored.token_hash == hash_token(token)
        assert token not in stored.token_hash


def test_invitations_need_a_valid_role(org_admin_client, organisation) -> None:
    response = org_admin_client.post(
        f"/api/v1/organisations/{organisation.id}/invitations", json={"role": "owner"}
    )

    assert response.status_code == 400


def test_a_revoked_invitation_can_no_longer_be_used(
    app, org_admin_client, organisation
) -> None:
    created = org_admin_client.post(
        f"/api/v1/organisations/{organisation.id}/invitations", json={"role": "editor"}
    )
    body = created.get_json()

    revoked = org_admin_client.delete(
        f"/api/v1/organisations/{organisation.id}/invitations/{body['id']}"
    )

    assert revoked.get_json()["state"] == "revoked"
    assert (
        org_admin_client.get(f"/api/v1/invitations/{body['token']}").get_json()["state"]
        == "revoked"
    )


def test_invitations_of_another_organisation_cannot_be_revoked(
    app, org_admin_client, other_organisation
) -> None:
    invite(app, other_organisation)
    with app.app_context():
        invitation_id = Invitation.query.one().id

    response = org_admin_client.delete(
        f"/api/v1/organisations/{other_organisation.id}/invitations/{invitation_id}"
    )

    assert response.status_code == 403


# --- Invitations: the link ---------------------------------------------------


def test_the_landing_page_info_needs_no_login(app, anon_client, organisation) -> None:
    token = invite(app, organisation, role="admin")

    body = anon_client.get(f"/api/v1/invitations/{token}").get_json()

    assert body == {"organisation": "Acme", "role": "admin", "state": "valid"}


def test_an_unknown_link_is_404(anon_client) -> None:
    assert anon_client.get("/api/v1/invitations/not-a-token").status_code == 404


def test_accepting_joins_with_the_role_and_switches_to_the_organisation(
    app,
    other_client,
    other_user,
    organisation,
) -> None:
    token = invite(app, organisation, role="admin")

    response = other_client.post(f"/api/v1/invitations/{token}/accept")
    me = other_client.get("/api/v1/auth/me").get_json()

    assert response.status_code == 200
    assert roles(app, organisation)["other@example.com"] == "admin"
    assert me["currentOrganisationId"] == organisation.id


def test_an_invitation_works_once(app, organisation) -> None:
    token = invite(app, organisation)
    with app.app_context():
        user = User.query.filter_by(email="inviter-editor@example.com").one()
        invitation = find_invitation(token)
        assert invitation is not None
        accept_invitation(invitation, user)

    second = logged_in_client(app, make_user(app, "late@example.com", None))
    response = second.post(f"/api/v1/invitations/{token}/accept")

    assert response.status_code == 410
    assert "accepted" in response.get_json()["message"]


def test_members_cannot_use_up_an_invitation(app, client, organisation) -> None:
    token = invite(app, organisation)

    response = client.post(f"/api/v1/invitations/{token}/accept")

    assert response.status_code == 409
    assert client.get(f"/api/v1/invitations/{token}").get_json()["state"] == "valid"


def test_an_expired_invitation_can_no_longer_be_used(
    app, other_client, organisation
) -> None:
    token = invite(app, organisation)
    with app.app_context():
        Invitation.query.one().expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.session.commit()

    assert other_client.post(f"/api/v1/invitations/{token}/accept").status_code == 410


# --- Registration modes ------------------------------------------------------


def register(client, email: str, **extra):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", **extra},
    )


def test_the_registration_mode_needs_no_login(app, anon_client) -> None:
    app.config["VULNIVERSE_REGISTRATION"] = "invite"

    assert anon_client.get("/api/v1/auth/registration").get_json() == {"mode": "invite"}


def test_open_registration_needs_no_invitation(anon_client) -> None:
    response = register(anon_client, "new@example.com")

    assert response.status_code == 201
    assert response.get_json()["organisations"] == []


def test_registering_with_an_invitation_joins_its_organisation(
    app, anon_client, organisation
) -> None:
    app.config["VULNIVERSE_REGISTRATION"] = "invite"
    token = invite(app, organisation)

    body = register(anon_client, "new@example.com", invitation=token).get_json()

    assert body["organisations"] == [
        {"id": organisation.id, "name": "Acme", "role": "editor"}
    ]
    assert body["currentOrganisationId"] == organisation.id


def test_invite_only_registration_refuses_without_an_invitation(
    app, anon_client
) -> None:
    app.config["VULNIVERSE_REGISTRATION"] = "invite"

    response = register(anon_client, "new@example.com")

    assert response.status_code == 403
    assert "invitation link" in response.get_json()["message"]


def test_closed_registration_refuses_even_with_an_invitation(
    app, anon_client, organisation
) -> None:
    app.config["VULNIVERSE_REGISTRATION"] = "closed"
    token = invite(app, organisation)

    assert register(anon_client, "new@example.com", invitation=token).status_code == 403


def test_a_bad_invitation_creates_no_account(app, anon_client) -> None:
    response = register(anon_client, "new@example.com", invitation="not-a-token")

    assert response.status_code == 404
    with app.app_context():
        assert User.query.filter_by(email="new@example.com").first() is None


# --- Deleting organisations ---------------------------------------------------


def test_an_empty_organisation_is_deleted_with_its_memberships_and_invitations(
    app,
    admin_client,
    other_organisation,
    other_user,
) -> None:
    invite(app, other_organisation)

    response = admin_client.delete(
        f"/api/v1/admin/organisations/{other_organisation.id}"
    )

    assert response.status_code == 200
    with app.app_context():
        assert db.session.get(Organisation, other_organisation.id) is None
        assert (
            Membership.query.filter_by(organisation_id=other_organisation.id).count()
            == 0
        )
        assert (
            Invitation.query.filter_by(organisation_id=other_organisation.id).count()
            == 0
        )
        # The account stays.
        assert db.session.get(User, other_user.id) is not None


def test_an_organisation_with_records_is_not_deleted(
    app, admin_client, test_user, organisation
) -> None:
    insert_record(app, "CVE-2026-04001", test_user.id, is_draft=True)

    response = admin_client.delete(f"/api/v1/admin/organisations/{organisation.id}")

    assert response.status_code == 409
    assert "1 record(s)" in response.get_json()["message"]
    with app.app_context():
        assert db.session.get(Organisation, organisation.id) is not None


def test_only_instance_admins_delete_organisations(
    org_admin_client, organisation
) -> None:
    assert (
        org_admin_client.delete(
            f"/api/v1/admin/organisations/{organisation.id}"
        ).status_code
        == 403
    )


def test_a_deleted_organisation_no_longer_is_anyones_current_one(
    app,
    other_client,
    other_organisation,
    organisation,
) -> None:
    with app.app_context():
        user = User.query.filter_by(email="other@example.com").one()
        db.session.add(
            Membership(user_id=user.id, organisation_id=organisation.id, role="editor")
        )
        Membership.query.filter_by(
            user_id=user.id, organisation_id=other_organisation.id
        ).delete()
        db.session.delete(db.session.get(Organisation, other_organisation.id))
        db.session.commit()

    me = other_client.get("/api/v1/auth/me").get_json()

    assert me["currentOrganisationId"] == organisation.id
