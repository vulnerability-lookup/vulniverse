"""add two-factor authentication (TOTP) to users

Revision ID: a4c7e2b91d35
Revises: d12e2dd9f16d
Create Date: 2026-11-17 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a4c7e2b91d35"
down_revision = "d12e2dd9f16d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(
            sa.Column("two_factor_secret_encrypted", sa.String(length=256))
        )
        batch_op.add_column(sa.Column("two_factor_last_step", sa.Integer()))
        batch_op.add_column(
            sa.Column(
                "two_factor_failures",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column("two_factor_failed_at", sa.DateTime(timezone=True))
        )


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("two_factor_failed_at")
        batch_op.drop_column("two_factor_failures")
        batch_op.drop_column("two_factor_last_step")
        batch_op.drop_column("two_factor_secret_encrypted")
