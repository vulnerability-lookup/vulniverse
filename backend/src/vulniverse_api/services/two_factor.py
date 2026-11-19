"""Two-factor authentication with TOTP (RFC 6238: 6 digits, 30-second
steps, SHA-1), as authenticator apps expect. Secrets are encrypted with
the same key as the CNA credentials."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast
from urllib.parse import quote

from flask import current_app
from sqlalchemy import CursorResult, Result, case, or_, update

from ..extensions import db
from ..models import User
from .accounts import end_sessions
from .cna_credentials import fernet

# Session keys. PASSED: this session entered a code or set 2FA up; with
# 2FA required, nothing else counts (api/__init__.py's require_login).
PASSED_KEY = "two_factor_passed"
# Between the password and the code: {userId, sessionToken, at}.
PENDING_KEY = "two_factor_pending"
PENDING_SECONDS = 300
# A secret being set up: {secret, userId, at}.
SETUP_KEY = "two_factor_setup"
SETUP_SECONDS = 600

STEP_SECONDS = 30
DIGITS = 6
MAX_FAILURES = 5
FAILURE_PAUSE = timedelta(minutes=15)


def required() -> bool:
    """[server] two_factor: every account must set it up (multi-user
    mode only; local mode has no logins)."""
    return bool(
        current_app.config["VULNIVERSE_TWO_FACTOR"]
        and current_app.config["VULNIVERSE_MODE"] == "multiuser"
    )


def generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret: str, step: int) -> str:
    digest = hmac.new(
        base64.b32decode(secret), struct.pack(">Q", step), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**DIGITS).zfill(DIGITS)


def matching_step(secret: str, code: str, now: float | None = None) -> int | None:
    """The time step the code belongs to, allowing one step of clock
    drift either way, or None."""
    code = code.replace(" ", "")
    current = int((time.time() if now is None else now) // STEP_SECONDS)
    for step in (current - 1, current, current + 1):
        if hmac.compare_digest(code_at(secret, step), code):
            return step
    return None


def provisioning_uri(secret: str, email: str, issuer: str = "Vulniverse") -> str:
    """What the QR code holds, for authenticator apps."""
    return (
        f"otpauth://totp/{quote(issuer)}:{quote(email)}"
        f"?secret={secret}&issuer={quote(issuer)}"
    )


def is_set_up(user: User) -> bool:
    return user.two_factor_secret_encrypted is not None


def enable(user: User, secret: str, code: str) -> bool:
    """Store the secret once the user proves their app has it. False for
    a wrong code, or when another session set one up meanwhile."""
    step = matching_step(secret, code)
    if step is None:
        return False

    # Only if there's still no secret: two setups at once can't both win.
    stored = db.session.execute(
        update(User)
        .where(User.id == user.id, User.two_factor_secret_encrypted.is_(None))
        .values(
            two_factor_secret_encrypted=fernet().encrypt(secret.encode()).decode(),
            two_factor_last_step=step,
            two_factor_failures=0,
            two_factor_failed_at=None,
        ),
        execution_options={"synchronize_session": False},
    )
    db.session.commit()
    return _changed(stored)


def reset(user: User) -> None:
    """Forget the secret (a lost device) and end the account's sessions;
    the user logs in again and sets it up anew."""
    user.two_factor_secret_encrypted = None
    user.two_factor_last_step = None
    user.two_factor_failures = 0
    user.two_factor_failed_at = None
    end_sessions(user)
    db.session.commit()


def check_code(user: User, code: str) -> Literal["ok", "wrong", "paused"]:
    """Check a login code. Each code works once, and after MAX_FAILURES
    wrong ones codes are refused for FAILURE_PAUSE, so they can't be
    guessed (a million of them, three valid at a time).

    Both happen in single UPDATEs, so parallel requests can't each get
    their own count of guesses or use the same code twice."""
    now = datetime.now(UTC)

    # Count the attempt before checking it; a right code resets the count.
    counted = db.session.execute(
        update(User)
        .where(
            User.id == user.id,
            or_(
                User.two_factor_failures < MAX_FAILURES,
                User.two_factor_failed_at.is_(None),
                User.two_factor_failed_at < now - FAILURE_PAUSE,
            ),
        )
        .values(
            # After a pause, counting starts over.
            two_factor_failures=case(
                (User.two_factor_failures >= MAX_FAILURES, 1),
                else_=User.two_factor_failures + 1,
            ),
            two_factor_failed_at=now,
        ),
        execution_options={"synchronize_session": False},
    )
    db.session.commit()
    if not _changed(counted):
        return "paused"

    assert user.two_factor_secret_encrypted is not None
    secret = fernet().decrypt(user.two_factor_secret_encrypted.encode()).decode()
    step = matching_step(secret, code)
    if step is None:
        return "wrong"

    accepted = db.session.execute(
        update(User)
        .where(
            User.id == user.id,
            or_(
                User.two_factor_last_step.is_(None),
                User.two_factor_last_step < step,
            ),
        )
        .values(
            two_factor_last_step=step,
            two_factor_failures=0,
            two_factor_failed_at=None,
        ),
        execution_options={"synchronize_session": False},
    )
    db.session.commit()
    return "ok" if _changed(accepted) else "wrong"


def _changed(result: Result[Any]) -> bool:
    return cast(CursorResult[Any], result).rowcount == 1
