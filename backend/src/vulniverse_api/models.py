from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .extensions import db


class VulnerabilityRecord(db.Model):
    __tablename__ = "vulnerability_record"

    id: Mapped[int] = mapped_column(primary_key=True)

    identifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    profile: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="cve-5.2.0",
    )

    document: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    is_draft: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Template(db.Model):
    __tablename__ = "template"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )

    # A list of {"path": "containers.cna.affected.0.vendor", "value": "Acme"}
    # entries — arbitrary and unvalidated against any schema, applied by
    # the frontend as a set of targeted writes onto whatever record is
    # currently open.
    fields: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class CnaPublication(db.Model):
    __tablename__ = "cna_publication"
    __table_args__ = (
        UniqueConstraint("record_identifier", "target", name="uq_cna_publication_record_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # The Vulniverse VulnerabilityRecord.identifier this tracks — not a
    # foreign key, since a record can be deleted/renamed independently of
    # its publication history.
    record_identifier: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
    )

    # "vl" | "cve-program" — matches an [integrations.<target>] table in
    # config/vulniverse.toml. One row per (record, target) pair.
    target: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # A PublicationStatus value (services/cna_publication.py). Stored as a
    # plain string, not a SQL enum, matching the rest of this file's
    # "validation lives elsewhere" style.
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    cve_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Credential-scrubbed (see services/cna_publication.py) before storage.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
