from __future__ import annotations

import click
from flask import Flask

from .extensions import db
from .models import Template, User, VulnerabilityRecord


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

    @app.cli.command("backfill-record-owner")
    @click.argument("email")
    def backfill_record_owner(email: str) -> None:
        """flask --app vulniverse_api backfill-record-owner <email> —
        one-time cleanup for records/templates created before
        created_by_id existed (or via a direct API call): assigns them
        all to the given user, so draft-visibility (owner-only) has no
        ownerless edge case to special-case going forward. Every
        record/template created through the app already gets a real
        owner at creation time; this is purely a historical backfill.
        """
        user = User.query.filter_by(email=email.strip().lower()).first()

        if user is None:
            click.echo(f"No user found with email {email!r}.")
            return

        updated_records = VulnerabilityRecord.query.filter_by(
            created_by_id=None,
        ).update({"created_by_id": user.id})

        updated_templates = Template.query.filter_by(
            created_by_id=None,
        ).update({"created_by_id": user.id})

        db.session.commit()

        click.echo(
            f"Assigned {updated_records} record(s) and "
            f"{updated_templates} template(s) to {user.email}.",
        )
