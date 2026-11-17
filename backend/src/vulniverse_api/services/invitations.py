"""Invitation links: single use, valid for INVITATION_LIFETIME, revocable.

The link carries a random token; the database keeps only its SHA-256, so
a copy of the database can't be used to join an organisation.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal

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


def accept_invitation(invitation: Invitation, user: User) -> Membership:
    """Make the user a member with the invitation's role and use it up.
    The caller checks that it's valid and the user not yet a member."""
    membership = Membership(
        user_id=user.id,
        organisation_id=invitation.organisation_id,
        role=invitation.role,
    )
    invitation.accepted_by_id = user.id
    invitation.accepted_at = datetime.now(UTC)
    db.session.add(membership)
    db.session.commit()

    return membership
