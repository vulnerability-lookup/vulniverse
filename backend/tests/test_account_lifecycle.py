"""Account lifecycle edge cases: sessions after deactivation and
deletion, the first admin, organisations keeping an active admin, and
invitations used at the same moment. Several clients per test, so
switching() between them (see test_two_factor.py)."""

from __future__ import annotations

from conftest import logged_in_client, make_user
from flask import g
from test_invitations_api import invite

from vulniverse_api.api import auth as auth_api
from vulniverse_api.extensions import db
from vulniverse_api.models import Invitation, Membership, User
from vulniverse_api.services.invitations import accept_invitation, find_invitation


def switching() -> None:
    g.pop("_login_user", None)


def set_active(admin_client, user_id: int, active: bool):
    switching()
    return admin_client.put(f"/api/v1/admin/users/{user_id}", json={"isActive": active})


# --- Sessions ----------------------------------------------------------------


def test_reactivating_does_not_revive_old_sessions(
    app, admin_client, test_user
) -> None:
    old = logged_in_client(app, test_user)

    assert set_active(admin_client, test_user.id, False).status_code == 200
    assert set_active(admin_client, test_user.id, True).status_code == 200

    switching()
    assert old.get("/api/v1/auth/me").status_code == 401


def test_a_deleted_accounts_session_does_not_open_the_next_account_with_its_id(
    app, admin_client
) -> None:
    gone = make_user(app, "gone@example.com", None)  # the newest id
    old = logged_in_client(app, gone)
    switching()
    admin_client.delete(f"/api/v1/admin/users/{gone.id}")
    successor = make_user(app, "next@example.com", None)
    assert successor.id == gone.id  # SQLite reuses the highest id

    switching()
    assert old.get("/api/v1/auth/me").status_code == 401


# --- The first admin -----------------------------------------------------------


def test_create_admin_creates_the_account(app) -> None:
    result = app.test_cli_runner().invoke(
        args=["create-admin", "Boss@Example.com"],
        input="long-password\nlong-password\n",
    )

    assert result.exit_code == 0, result.output
    user = User.query.filter_by(email="boss@example.com").one()
    assert user.is_admin


def test_create_admin_asks_before_promoting_a_registered_account(
    app, test_user
) -> None:
    result = app.test_cli_runner().invoke(
        args=["create-admin", "test@example.com"], input="n\n"
    )

    assert "addresses aren't verified" in result.output
    assert result.exit_code == 1
    assert not db.session.get(User, test_user.id).is_admin  # type: ignore[union-attr]


# --- An active admin per organisation -------------------------------------------


def test_the_last_active_admin_cannot_be_deactivated(
    app, admin_client, other_organisation, other_user
) -> None:
    lead = make_user(app, "lead@example.com", other_organisation, role="admin")
    # A deactivated admin doesn't count.
    retired = make_user(app, "retired@example.com", other_organisation, role="admin")
    db.session.get(User, retired.id).is_active = False  # type: ignore[union-attr]
    db.session.commit()

    response = set_active(admin_client, lead.id, False)

    assert response.status_code == 409
    assert "last admin of Other" in response.get_json()["message"]


def test_the_last_active_admin_cannot_step_down(
    app, organisation, colleague_user
) -> None:
    lead = make_user(app, "lead@example.com", organisation, role="admin")
    retired = make_user(app, "retired@example.com", organisation, role="admin")
    db.session.get(User, retired.id).is_active = False  # type: ignore[union-attr]
    db.session.commit()
    client = logged_in_client(app, lead)

    demote = client.put(
        f"/api/v1/organisations/{organisation.id}/members/{lead.id}",
        json={"role": "editor"},
    )
    assert demote.status_code == 409

    # The deactivated admin can go: it changes nothing.
    switching()
    remove = client.delete(
        f"/api/v1/organisations/{organisation.id}/members/{retired.id}"
    )
    assert remove.status_code == 200


# --- Invitations at the same moment --------------------------------------------


def test_an_invitation_checked_valid_but_used_meanwhile_is_refused(
    app, organisation
) -> None:
    token = invite(app, organisation)
    first = make_user(app, "first@example.com", None)
    second = make_user(app, "second@example.com", None)
    # Both requests found it valid before either used it.
    stale = find_invitation(token)
    assert stale is not None
    db.session.expunge(stale)

    assert accept_invitation(find_invitation(token), first) is not None  # type: ignore[arg-type]
    assert accept_invitation(stale, second) is None

    members = Membership.query.filter_by(organisation_id=organisation.id)
    assert {m.user.email for m in members} == {"first@example.com"}


def test_registering_with_a_link_used_meanwhile_leaves_no_account(
    app, anon_client, organisation, monkeypatch
) -> None:
    token = invite(app, organisation)
    accept_invitation(find_invitation(token), make_user(app, "first@example.com", None))  # type: ignore[arg-type]
    # As if the check had run just before the other registration used it.
    monkeypatch.setattr(auth_api, "invitation_error", lambda invitation: None)

    response = anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "late@example.com",
            "password": "password123",
            "invitation": token,
        },
    )

    assert response.status_code == 410
    assert User.query.filter_by(email="late@example.com").count() == 0
    assert Invitation.query.one().accepted_by.email == "first@example.com"  # type: ignore[union-attr]
