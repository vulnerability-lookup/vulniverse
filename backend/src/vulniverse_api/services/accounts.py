"""Account rules: passwords, and deleting an account (by its owner or
an instance admin)."""

from __future__ import annotations

import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import (
    Invitation,
    Membership,
    Template,
    User,
    UserCnaCredential,
    VulnerabilityRecord,
)

MIN_PASSWORD_LENGTH = 8

# Checked against when the address is unknown, so a wrong address takes
# as long as a wrong password and response times don't reveal accounts.
_UNKNOWN_USER_HASH = generate_password_hash(secrets.token_urlsafe(16))


def password_matches(user: User | None, password: str) -> bool:
    if user is None:
        check_password_hash(_UNKNOWN_USER_HASH, password)
        return False

    return check_password_hash(user.password_hash, password)


def password_problem(password: object) -> str | None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        return f"A password of at least {MIN_PASSWORD_LENGTH} characters is required."

    return None


def set_password(user: User, password: str) -> None:
    user.password_hash = generate_password_hash(password)
    db.session.commit()


def generate_password() -> str:
    return secrets.token_urlsafe(12)


def deletion_problem(user: User) -> str | None:
    """Why the account can't be deleted now, or None."""
    if (
        user.is_admin
        and User.query.filter_by(is_admin=True, is_active=True).count() <= 1
    ):
        return "This is the last instance admin; make someone else an admin first."

    stranded = []
    for membership in Membership.query.filter_by(user_id=user.id, role="admin"):
        organisation_id = membership.organisation_id
        admins = Membership.query.filter_by(
            organisation_id=organisation_id, role="admin"
        ).count()
        members = Membership.query.filter_by(organisation_id=organisation_id).count()

        if admins == 1 and members > 1:
            stranded.append(membership.organisation.name)

    if stranded:
        return (
            f"This is the last admin of {', '.join(sorted(stranded))};"
            " make another member an admin first."
        )

    return None


def delete_account(user: User) -> None:
    """Delete the account and what's only its own (templates, CNA
    credentials, memberships). Records and invitations stay, without the
    link to it. The caller checks deletion_problem() first."""
    user_id = user.id

    UserCnaCredential.query.filter_by(user_id=user_id).delete()
    Template.query.filter_by(created_by_id=user_id).delete()
    Membership.query.filter_by(user_id=user_id).delete()
    VulnerabilityRecord.query.filter_by(created_by_id=user_id).update(
        {"created_by_id": None},
        synchronize_session=False,
    )
    Invitation.query.filter_by(created_by_id=user_id).update({"created_by_id": None})
    Invitation.query.filter_by(accepted_by_id=user_id).update({"accepted_by_id": None})

    db.session.delete(user)
    db.session.commit()
