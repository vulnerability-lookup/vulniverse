"""The organisations migration (1b069a491b68) on a database with data in
the shape it had before: every user and record lands in the default
organisation, IDs become unique per organisation, and a downgrade
restores the old rules."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask import Flask
from flask_migrate import downgrade, upgrade
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vulniverse_api import app_config, create_app
from vulniverse_api.extensions import db

MIGRATIONS = str(Path(__file__).resolve().parent.parent / "migrations")
BEFORE = "e7a3c1d5b9f2"
THIS = "1b069a491b68"


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Flask]:
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(
        app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample"
    )
    app_config.load_app_config.cache_clear()

    application = create_app(
        {
            "TESTING": True,
            # A file, not :memory: — the migrations open their own connections.
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'vulniverse.sqlite'}",
            "VULNIVERSE_MODE": "multiuser",
        }
    )

    with application.app_context():
        upgrade(directory=MIGRATIONS, revision=BEFORE)
        run(
            'INSERT INTO "user" (id, email, password_hash, is_admin, is_active)'
            " VALUES (1, 'admin@example.com', 'x', 1, 1),"
            " (2, 'editor@example.com', 'x', 0, 1)"
        )
        run(
            "INSERT INTO vulnerability_record (id, identifier, profile, document, is_draft, created_by_id)"
            " VALUES (1, 'CVE-2026-0001', 'cve-5.2.0', '{}', 0, 1),"
            " (2, NULL, 'cve-5.2.0', '{}', 1, 2)"
        )
        yield application
        db.session.remove()

    app_config.load_app_config.cache_clear()


def run(sql: str):
    result = db.session.execute(text(sql))
    db.session.commit()
    return result


def test_existing_users_and_records_move_into_the_default_organisation(
    app: Flask,
) -> None:
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=THIS)

        organisations = run("SELECT id, name, slug FROM organisation").all()
        assert [(name, slug) for _, name, slug in organisations] == [
            ("Default organisation", "default")
        ]
        default = organisations[0][0]

        assert run(
            "SELECT user_id, organisation_id, role FROM membership ORDER BY user_id"
        ).all() == [
            (1, default, "admin"),
            (2, default, "editor"),
        ]
        assert run(
            "SELECT id, organisation_id, version FROM vulnerability_record ORDER BY id"
        ).all() == [
            (1, default, 1),
            (2, default, 1),
        ]


def test_ids_become_unique_per_organisation(app: Flask) -> None:
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=THIS)
        run("INSERT INTO organisation (id, name, slug) VALUES (2, 'Other', 'other')")

        # The same ID in another organisation is fine…
        run(
            "INSERT INTO vulnerability_record (identifier, profile, document, is_draft, organisation_id)"
            " VALUES ('CVE-2026-0001', 'cve-5.2.0', '{}', 1, 2)"
        )

        # …a second one in the same organisation is not, in any case.
        with pytest.raises(IntegrityError):
            run(
                "INSERT INTO vulnerability_record (identifier, profile, document, is_draft, organisation_id)"
                f" VALUES ('cve-2026-0001', 'cve-5.2.0', '{{}}', 1, {default_id()})"
            )
        db.session.rollback()


def test_downgrade_restores_the_old_tables_and_global_uniqueness(app: Flask) -> None:
    with app.app_context():
        upgrade(directory=MIGRATIONS, revision=THIS)
        downgrade(directory=MIGRATIONS, revision=BEFORE)

        tables = {
            name
            for (name,) in run("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        columns = {row[1] for row in run("PRAGMA table_info(vulnerability_record)")}

        assert not {"organisation", "membership"} & tables
        assert not {"organisation_id", "version"} & columns
        assert run("SELECT count(*) FROM vulnerability_record").scalar() == 2

        with pytest.raises(IntegrityError):
            run(
                "INSERT INTO vulnerability_record (identifier, profile, document, is_draft)"
                " VALUES ('cve-2026-0001', 'cve-5.2.0', '{}', 1)"
            )
        db.session.rollback()


def default_id() -> int:
    return run("SELECT id FROM organisation WHERE slug = 'default'").scalar()
