from __future__ import annotations

import secrets

from werkzeug.security import generate_password_hash

from ..extensions import db
from ..models import User

LOCAL_USER_EMAIL = "local@vulniverse.invalid"


def get_local_user() -> User | None:
    """Return the internal user for local deployments."""

    return User.query.filter_by(
        email=LOCAL_USER_EMAIL,
    ).first()


def create_local_user() -> User:
    """Create the local user if it does not exist."""

    user = get_local_user()

    if user is not None:
        if not user.is_active or user.is_admin:
            raise RuntimeError(
                "The local user has an invalid configuration."
            )

        return user

    user = User(
        email=LOCAL_USER_EMAIL,
        password_hash=generate_password_hash(
            secrets.token_urlsafe(48)
        ),
        is_admin=False,
        is_active=True,
    )

    db.session.add(user)
    db.session.commit()

    return user
