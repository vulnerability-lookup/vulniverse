"""Two-factor authentication: the TOTP maths, setup, the login code
step, its guard against guessing, and the [server] two_factor gate.
One client per test (see insert_record in test_records_api.py)."""

from __future__ import annotations

import base64
import time

import pytest
from conftest import logged_in_client
from flask import g
from sqlalchemy.orm import Session

from vulniverse_api.extensions import db
from vulniverse_api.models import User
from vulniverse_api.services import two_factor

SECRET = base64.b32encode(b"12345678901234567890").decode()


def test_codes_match_the_rfc_6238_test_vector() -> None:
    # RFC 6238 appendix B, SHA-1, T=59s: 94287082 (8 digits).
    assert two_factor.code_at(SECRET, 59 // 30) == "287082"
    assert two_factor.matching_step(SECRET, "287 082", now=59) == 1
    assert two_factor.matching_step(SECRET, "287082", now=59 + 90) is None


def now_code(secret: str = SECRET, offset: int = 0) -> str:
    return two_factor.code_at(secret, int(time.time() // 30) + offset)


@pytest.fixture
def required(app):
    app.config["VULNIVERSE_TWO_FACTOR"] = True


def set_up(app, user_id: int) -> None:
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        assert two_factor.enable(user, SECRET, now_code(offset=-1))


def login(client, password: str = "password123"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": password},
    )


def test_off_by_default_nothing_changes(app, client) -> None:
    assert client.get("/api/v1/records").status_code == 200
    assert client.get("/api/v1/auth/me").get_json()["twoFactor"] == {
        "required": False,
        "enabled": False,
    }


def test_when_required_an_account_without_it_can_only_set_it_up(
    app, required, client
) -> None:
    refused = client.get("/api/v1/records")
    assert refused.status_code == 403
    assert refused.get_json()["code"] == "TWO_FACTOR_SETUP_REQUIRED"

    setup = client.post("/api/v1/auth/two-factor/setup").get_json()
    assert setup["uri"].startswith("otpauth://totp/Vulniverse:test%40example.com?")
    wrong = client.post("/api/v1/auth/two-factor", json={"code": "000000"})
    assert wrong.status_code == 400

    done = client.post(
        "/api/v1/auth/two-factor", json={"code": now_code(setup["secret"])}
    )
    assert done.status_code == 200
    assert done.get_json()["twoFactor"]["enabled"] is True
    assert client.get("/api/v1/records").status_code == 200


def test_login_asks_for_the_code_after_the_password(
    app, required, anon_client, test_user
) -> None:
    set_up(app, test_user.id)

    first = login(anon_client)
    assert first.get_json() == {"twoFactorRequired": True}
    assert anon_client.get("/api/v1/auth/me").status_code == 401

    second = anon_client.post(
        "/api/v1/auth/login/two-factor", json={"code": now_code()}
    )
    assert second.status_code == 200
    assert anon_client.get("/api/v1/records").status_code == 200


def test_a_code_works_only_once(app, required, anon_client, test_user) -> None:
    set_up(app, test_user.id)
    login(anon_client)
    code = now_code()
    anon_client.post("/api/v1/auth/login/two-factor", json={"code": code})
    anon_client.post("/api/v1/auth/logout")

    login(anon_client)
    again = anon_client.post("/api/v1/auth/login/two-factor", json={"code": code})
    assert again.status_code == 400


def test_the_code_step_needs_the_password_first(app, required, anon_client) -> None:
    response = anon_client.post(
        "/api/v1/auth/login/two-factor", json={"code": now_code()}
    )
    assert response.status_code == 401


def test_too_many_wrong_codes_pause_the_code_step(
    app, required, anon_client, test_user
) -> None:
    set_up(app, test_user.id)
    login(anon_client)

    for _ in range(two_factor.MAX_FAILURES):
        response = anon_client.post(
            "/api/v1/auth/login/two-factor", json={"code": "000000"}
        )
        assert response.status_code == 400

    paused = anon_client.post(
        "/api/v1/auth/login/two-factor", json={"code": now_code()}
    )
    assert paused.status_code == 429


def switching():
    """Before a request from another client in the same test: the app
    fixture's context caches the last request's user on g (see
    insert_record in test_records_api.py)."""
    g.pop("_login_user", None)


def passed_client(app, user):
    """A session that entered its 2FA code."""
    client = logged_in_client(app, user)
    with client.session_transaction() as session:
        session[two_factor.PASSED_KEY] = True
    return client


def test_admins_reset_it(app, required, admin_user, test_user) -> None:
    set_up(app, admin_user.id)
    set_up(app, test_user.id)
    admin_client = passed_client(app, admin_user)

    response = admin_client.delete(f"/api/v1/admin/users/{test_user.id}/two-factor")

    assert response.get_json()["twoFactorEnabled"] is False
    with app.app_context():
        user = db.session.get(User, test_user.id)
        assert user is not None and user.two_factor_secret_encrypted is None


def test_the_secret_is_stored_encrypted(app, test_user) -> None:
    set_up(app, test_user.id)
    with app.app_context():
        user = db.session.get(User, test_user.id)
        assert user is not None
        stored = user.two_factor_secret_encrypted
    assert stored is not None and SECRET not in stored


def test_setup_is_refused_when_off(app, test_user) -> None:
    client = logged_in_client(app, test_user)
    assert client.post("/api/v1/auth/two-factor/setup").status_code == 404


# --- Sessions: 2FA is per session, and resets end them -----------------------


def test_setting_up_in_one_session_does_not_unlock_another(
    app, required, test_user
) -> None:
    password_only = logged_in_client(app, test_user)
    set_up(app, test_user.id)  # in another session
    switching()

    assert password_only.get("/api/v1/records").status_code == 401
    assert password_only.get("/api/v1/auth/me").status_code == 401


def test_a_password_change_ends_the_other_sessions_only(app, test_user) -> None:
    mine = logged_in_client(app, test_user)
    other = logged_in_client(app, test_user)

    response = mine.post(
        "/api/v1/auth/password",
        json={"currentPassword": "password123", "newPassword": "new-password-456"},
    )

    assert response.status_code == 200
    switching()
    assert mine.get("/api/v1/auth/me").status_code == 200
    switching()
    assert other.get("/api/v1/auth/me").status_code == 401


def test_an_admin_password_reset_ends_sessions_and_logins_halfway(
    app, required, admin_user, test_user, anon_client
) -> None:
    set_up(app, admin_user.id)
    set_up(app, test_user.id)
    session = passed_client(app, test_user)
    login(anon_client)  # password done, code not yet
    switching()

    passed_client(app, admin_user).post(
        f"/api/v1/admin/users/{test_user.id}/reset-password"
    )

    switching()
    assert session.get("/api/v1/auth/me").status_code == 401
    switching()
    halfway = anon_client.post(
        "/api/v1/auth/login/two-factor", json={"code": now_code()}
    )
    assert halfway.status_code == 401


def test_a_two_factor_reset_ends_sessions(app, required, admin_user, test_user) -> None:
    set_up(app, admin_user.id)
    set_up(app, test_user.id)
    session = passed_client(app, test_user)

    passed_client(app, admin_user).delete(
        f"/api/v1/admin/users/{test_user.id}/two-factor"
    )

    switching()
    assert session.get("/api/v1/auth/me").status_code == 401


def test_logout_drops_a_setup_in_progress(app, required, client) -> None:
    client.post("/api/v1/auth/two-factor/setup")
    client.post("/api/v1/auth/logout")

    with client.session_transaction() as session:
        assert two_factor.SETUP_KEY not in session


def test_a_setup_expires(app, required, client) -> None:
    secret = client.post("/api/v1/auth/two-factor/setup").get_json()["secret"]
    with client.session_transaction() as session:
        setup = session[two_factor.SETUP_KEY]
        # Reassigned: the session doesn't notice changes inside the dict.
        session[two_factor.SETUP_KEY] = {
            **setup,
            "at": setup["at"] - two_factor.SETUP_SECONDS - 1,
        }

    response = client.post("/api/v1/auth/two-factor", json={"code": now_code(secret)})
    assert response.status_code == 409


# --- Parallel requests -------------------------------------------------------


def copies(app, user_id: int, count: int) -> list[User]:
    """The user as several requests at once each loaded it."""
    loaded = []
    for _ in range(count):
        with Session(db.engine) as session:
            user = session.get(User, user_id)
            assert user is not None
            session.expunge(user)
            loaded.append(user)
    return loaded


def test_a_code_works_once_even_in_parallel(app, test_user) -> None:
    set_up(app, test_user.id)
    with app.app_context():
        first, second = copies(app, test_user.id, 2)
        code = now_code()

        assert two_factor.check_code(first, code) == "ok"
        assert two_factor.check_code(second, code) == "wrong"


def test_parallel_wrong_codes_all_count(app, test_user) -> None:
    set_up(app, test_user.id)
    with app.app_context():
        loaded = copies(app, test_user.id, two_factor.MAX_FAILURES + 1)

        for user in loaded[:-1]:
            assert two_factor.check_code(user, "000000") == "wrong"
        assert two_factor.check_code(loaded[-1], now_code()) == "paused"
