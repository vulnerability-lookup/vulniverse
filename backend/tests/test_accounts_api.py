"""Account security: changing one's password, deleting one's account,
and admins resetting passwords and deleting accounts. One client per test (see insert_record in
test_records_api.py for why)."""

from __future__ import annotations

from conftest import logged_in_client, make_user
from test_records_api import insert_record
from werkzeug.security import check_password_hash

from vulniverse_api.extensions import db
from vulniverse_api.models import (
    Membership,
    Template,
    User,
    UserCnaCredential,
    VulnerabilityRecord,
)


def login(client, password: str, email: str = "test@example.com"):
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )


def stored(app, email: str = "test@example.com") -> User | None:
    with app.app_context():
        return User.query.filter_by(email=email).first()


# --- Logging in -------------------------------------------------------------


def test_an_unknown_address_is_just_invalid(anon_client) -> None:
    response = login(anon_client, "password123", email="nobody@example.com")

    assert response.status_code == 401
    assert response.get_json()["message"] == "Invalid email or password."


# --- Changing one's password -------------------------------------------------


def change(client, current: str, new: str):
    return client.post(
        "/api/v1/auth/password", json={"currentPassword": current, "newPassword": new}
    )


def test_changing_the_password(app, client) -> None:
    response = change(client, "password123", "new-password-456")

    assert response.status_code == 200
    assert check_password_hash(stored(app).password_hash, "new-password-456")  # type: ignore[union-attr]


def test_changing_needs_the_current_password(app, client) -> None:
    response = change(client, "not-it", "new-password-456")

    assert response.status_code == 403
    assert check_password_hash(stored(app).password_hash, "password123")  # type: ignore[union-attr]


def test_the_new_password_needs_eight_characters(client) -> None:
    assert change(client, "password123", "short").status_code == 400


# --- Deleting one's account --------------------------------------------------


def test_deleting_ones_account_keeps_records_but_not_what_is_only_ones_own(
    app,
    client,
    test_user,
    organisation,
) -> None:
    rid = insert_record(app, "CVE-2026-06001", test_user.id, is_draft=True)
    with app.app_context():
        db.session.add(
            Template(
                profile="cve-5.2.0", name="Mine", created_by_id=test_user.id, fields=[]
            )
        )
        db.session.add(
            UserCnaCredential(
                user_id=test_user.id,
                target="vl",
                cve_url="https://example.com",
                short_name="x",
                org_id="x",
                cve_api_org="x",
                cve_api_user="x",
                cve_api_key_encrypted="x",
            )
        )
        db.session.commit()

    response = client.delete("/api/v1/auth/account", json={"password": "password123"})

    assert response.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    with app.app_context():
        assert db.session.get(User, test_user.id) is None
        record = db.session.get(VulnerabilityRecord, rid)
        assert record is not None and record.created_by_id is None
        assert record.organisation_id == organisation.id
        assert Template.query.count() == 0
        assert UserCnaCredential.query.count() == 0
        assert Membership.query.filter_by(user_id=test_user.id).count() == 0


def test_deleting_ones_account_needs_the_password(app, client, test_user) -> None:
    response = client.delete("/api/v1/auth/account", json={"password": "not-it"})

    assert response.status_code == 403
    assert stored(app) is not None


def test_the_last_admin_of_an_organisation_with_members_cannot_leave(
    app, organisation, test_user
) -> None:
    lead = make_user(app, "lead@example.com", organisation, role="admin")

    response = logged_in_client(app, lead).delete(
        "/api/v1/auth/account", json={"password": "password123"}
    )

    assert response.status_code == 409
    assert "last admin of Acme" in response.get_json()["message"]


def test_the_last_instance_admin_cannot_leave(app, admin_client, admin_user) -> None:
    response = admin_client.delete(
        "/api/v1/auth/account", json={"password": "password123"}
    )

    assert response.status_code == 409
    assert "last instance admin" in response.get_json()["message"]


# --- Admins: resetting passwords, deleting accounts ---------------------------


def test_admins_reset_a_password(app, admin_client, test_user) -> None:
    response = admin_client.post(f"/api/v1/admin/users/{test_user.id}/reset-password")

    password = response.get_json()["password"]
    assert len(password) >= 12
    user = stored(app)
    assert user is not None
    assert check_password_hash(user.password_hash, password)


def test_only_admins_reset_passwords(client, test_user) -> None:
    assert (
        client.post(f"/api/v1/admin/users/{test_user.id}/reset-password").status_code
        == 403
    )


def test_admins_delete_accounts(app, admin_client, other_user) -> None:
    response = admin_client.delete(f"/api/v1/admin/users/{other_user.id}")

    assert response.status_code == 200
    assert stored(app, "other@example.com") is None


def test_admins_delete_their_own_account_elsewhere(admin_client, admin_user) -> None:
    assert (
        admin_client.delete(f"/api/v1/admin/users/{admin_user.id}").status_code == 400
    )


def test_admins_cannot_strand_an_organisation(
    app, admin_client, other_organisation, other_user
) -> None:
    lead = make_user(app, "lead@example.com", other_organisation, role="admin")

    response = admin_client.delete(f"/api/v1/admin/users/{lead.id}")

    assert response.status_code == 409
    assert "last admin of Other" in response.get_json()["message"]
