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
from urllib.parse import quote

from flask import current_app

from ..extensions import db
from ..models import User
from .cna_credentials import fernet

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
    """Store the secret once the user proves their app has it."""
    step = matching_step(secret, code)
    if step is None:
        return False

    user.two_factor_secret_encrypted = fernet().encrypt(secret.encode()).decode()
    user.two_factor_last_step = step
    user.two_factor_failures = 0
    db.session.commit()
    return True


def reset(user: User) -> None:
    """Forget the secret (a lost device); the user sets it up again."""
    user.two_factor_secret_encrypted = None
    user.two_factor_last_step = None
    user.two_factor_failures = 0
    user.two_factor_failed_at = None
    db.session.commit()


def paused(user: User) -> bool:
    """Too many wrong codes lately: refuse codes for a while, so they
    can't be guessed (a million of them, three valid at a time)."""
    return (
        user.two_factor_failures >= MAX_FAILURES
        and user.two_factor_failed_at is not None
        and datetime.now(UTC) - _aware(user.two_factor_failed_at) < FAILURE_PAUSE
    )


def verify(user: User, code: str) -> bool:
    """Check a login code; each code works once. The caller checks
    paused() first."""
    assert user.two_factor_secret_encrypted is not None
    secret = fernet().decrypt(user.two_factor_secret_encrypted.encode()).decode()
    step = matching_step(secret, code)

    if step is None or step <= (user.two_factor_last_step or -1):
        if user.two_factor_failures >= MAX_FAILURES:
            user.two_factor_failures = 0  # the pause is over: a fresh count
        user.two_factor_failures += 1
        user.two_factor_failed_at = datetime.now(UTC)
        db.session.commit()
        return False

    user.two_factor_last_step = step
    user.two_factor_failures = 0
    user.two_factor_failed_at = None
    db.session.commit()
    return True


def _aware(moment: datetime) -> datetime:
    # SQLite gives naive datetimes back; they are UTC.
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
