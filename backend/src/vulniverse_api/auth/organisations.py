"""Who may see and change which records: membership in the organisation
owning them.

- Members of an organisation read and change all its records, drafts
  included; that's how colleagues share work.
- Published records are readable by every logged-in user.
- Instance admins (User.is_admin) may read and change everything.

The current organisation (where new records go, which the record list
shows) is kept in the session; without a valid choice there, it's the
user's first membership.
"""

from __future__ import annotations

from flask import session
from flask_login import current_user

from ..models import Membership, Organisation, User, VulnerabilityRecord

SESSION_KEY = "organisation_id"


def memberships(user: User) -> list[Membership]:
    """The user's memberships, oldest first."""
    return Membership.query.filter_by(user_id=user.id).order_by(Membership.id).all()


def is_member(user: User, organisation_id: int) -> bool:
    return (
        Membership.query.filter_by(
            user_id=user.id,
            organisation_id=organisation_id,
        ).first()
        is not None
    )


def current_organisation() -> Organisation | None:
    """The organisation the current user works in, or None without any."""
    if not current_user.is_authenticated:
        return None

    joined = memberships(current_user)
    chosen = session.get(SESSION_KEY)

    for membership in joined:
        if membership.organisation_id == chosen:
            return membership.organisation

    return joined[0].organisation if joined else None


def can_read_record(record: VulnerabilityRecord) -> bool:
    return (
        not record.is_draft
        or current_user.is_admin
        or is_member(current_user, record.organisation_id)
    )


def can_modify_record(record: VulnerabilityRecord) -> bool:
    return current_user.is_admin or is_member(current_user, record.organisation_id)
