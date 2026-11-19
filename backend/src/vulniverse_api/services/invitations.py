"""Invitation links: single use, valid for INVITATION_LIFETIME, revocable.

The link carries a random token; the database keeps only its SHA-256, so
a copy of the database can't be used to join an organisation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, cast

from sqlalchemy import CursorResult, update

from ..extensions import db
from ..models import Invitation, Membership, Organisation, User

INVITATION_LIFETIME = timedelta(days=7)

type InvitationState = Literal["valid", "accepted", "revoked", "expired"]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_invitation(
    organisation: Organisation,
    role: str,
    created_by: User,
) -> tuple[Invitation, str]:
    """The new invitation and its token, which isn't stored anywhere."""
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        organisation_id=organisation.id,
        token_hash=hash_token(token),
        role=role,
        created_by_id=created_by.id,
        expires_at=datetime.now(UTC) + INVITATION_LIFETIME,
    )
    db.session.add(invitation)
    db.session.commit()

    return invitation, token


def find_invitation(token: str) -> Invitation | None:
    return Invitation.query.filter_by(token_hash=hash_token(token)).first()


def invitation_state(invitation: Invitation) -> InvitationState:
    if invitation.accepted_at is not None:
        return "accepted"
    if invitation.revoked_at is not None:
        return "revoked"

    expires_at = invitation.expires_at
    # SQLite gives back naive datetimes; they were stored as UTC.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    return "expired" if expires_at <= datetime.now(UTC) else "valid"


def accept_invitation(invitation: Invitation, user: User) -> Membership | None:
    """Make the user a member with the invitation's role and use it up,
    committing both together with whatever else is pending (a new
    account). None, and everything pending rolled back, if the invitation
    is no longer valid: used by a parallel request meanwhile. The caller
    checks that the user isn't a member yet."""
    now = datetime.now(UTC)
    db.session.flush()  # a new account gets its id

    # Only if still valid, in one UPDATE: two requests can't both use it.
    used = db.session.execute(
        update(Invitation)
        .where(
            Invitation.id == invitation.id,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
            Invitation.expires_at > now,
        )
        .values(accepted_by_id=user.id, accepted_at=now),
        execution_options={"synchronize_session": False},
    )
    if cast(CursorResult[Any], used).rowcount != 1:
        db.session.rollback()
        return None

    membership = Membership(
        user_id=user.id,
        organisation_id=invitation.organisation_id,
        role=invitation.role,
    )
    db.session.add(membership)
    db.session.commit()
    db.session.refresh(invitation)

    return membership
