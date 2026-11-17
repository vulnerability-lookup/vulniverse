from __future__ import annotations

from typing import Any

from flask import current_app, request, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash, generate_password_hash

from ..auth.local_user import LOCAL_USER_EMAIL
from ..auth.organisations import (
    SESSION_KEY,
    current_organisation,
    is_member,
    memberships,
)
from ..auth.permissions import multiuser_only
from ..extensions import db
from ..models import User
from ..services.invitations import accept_invitation, find_invitation
from . import api_bp
from .organisations import invitation_error


@api_bp.get("/auth/csrf-token")
def csrf_token() -> dict[str, str]:
    # Exempt from the login gate — the frontend needs this before it can
    # even attempt /auth/login or /auth/register, both of which are
    # state-changing requests Flask-WTF's CSRFProtect checks too.
    return {"csrfToken": generate_csrf()}


def _serialize(user: User) -> dict[str, Any]:
    # After login_user(), so current_organisation() sees this user.
    current = current_organisation()

    return {
        "id": user.id,
        "email": user.email,
        "isAdmin": user.is_admin,
        "authMode": current_app.config["VULNIVERSE_MODE"],
        "organisations": [
            {
                "id": membership.organisation.id,
                "name": membership.organisation.name,
                "role": membership.role,
            }
            for membership in memberships(user)
        ],
        "currentOrganisationId": current.id if current else None,
    }


@api_bp.get("/auth/registration")
@multiuser_only
def registration_mode() -> tuple[dict, int]:
    """Who may register ([server] registration): "open", "invite" or
    "closed"; the register page adapts to it."""
    return {"mode": current_app.config["VULNIVERSE_REGISTRATION"]}, 200


@api_bp.post("/auth/register")
@multiuser_only
def register() -> tuple[dict, int]:
    """Create an account, joining an organisation if an invitation link's
    token comes along ("invitation"). Whether that's needed, or possible
    at all, is [server] registration's call."""
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    mode = current_app.config["VULNIVERSE_REGISTRATION"]

    if mode == "closed":
        return {"message": "Registration is closed on this instance."}, 403

    token = payload.get("invitation")
    invitation = None

    # Checked before the account exists, so a bad link doesn't leave one
    # behind without the organisation it was meant for.
    if token is not None:
        invitation = find_invitation(token) if isinstance(token, str) else None
        error = invitation_error(invitation)
        if error is not None:
            return error
    elif mode == "invite":
        return {
            "message": "Registration needs an invitation link from an organisation.",
        }, 403

    email = payload.get("email")
    password = payload.get("password")

    if not isinstance(email, str) or not email.strip():
        return {"message": "A non-empty 'email' is required."}, 400

    if not isinstance(password, str) or len(password) < 8:
        return {
            "message": "A password of at least 8 characters is required.",
        }, 400

    email = email.strip().lower()

    if email == LOCAL_USER_EMAIL:
        return {
            "message": "This email address is reserved."
        }, 400

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

    if invitation is not None:
        membership = accept_invitation(invitation, user)
        session[SESSION_KEY] = membership.organisation_id

    return _serialize(user), 201


@api_bp.post("/auth/login")
@multiuser_only
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
@multiuser_only
@login_required
def logout() -> tuple[dict, int]:
    logout_user()

    return {"message": "Logged out."}, 200


@api_bp.get("/auth/me")
def me() -> tuple[dict, int]:
    return _serialize(current_user), 200


@api_bp.post("/auth/organisation")
def switch_organisation() -> tuple[dict, int]:
    """Make one of the user's organisations the current one: where new
    records go and which records the list shows."""
    payload = request.get_json(silent=True)
    organisation_id = payload.get("id") if isinstance(payload, dict) else None

    # bool is an int subclass; True isn't an id.
    if not isinstance(organisation_id, int) or isinstance(organisation_id, bool):
        return {"message": "An integer 'id' is required."}, 400

    if not is_member(current_user, organisation_id):
        return {"message": "You are not a member of this organisation."}, 403

    session[SESSION_KEY] = organisation_id

    return _serialize(current_user), 200
