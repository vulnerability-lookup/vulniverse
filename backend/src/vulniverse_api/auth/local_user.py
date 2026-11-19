from __future__ import annotations

import secrets

from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import Membership, Organisation, User

LOCAL_USER_EMAIL = "local@vulniverse.invalid"
LOCAL_ORGANISATION_SLUG = "local"


def get_local_user() -> User | None:
    """Return the internal user for local deployments."""

    return User.query.filter_by(
        email=LOCAL_USER_EMAIL,
    ).first()


def create_local_user() -> User:
    """Create the local user if it does not exist, and make sure it
    belongs to an organisation (records always do)."""

    user = get_local_user()

    if user is not None:
        if not user.is_active or user.is_admin:
            raise RuntimeError("The local user has an invalid configuration.")

        ensure_local_organisation(user)
        return user

    user = User(
        email=LOCAL_USER_EMAIL,
        password_hash=generate_password_hash(secrets.token_urlsafe(48)),
        is_admin=False,
        is_active=True,
    )

    db.session.add(user)
    db.session.commit()
    ensure_local_organisation(user)

    return user


def ensure_local_organisation(user: User) -> None:
    """Local mode has one organisation, "Local workspace". An installation
    upgraded from before organisations already has the local user in the
    migration's default organisation, which is kept."""

    if Membership.query.filter_by(user_id=user.id).first() is not None:
        return

    organisation = Organisation.query.filter_by(
        slug=LOCAL_ORGANISATION_SLUG,
    ).first()

    if organisation is None:
        organisation = Organisation(
            name="Local workspace",
            slug=LOCAL_ORGANISATION_SLUG,
        )
        db.session.add(organisation)

    db.session.add(
        Membership(user=user, organisation=organisation, role="admin"),
    )
    db.session.commit()
