from __future__ import annotations


def test_health_is_exempt_from_login_gate(anon_client) -> None:
    response = anon_client.get("/api/v1/health")

    assert response.status_code == 200


def test_capabilities_requires_login(anon_client) -> None:
    response = anon_client.get("/api/v1/capabilities")

    assert response.status_code == 401


def test_register_creates_and_logs_in_user(anon_client) -> None:
    response = anon_client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "password123"},
    )

    assert response.status_code == 201
    assert response.get_json()["email"] == "new@example.com"

    me_response = anon_client.get("/api/v1/auth/me")

    assert me_response.status_code == 200
    assert me_response.get_json()["email"] == "new@example.com"


def test_register_rejects_duplicate_email(anon_client) -> None:
    payload = {"email": "dup@example.com", "password": "password123"}

    first = anon_client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = anon_client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


def test_register_rejects_short_password(anon_client) -> None:
    response = anon_client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )

    assert response.status_code == 400


def test_login_with_correct_credentials(anon_client, test_user) -> None:
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )

    assert response.status_code == 200
    assert response.get_json()["email"] == test_user.email


def test_login_with_wrong_password(anon_client, test_user) -> None:
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_login(anon_client) -> None:
    response = anon_client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_returns_current_user(client, test_user) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.get_json()["email"] == test_user.email


def test_logout_ends_session(client) -> None:
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200

    after_logout = client.get("/api/v1/auth/me")
    assert after_logout.status_code == 401


def test_csrf_token_is_exempt_from_login_gate(anon_client) -> None:
    response = anon_client.get("/api/v1/auth/csrf-token")

    assert response.status_code == 200
    assert "csrfToken" in response.get_json()
