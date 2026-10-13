from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ..extensions import db
from .user import User


class Template(
    db.Model,
):  # type: ignore[name-defined]
    __tablename__ = "template"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    profile: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="cve-5.2.0",
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    # Attribution only, not access control. Every logged-in user can
    # still view/edit/delete templates regardless of who created them.
    created_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey("user.id"),
        nullable=True,
    )

    created_by: Mapped[
        User | None
    ] = relationship(
        foreign_keys=[
            created_by_id,
        ],
    )

    # A list such as:
    #
    # {
    #     "path": "containers.cna.affected.0.vendor",
    #     "value": "Acme",
    # }
    #
    # Template fields belong to the profile above and should only be
    # offered for documents using that same profile.
    fields: Mapped[
        list[dict[str, Any]]
    ] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
