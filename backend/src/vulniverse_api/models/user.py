from __future__ import annotations

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
