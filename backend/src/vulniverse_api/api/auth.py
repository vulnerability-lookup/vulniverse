from __future__ import annotations

from typing import Any

from flask import request
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import User
from . import api_bp


@api_bp.get("/auth/csrf-token")
def csrf_token() -> dict[str, str]:
    # Exempt from the login gate — the frontend needs this before it can
    # even attempt /auth/login or /auth/register, both of which are
    # state-changing requests Flask-WTF's CSRFProtect checks too.
    return {"csrfToken": generate_csrf()}


def _serialize(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "isAdmin": user.is_admin,
    }


@api_bp.post("/auth/register")
def register() -> tuple[dict, int]:
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not email.strip():
        return {"message": "A non-empty 'email' is required."}, 400

    if not isinstance(password, str) or len(password) < 8:
        return {
            "message": "A password of at least 8 characters is required.",
        }, 400

    email = email.strip().lower()

    existing = User.query.filter_by(email=email).first()

    if existing:
        return {"message": "An account with this email already exists."}, 409

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
    )

    db.session.add(user)
    db.session.commit()

    login_user(user)

    return _serialize(user), 201


@api_bp.post("/auth/login")
def login() -> tuple[dict, int]:
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not isinstance(password, str):
        return {"message": "'email' and 'password' are required."}, 400

    user = User.query.filter_by(email=email.strip().lower()).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return {"message": "Invalid email or password."}, 401

    if not user.is_active:
        return {"message": "This account has been deactivated."}, 403

    login_user(user)

    return _serialize(user), 200


@api_bp.post("/auth/logout")
@login_required
def logout() -> tuple[dict, int]:
    logout_user()

    return {"message": "Logged out."}, 200


@api_bp.get("/auth/me")
def me() -> tuple[dict, int]:
    return _serialize(current_user), 200
