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


class Patch2VulnBatch(
    db.Model,  # type: ignore[name-defined]
):
    """Commits submitted to Patch2Vuln together, for review one by one.

    Belongs to an organisation like its records: every member sees it.
    """

    __tablename__ = "patch2vuln_batch"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisation.id"),
        nullable=False,
        index=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id"),
        nullable=True,
    )

    created_by: Mapped[User | None] = relationship()

    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    # The profile the candidates are reviewed in.
    profile: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    candidates: Mapped[list[Patch2VulnCandidate]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="Patch2VulnCandidate.position",
    )


class Patch2VulnCandidate(
    db.Model,  # type: ignore[name-defined]
):
    """One commit of a batch: its Patch2Vuln job and what came of it."""

    __tablename__ = "patch2vuln_candidate"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey("patch2vuln_batch.id"),
        nullable=False,
        index=True,
    )

    batch: Mapped[Patch2VulnBatch] = relationship(
        back_populates="candidates",
    )

    # Submission order.
    position: Mapped[int] = mapped_column(
        nullable=False,
    )

    # The commits analysed together for one vulnerability (Patch2Vuln
    # forgets a job's input once it has run).
    commit_urls: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    job_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    # The job's last known status: queued, running, completed, failed,
    # canceled, or expired (Patch2Vuln no longer knows the job).
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="queued",
    )

    # Copied once the job succeeds: Patch2Vuln deletes results after a
    # while (a day by default), reviewing a batch can take longer.
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    dismissed: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    # The record created from this candidate.
    record_id: Mapped[int | None] = mapped_column(
        ForeignKey("vulnerability_record.id"),
        nullable=True,
        unique=True,
    )
