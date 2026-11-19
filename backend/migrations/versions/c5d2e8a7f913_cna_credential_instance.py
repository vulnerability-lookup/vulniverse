"""cna credentials name an operator-configured instance, not a URL

Revision ID: c5d2e8a7f913
Revises: b81f3c6d0e52
Create Date: 2026-11-18 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from vulniverse_api.app_config import load_app_config

# revision identifiers, used by Alembic.
revision = "c5d2e8a7f913"
down_revision = "b81f3c6d0e52"
branch_labels = None
depends_on = None

credential = sa.table(
    "user_cna_credential",
    sa.column("id"),
    sa.column("target"),
    sa.column("cve_url"),
    sa.column("instance"),
)


def _instances() -> dict[str, list[dict[str, str]]]:
    return load_app_config()["publish_instances"]


def upgrade():
    with op.batch_alter_table("user_cna_credential") as batch_op:
        batch_op.add_column(sa.Column("instance", sa.String(length=64)))

    # A stored URL that's one of the configured instances keeps working;
    # any other gets "" and its owner picks an instance (with the key).
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(credential.c.id, credential.c.target, credential.c.cve_url)
    ).all()
    for row_id, target, url in rows:
        match = next(
            (
                entry["id"]
                for entry in _instances().get(target, [])
                if entry["api_url"].rstrip("/") == (url or "").rstrip("/")
            ),
            "",
        )
        connection.execute(
            credential.update().where(credential.c.id == row_id).values(instance=match)
        )

    with op.batch_alter_table("user_cna_credential") as batch_op:
        batch_op.alter_column(
            "instance", existing_type=sa.String(length=64), nullable=False
        )
        batch_op.drop_column("cve_url")


def downgrade():
    with op.batch_alter_table("user_cna_credential") as batch_op:
        batch_op.add_column(sa.Column("cve_url", sa.String(length=512)))

    connection = op.get_bind()
    rows = connection.execute(
        sa.select(credential.c.id, credential.c.target, credential.c.instance)
    ).all()
    for row_id, target, instance in rows:
        url = next(
            (
                entry["api_url"]
                for entry in _instances().get(target, [])
                if entry["id"] == instance
            ),
            "",
        )
        connection.execute(
            credential.update().where(credential.c.id == row_id).values(cve_url=url)
        )

    with op.batch_alter_table("user_cna_credential") as batch_op:
        batch_op.alter_column(
            "cve_url", existing_type=sa.String(length=512), nullable=False
        )
        batch_op.drop_column("instance")
