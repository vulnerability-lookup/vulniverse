"""add invitations: single-use links to join an organisation

Revision ID: d12e2dd9f16d
Revises: 1b069a491b68
Create Date: 2026-11-17 16:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d12e2dd9f16d"
down_revision = "1b069a491b68"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "invitation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_by_id", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisation.id"],
            name="fk_invitation_organisation_id_organisation",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user.id"],
            name="fk_invitation_created_by_id_user",
        ),
        sa.ForeignKeyConstraint(
            ["accepted_by_id"],
            ["user.id"],
            name="fk_invitation_accepted_by_id_user",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_invitation_token_hash"),
    )
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_invitation_organisation_id"),
            ["organisation_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("invitation", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_invitation_organisation_id"))

    op.drop_table("invitation")
