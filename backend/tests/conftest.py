from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.security import generate_password_hash

from vulniverse_api import app_config, create_app
from vulniverse_api.extensions import db
from vulniverse_api.models import User


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Flask]:
    # Neither file exists, so load_app_config() falls back to its built-in
    # defaults (every panel enabled) instead of whatever this checkout's
    # config/vulniverse.toml(.sample) happens to say.
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")
    app_config.load_app_config.cache_clear()

    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        # Flask-WTF's own documented testing convention — the test client
        # doesn't do the browser-side CSRF-token dance the real frontend
        # does, so mutating requests would otherwise all 400.
        "WTF_CSRF_ENABLED": False,
        # A fresh, real key per test run — tests that exercise per-user
        # CNA credential encryption need this to actually round-trip.
        "CNA_CREDENTIAL_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        # The test suite exercises register/login/logout/admin routes,
        # which are @multiuser_only (404 in local mode) — overrides
        # whatever config/vulniverse.toml(.sample) says, same mechanism
        # as every other setting above.
        "VULNIVERSE_MODE": "multiuser",
    })

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()

    app_config.load_app_config.cache_clear()


@pytest.fixture
def test_user(app: Flask) -> User:
    with app.app_context():
        user = User(
            email="test@example.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def admin_user(app: Flask) -> User:
    with app.app_context():
        user = User(
            email="admin@example.com",
            password_hash=generate_password_hash("password123"),
            is_admin=True,
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def anon_client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def client(app: Flask, test_user: User) -> FlaskClient:
    test_client = app.test_client()

    with test_client.session_transaction() as session:
        session["_user_id"] = str(test_user.id)

    return test_client


@pytest.fixture
def admin_client(app: Flask, admin_user: User) -> FlaskClient:
    test_client = app.test_client()

    with test_client.session_transaction() as session:
        session["_user_id"] = str(admin_user.id)

    return test_client


@pytest.fixture
def other_user(app: Flask) -> User:
    with app.app_context():
        user = User(
            email="other@example.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def other_client(app: Flask, other_user: User) -> FlaskClient:
    test_client = app.test_client()

    with test_client.session_transaction() as session:
        session["_user_id"] = str(other_user.id)

    return test_client
