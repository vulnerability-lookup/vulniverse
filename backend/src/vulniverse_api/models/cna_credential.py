from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from ..extensions import db


class UserCnaCredential(
    db.Model,
):  # type: ignore[name-defined]
    __tablename__ = "user_cna_credential"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "target",
            name=(
                "uq_user_cna_credential_"
                "user_target"
            ),
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

    # "vl" | "cve-program"
    # See KNOWN_TARGETS in services/cna_publication.py.
    target: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    cve_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    short_name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    org_id: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    cve_api_org: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    cve_api_user: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    # Encrypted at rest with Fernet using
    # CNA_CREDENTIAL_ENCRYPTION_KEY.
    # Never returned by an API response.
    cve_api_key_encrypted: Mapped[
        str
    ] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[
        datetime
    ] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
