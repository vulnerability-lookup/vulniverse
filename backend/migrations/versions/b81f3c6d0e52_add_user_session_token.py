"""add user session_token: a new one ends the account's sessions

Revision ID: b81f3c6d0e52
Revises: a4c7e2b91d35
Create Date: 2026-11-18 10:00:00.000000

"""

import secrets

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b81f3c6d0e52"
down_revision = "a4c7e2b91d35"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("session_token", sa.String(length=32)))

    # A random one per account; existing sessions (without one) end.
    user = sa.table("user", sa.column("id"), sa.column("session_token"))
    connection = op.get_bind()
    for (user_id,) in connection.execute(sa.select(user.c.id)).all():
        connection.execute(
            user.update()
            .where(user.c.id == user_id)
            .values(session_token=secrets.token_hex(16))
        )

    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column(
            "session_token", existing_type=sa.String(length=32), nullable=False
        )


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("session_token")
