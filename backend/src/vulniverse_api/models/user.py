from __future__ import annotations

import secrets
from datetime import datetime

from flask_login import UserMixin
from sqlalchemy import (
    DateTime,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from ..extensions import db


# db.Model is a Flask-SQLAlchemy 3.x dynamically-built declarative base.
# mypy cannot resolve it as a valid base class without introducing a
# custom DeclarativeBase.
class User(
    UserMixin,
    db.Model,  # type: ignore[name-defined]
):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    # A single admin/non-admin tier. Administration controls user
    # management only; record/template access remains separate.
    is_admin: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    # A deactivated account cannot log in, but its existing records,
    # templates, and created_by attribution remain untouched.
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    # Part of the session's user ID (get_id). A new one ends every session
    # of the account and every half-finished login: on deactivation, a
    # password change or reset and a 2FA reset (services/accounts.py's
    # end_sessions). Random, so a deleted account's cookie can't match a
    # new account that gets its ID (SQLite reuses the highest one).
    session_token: Mapped[str] = mapped_column(
        String(32), nullable=False, default=lambda: secrets.token_hex(16)
    )

    def get_id(self) -> str:
        return f"{self.id}:{self.session_token}"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Two-factor authentication (TOTP, services/two_factor.py), when
    # [server] two_factor is on. The secret is Fernet-encrypted; None
    # until the user sets it up.
    two_factor_secret_encrypted: Mapped[str | None] = mapped_column(String(256))

    # The last accepted code's time step: a code works only once.
    two_factor_last_step: Mapped[int | None] = mapped_column()

    # Wrong codes in a row, and when the last one came: too many and the
    # code step waits (TWO_FACTOR_MAX_FAILURES), against guessing codes.
    two_factor_failures: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    two_factor_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
