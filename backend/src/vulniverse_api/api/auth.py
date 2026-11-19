from __future__ import annotations

import time
from typing import Any

from flask import current_app, request, session
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

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
from ..services import two_factor
from ..services.accounts import (
    delete_account,
    deletion_problem,
    password_matches,
    password_problem,
    set_password,
)
from ..services.invitations import accept_invitation, find_invitation
from . import api_bp
from .invitations import USED_MEANWHILE, invitation_error


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
        "twoFactor": {
            "required": two_factor.required(),
            "enabled": two_factor.is_set_up(user),
        },
    }


TWO_FACTOR_KEYS = (
    two_factor.PASSED_KEY,
    two_factor.PENDING_KEY,
    two_factor.SETUP_KEY,
)


def start_session(user: User, *, passed_two_factor: bool = False) -> None:
    """Log the user in, with no 2FA state left from an earlier login in
    this browser."""
    for key in TWO_FACTOR_KEYS:
        session.pop(key, None)
    login_user(user)
    if passed_two_factor:
        session[two_factor.PASSED_KEY] = True


def end_session() -> None:
    logout_user()
    for key in TWO_FACTOR_KEYS:
        session.pop(key, None)


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

    problem = password_problem(password)
    if problem or not isinstance(password, str):
        return {"message": problem}, 400

    email = email.strip().lower()

    if email == LOCAL_USER_EMAIL:
        return {"message": "This email address is reserved."}, 400

    existing = User.query.filter_by(email=email).first()

    if existing:
        return {"message": "An account with this email already exists."}, 409

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)

    # With an invitation, the account and its membership are saved
    # together, or neither (the link was used meanwhile).
    membership = None
    try:
        if invitation is not None:
            membership = accept_invitation(invitation, user)
            if membership is None:
                return USED_MEANWHILE
        else:
            db.session.commit()
    except IntegrityError:
        # The same address registered at the same moment.
        db.session.rollback()
        return {"message": "An account with this email already exists."}, 409

    start_session(user)
    if membership is not None:
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

    invalid = {"message": "Invalid email or password."}, 401

    if user is None:
        # Takes as long as a wrong password, so timing reveals no accounts.
        password_matches(None, password)
        return invalid

    if not password_matches(user, password):
        return invalid

    if not user.is_active:
        return {"message": "This account has been deactivated."}, 403

    if two_factor.required() and two_factor.is_set_up(user):
        end_session()
        # The session cookie is signed, so this can't be forged; the
        # session token ends it on a password or 2FA reset meanwhile.
        session[two_factor.PENDING_KEY] = {
            "userId": user.id,
            "sessionToken": user.session_token,
            "at": time.time(),
        }
        return {"twoFactorRequired": True}, 200

    # Without 2FA set up yet, the session can only set it up (require_login).
    start_session(user)

    return _serialize(user), 200


@api_bp.post("/auth/login/two-factor")
@multiuser_only
def login_two_factor() -> tuple[dict, int]:
    """{"code"}: the second login step, after the password."""
    pending = session.get(two_factor.PENDING_KEY)
    if not isinstance(pending, dict):
        pending = {}
    user = None
    if time.time() - pending.get("at", 0) <= two_factor.PENDING_SECONDS:
        user = db.session.get(User, pending.get("userId"), populate_existing=True)

    if (
        user is None
        or user.session_token != pending.get("sessionToken")
        or not user.is_active
        or not two_factor.is_set_up(user)
    ):
        session.pop(two_factor.PENDING_KEY, None)
        return {"message": "Log in again with your password."}, 401

    payload = request.get_json(silent=True)
    code = payload.get("code") if isinstance(payload, dict) else None
    if not isinstance(code, str):
        return {"message": "A 'code' is required."}, 400

    outcome = two_factor.check_code(user, code)
    if outcome == "paused":
        return {"message": "Too many wrong codes; wait 15 minutes."}, 429
    if outcome == "wrong":
        return {"message": "That code is wrong or was already used."}, 400

    start_session(user, passed_two_factor=True)

    return _serialize(user), 200


def refresh_session(user: User) -> None:
    """After the user's own password change (which ends all their
    sessions): keep this one, with the new session token."""
    login_user(user)


def confirm_password(payload: dict, key: str) -> tuple[dict, int] | None:
    """The logged-in user's password, asked again before changing it or
    deleting the account."""
    password = payload.get(key)
    if not isinstance(password, str) or not password_matches(current_user, password):
        return {"message": "Your current password is wrong."}, 403

    return None


@api_bp.post("/auth/logout")
@multiuser_only
@login_required
def logout() -> tuple[dict, int]:
    end_session()

    return {"message": "Logged out."}, 200


@api_bp.get("/auth/me")
def me() -> tuple[dict, int]:
    return _serialize(current_user), 200


@api_bp.post("/auth/password")
@multiuser_only
def change_password() -> tuple[dict, int]:
    """{"currentPassword", "newPassword"}: change your own password."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    problem = password_problem(payload.get("newPassword"))
    if problem:
        return {"message": problem}, 400

    error = confirm_password(payload, "currentPassword")
    if error is not None:
        return error

    set_password(current_user, payload["newPassword"])
    refresh_session(current_user._get_current_object())  # the User, not the proxy

    return {"message": "Password changed."}, 200


@api_bp.delete("/auth/account")
@multiuser_only
def delete_own_account() -> tuple[dict, int]:
    """{"password"}: delete your own account (see services/accounts.py for
    what goes with it), and log out."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    error = confirm_password(payload, "password")
    if error is not None:
        return error

    problem = deletion_problem(current_user)
    if problem:
        return {"message": problem}, 409

    user = current_user._get_current_object()  # the User, not the proxy
    end_session()
    delete_account(user)

    return {"message": "Account deleted."}, 200


@api_bp.post("/auth/two-factor/setup")
@multiuser_only
def start_two_factor_setup() -> tuple[dict, int]:
    """A new secret for the user's authenticator app; it's stored once
    POST /auth/two-factor confirms a code from it. Losing the device
    means an admin resets it (or `flask reset-two-factor`)."""
    if not two_factor.required():
        return {"message": "Two-factor authentication is off on this instance."}, 404
    if two_factor.is_set_up(current_user):
        return {"message": "Two-factor authentication is already set up."}, 409

    secret = two_factor.generate_secret()
    session[two_factor.SETUP_KEY] = {
        "secret": secret,
        "userId": current_user.id,
        "at": time.time(),
    }

    return {
        "secret": secret,
        "uri": two_factor.provisioning_uri(secret, current_user.email),
    }, 200


@api_bp.post("/auth/two-factor")
@multiuser_only
def finish_two_factor_setup() -> tuple[dict, int]:
    """{"code"}: a code from the app, proving it has the secret."""
    setup = session.get(two_factor.SETUP_KEY)
    if (
        not isinstance(setup, dict)
        or setup.get("userId") != current_user.id
        or time.time() - setup.get("at", 0) > two_factor.SETUP_SECONDS
        or two_factor.is_set_up(current_user)
    ):
        session.pop(two_factor.SETUP_KEY, None)
        return {"message": "Start the setup again."}, 409

    payload = request.get_json(silent=True)
    code = payload.get("code") if isinstance(payload, dict) else None
    if not isinstance(code, str) or not two_factor.enable(
        current_user, setup["secret"], code
    ):
        return {"message": "That code is wrong; check the time on your device."}, 400

    session.pop(two_factor.SETUP_KEY, None)
    session[two_factor.PASSED_KEY] = True
    db.session.refresh(current_user)

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
