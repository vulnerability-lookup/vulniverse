from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask

from .extensions import csrf, db, login_manager, migrate


def create_app(
    test_config: dict[str, Any] | None = None,
) -> Flask:
    # A no-op if no .env file exists (e.g. production, where the real
    # environment is expected to already carry these) — see
    # docs/setup/production.md.
    load_dotenv()

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    database_path = instance_path / "vulniverse.sqlite"

    secret_key = os.environ.get("SECRET_KEY")

    if not secret_key and test_config is None:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. Copy "
            "backend/.env.example to backend/.env and fill it in "
            "(see docs/setup/production.md).",
        )

    cna_encryption_key = os.environ.get("CNA_CREDENTIAL_ENCRYPTION_KEY")

    if not cna_encryption_key and test_config is None:
        raise RuntimeError(
            "CNA_CREDENTIAL_ENCRYPTION_KEY environment variable is not "
            "set. Generate one with `python -c \"from cryptography.fernet "
            'import Fernet; print(Fernet.generate_key().decode())"` and '
            "set it in backend/.env (see docs/setup/production.md).",
        )

    app.config.from_mapping(
        SECRET_KEY=secret_key or "development-only-change-me",
        CNA_CREDENTIAL_ENCRYPTION_KEY=cna_encryption_key,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL",
            f"sqlite:///{database_path}",
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Ensure models are registered with SQLAlchemy and Alembic.
    from . import models
    from .api import api_bp
    from .cli import register_cli

    @login_manager.user_loader
    def load_user(user_id: str) -> models.User | None:
        # populate_existing=True: is_admin/is_active can change (an admin
        # action) between two requests from the same still-logged-in
        # session — without this, a stale identity-mapped User object
        # could mask a deactivation until something else evicts it.
        return db.session.get(
            models.User,
            int(user_id),
            populate_existing=True,
        )

    app.register_blueprint(
        api_bp,
        url_prefix="/api/v1",
    )

    register_cli(app)

    return app
