from __future__ import annotations

from vulniverse_api.extensions import db
from vulniverse_api.models import User


def test_list_users_requires_login(anon_client) -> None:
    response = anon_client.get("/api/v1/admin/users")

    assert response.status_code == 401


def test_list_users_requires_admin(client) -> None:
    response = client.get("/api/v1/admin/users")

    assert response.status_code == 403


def test_admin_can_list_users(admin_client, test_user: User) -> None:
    response = admin_client.get("/api/v1/admin/users")

    assert response.status_code == 200

    emails = {user["email"] for user in response.get_json()["users"]}

    assert test_user.email in emails
    assert "admin@example.com" in emails


def test_admin_can_promote_a_user(admin_client, test_user: User) -> None:
    response = admin_client.put(
        f"/api/v1/admin/users/{test_user.id}",
        json={"isAdmin": True},
    )

    assert response.status_code == 200
    assert response.get_json()["isAdmin"] is True


def test_admin_can_deactivate_a_user(admin_client, test_user: User) -> None:
    response = admin_client.put(
        f"/api/v1/admin/users/{test_user.id}",
        json={"isActive": False},
    )

    assert response.status_code == 200
    assert response.get_json()["isActive"] is False


def test_admin_cannot_demote_self(admin_client, admin_user: User) -> None:
    response = admin_client.put(
        f"/api/v1/admin/users/{admin_user.id}",
        json={"isAdmin": False},
    )

    assert response.status_code == 400


def test_admin_cannot_deactivate_self(admin_client, admin_user: User) -> None:
    response = admin_client.put(
        f"/api/v1/admin/users/{admin_user.id}",
        json={"isActive": False},
    )

    assert response.status_code == 400


def test_update_unknown_user_is_404(admin_client) -> None:
    response = admin_client.put(
        "/api/v1/admin/users/999999",
        json={"isAdmin": True},
    )

    assert response.status_code == 404


def test_deactivated_user_cannot_login(client, test_user: User, app) -> None:
    with app.app_context():
        user = db.session.get(User, test_user.id)
        assert user is not None
        user.is_active = False
        db.session.commit()

    anon = app.test_client()
    response = anon.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )

    assert response.status_code == 403


def test_deactivating_a_user_ends_their_existing_session(
    app, client, test_user: User,
) -> None:
    # client is already logged in as test_user; deactivate the row
    # directly (the admin endpoint's own behavior is covered by
    # test_admin_can_deactivate_a_user above) and confirm the existing
    # session loses access immediately, not just on its next login.
    with app.app_context():
        user = db.session.get(User, test_user.id)
        assert user is not None
        user.is_active = False
        db.session.commit()

    response = client.get("/api/v1/records")

    assert response.status_code == 401
