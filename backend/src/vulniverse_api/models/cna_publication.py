from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
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


class CnaPublication(
    db.Model,
):  # type: ignore[name-defined]
    __tablename__ = "cna_publication"

    __table_args__ = (
        UniqueConstraint(
            "record_identifier",
            "target",
            name=(
                "uq_cna_publication_"
                "record_target"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    # Vulniverse VulnerabilityRecord.identifier this publication tracks.
    #
    # This deliberately is not a foreign key because records can be
    # deleted or renamed independently of publication history.
    record_identifier: Mapped[
        str
    ] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    # "vl" | "cve-program".
    #
    # Matches UserCnaCredential.target for the user who triggered the
    # publication. One row exists per (record, target) pair.
    target: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # A PublicationStatus value from services/cna_publication.py.
    # Stored as a plain string rather than a SQL enum.
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    cve_id: Mapped[
        str | None
    ] = mapped_column(
        String(64),
        nullable=True,
    )

    reserved_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    published_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rejected_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Credential-scrubbed before storage.
    last_error: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    last_request: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    last_response: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
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
