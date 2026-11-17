from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ..extensions import db
from .user import User

# "admin" manages the organisation's members and settings, "editor" works
# on its records. Both can read and change every record of the
# organisation, drafts included.
MEMBERSHIP_ROLES = ("admin", "editor")


class Organisation(
    db.Model,  # type: ignore[name-defined]
):
    """A team that owns records together, e.g. one CNA."""

    __tablename__ = "organisation"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # Stable, URL-safe handle; the name may change.
    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Membership(
    db.Model,  # type: ignore[name-defined]
):
    """A user's place in an organisation, with their role there."""

    __tablename__ = "membership"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organisation_id",
            name="uq_membership_user_organisation",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id"),
        nullable=False,
        index=True,
    )

    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisation.id"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="editor",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship()
    organisation: Mapped[Organisation] = relationship()


class Invitation(
    db.Model,  # type: ignore[name-defined]
):
    """A single-use link to join an organisation with a role.

    Only a hash of the link's token is stored, so the database alone
    can't be used to join; the link itself is shown once, on creation.
    """

    __tablename__ = "invitation"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisation.id"),
        nullable=False,
        index=True,
    )

    # SHA-256 of the token, hex.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )

    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Set once used (single use) or revoked; either ends the invitation.
    accepted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"),
        nullable=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    organisation: Mapped[Organisation] = relationship()
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    accepted_by: Mapped[User | None] = relationship(foreign_keys=[accepted_by_id])
