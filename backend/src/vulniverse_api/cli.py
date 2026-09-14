from __future__ import annotations

import click
from flask import Flask

from .extensions import db
from .models import User


def register_cli(app: Flask) -> None:
    """flask --app vulniverse_api create-admin <email> — the one-time
    manual step to bootstrap the first admin, since registration is
    open/self-service and there's otherwise no "first admin" moment.
    The user must already have registered a normal account first.
    """

    @app.cli.command("create-admin")
    @click.argument("email")
    def create_admin(email: str) -> None:
        user = User.query.filter_by(email=email.strip().lower()).first()

        if user is None:
            click.echo(
                f"No user found with email {email!r}. "
                "They need to register an account first.",
            )
            return

        if user.is_admin:
            click.echo(f"{user.email} is already an admin.")
            return

        user.is_admin = True
        db.session.commit()

        click.echo(f"{user.email} is now an admin.")
