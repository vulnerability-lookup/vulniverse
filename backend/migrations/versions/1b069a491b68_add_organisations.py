"""add organisations; records belong to one, IDs unique per organisation

Records move from belonging to a single user to belonging to an
organisation, whose members share them (drafts included). Existing data
goes into one "Default organisation": every user becomes a member (an
instance admin as its admin), every record belongs to it. Nothing
changes for anyone until organisations are set up and users moved.

Record IDs become unique per organisation instead of instance-wide;
the old global uniqueness guarantees no duplicates inside the default
organisation. A downgrade with the same ID in two organisations fails
on the restored global index, on purpose, rather than merging records.

Records also get a version, counting saves.

Revision ID: 1b069a491b68
Revises: e7a3c1d5b9f2
Create Date: 2026-11-17 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1b069a491b68"
down_revision = "e7a3c1d5b9f2"
branch_labels = None
depends_on = None

DEFAULT_ORGANISATION = "(SELECT id FROM organisation WHERE slug = 'default')"


def upgrade():
    op.create_table(
        "organisation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organisation_slug"),
    )

    op.create_table(
        "membership",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_membership_user_id_user"
        ),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisation.id"],
            name="fk_membership_organisation_id_organisation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "organisation_id", name="uq_membership_user_organisation"
        ),
    )
    with op.batch_alter_table("membership", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_membership_user_id"), ["user_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_membership_organisation_id"),
            ["organisation_id"],
            unique=False,
        )

    # Everyone and everything into one organisation to start with.
    op.execute(
        "INSERT INTO organisation (name, slug) VALUES ('Default organisation', 'default')"
    )
    op.execute(
        "INSERT INTO membership (user_id, organisation_id, role)"
        f" SELECT id, {DEFAULT_ORGANISATION},"
        " CASE WHEN is_admin THEN 'admin' ELSE 'editor' END"
        ' FROM "user"'
    )

    # An expression index doesn't survive SQLite's batch table rebuild,
    # so it goes before it; its per-organisation successor comes after.
    op.drop_index(
        "uq_vulnerability_record_identifier_lower",
        table_name="vulnerability_record",
    )

    with op.batch_alter_table("vulnerability_record", schema=None) as batch_op:
        batch_op.add_column(sa.Column("organisation_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("version", sa.Integer(), server_default="1", nullable=False)
        )

    op.execute(
        f"UPDATE vulnerability_record SET organisation_id = {DEFAULT_ORGANISATION}"
    )

    with op.batch_alter_table("vulnerability_record", schema=None) as batch_op:
        batch_op.alter_column(
            "organisation_id", existing_type=sa.Integer(), nullable=False
        )
        batch_op.create_foreign_key(
            "fk_vulnerability_record_organisation_id_organisation",
            "organisation",
            ["organisation_id"],
            ["id"],
        )
        batch_op.create_index(
            batch_op.f("ix_vulnerability_record_organisation_id"),
            ["organisation_id"],
            unique=False,
        )
        # Still an index for lookups, no longer a uniqueness rule.
        batch_op.drop_index(batch_op.f("ix_vulnerability_record_identifier"))
        batch_op.create_index(
            batch_op.f("ix_vulnerability_record_identifier"),
            ["identifier"],
            unique=False,
        )

    op.create_index(
        "uq_vulnerability_record_organisation_identifier_lower",
        "vulnerability_record",
        ["organisation_id", sa.text("lower(identifier)")],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "uq_vulnerability_record_organisation_identifier_lower",
        table_name="vulnerability_record",
    )

    with op.batch_alter_table("vulnerability_record", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_vulnerability_record_identifier"))
        batch_op.create_index(
            batch_op.f("ix_vulnerability_record_identifier"),
            ["identifier"],
            unique=True,
        )
        batch_op.drop_index(batch_op.f("ix_vulnerability_record_organisation_id"))
        batch_op.drop_constraint(
            "fk_vulnerability_record_organisation_id_organisation", type_="foreignkey"
        )
        batch_op.drop_column("version")
        batch_op.drop_column("organisation_id")

    op.create_index(
        "uq_vulnerability_record_identifier_lower",
        "vulnerability_record",
        [sa.text("lower(identifier)")],
        unique=True,
    )

    with op.batch_alter_table("membership", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_membership_organisation_id"))
        batch_op.drop_index(batch_op.f("ix_membership_user_id"))

    op.drop_table("membership")
    op.drop_table("organisation")
