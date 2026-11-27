"""add patch2vuln batches: commits analysed together, reviewed one by one

Revision ID: f2b8d4a6c1e3
Revises: d9e4a1f6b7c2
Create Date: 2026-11-27 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2b8d4a6c1e3"
down_revision = "d9e4a1f6b7c2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "patch2vuln_batch",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("profile", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisation.id"],
            name="fk_patch2vuln_batch_organisation_id_organisation",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["user.id"],
            name="fk_patch2vuln_batch_created_by_id_user",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("patch2vuln_batch", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_patch2vuln_batch_organisation_id"),
            ["organisation_id"],
            unique=False,
        )

    op.create_table(
        "patch2vuln_candidate",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("commit_url", sa.String(length=512), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("dismissed", sa.Boolean(), nullable=False),
        sa.Column("record_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["batch_id"],
            ["patch2vuln_batch.id"],
            name="fk_patch2vuln_candidate_batch_id_patch2vuln_batch",
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["vulnerability_record.id"],
            name="fk_patch2vuln_candidate_record_id_vulnerability_record",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id", name="uq_patch2vuln_candidate_record_id"),
    )
    with op.batch_alter_table("patch2vuln_candidate", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_patch2vuln_candidate_batch_id"),
            ["batch_id"],
            unique=False,
        )


def downgrade():
    op.drop_table("patch2vuln_candidate")
    op.drop_table("patch2vuln_batch")
