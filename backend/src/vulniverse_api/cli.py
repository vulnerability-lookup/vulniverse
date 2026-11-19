from __future__ import annotations

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from .auth.identity import is_local_mode
from .auth.local_user import create_local_user
from .extensions import db
from .models import Template, User, VulnerabilityRecord
from .services import two_factor
from .services.accounts import password_problem
from .services.cpe_catalog import sync_catalog


def register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.argument("email")
    def create_admin(email: str) -> None:
        """flask --app vulniverse_api create-admin <email>: create an
        instance admin, asking for the password. Creating the account
        here, rather than promoting one someone registered, matters:
        addresses aren't verified, so with open registration anyone may
        have registered the address first."""
        email = email.strip().lower()
        user = User.query.filter_by(email=email).first()

        if user is not None:
            if user.is_admin:
                click.echo(f"{user.email} is already an admin.")
                return
            # Registered by whoever typed the address; nothing proves it's
            # the person meant.
            click.confirm(
                f"{user.email} already has an account, registered"
                f" {user.created_at:%Y-%m-%d %H:%M} UTC through the web"
                " (addresses aren't verified). Make it an admin?",
                abort=True,
            )
            user.is_admin = True
            db.session.commit()
            click.echo(f"{user.email} is now an admin.")
            return

        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        problem = password_problem(password)
        if problem:
            raise click.ClickException(problem)

        db.session.add(
            User(
                email=email,
                password_hash=generate_password_hash(password),
                is_admin=True,
            )
        )
        db.session.commit()
        click.echo(f"Created the admin account {email}.")

    @app.cli.command("reset-two-factor")
    @click.argument("email")
    def reset_two_factor(email: str) -> None:
        """Forget a user's 2FA secret, e.g. when the only admin lost
        their device; they set it up again at their next login."""
        user = User.query.filter_by(email=email.strip().lower()).first()

        if user is None:
            click.echo(f"No user found with email {email!r}.")
            return

        two_factor.reset(user)
        click.echo(f"Two-factor authentication reset for {user.email}.")

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

    @app.cli.command("init-local-user")
    def init_local_user() -> None:
        """Initialize the internal user for local mode."""

        if not is_local_mode():
            raise click.ClickException("Local user initialization requires local mode.")

        user = create_local_user()

        click.echo(f"Local user initialized: {user.email}")

    @app.cli.group("cpe")
    def cpe_group() -> None:
        """Manage the local CPE vendor/product reference catalog."""

    @cpe_group.command("sync")
    def sync_cpe() -> None:
        """flask --app vulniverse_api cpe sync — refreshes the local
        vendor/product catalog from cpe.gcve.eu's export endpoints.
        A failed sync leaves the existing catalog untouched.
        """
        result = sync_catalog()

        click.echo(
            "CPE catalog synchronized: "
            f"{result['vendors']} vendors, {result['products']} products.",
        )
