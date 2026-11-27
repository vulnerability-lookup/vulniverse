"""patch2vuln candidates: several commits for one vulnerability

Revision ID: a7c3e9f1b2d4
Revises: f2b8d4a6c1e3
Create Date: 2026-11-27 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c3e9f1b2d4"
down_revision = "f2b8d4a6c1e3"
branch_labels = None
depends_on = None

candidate = sa.table(
    "patch2vuln_candidate",
    sa.column("id", sa.Integer()),
    sa.column("commit_url", sa.String()),
    sa.column("commit_urls", sa.JSON()),
)


def upgrade():
    with op.batch_alter_table("patch2vuln_candidate", schema=None) as batch_op:
        batch_op.add_column(sa.Column("commit_urls", sa.JSON(), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.select(candidate.c.id, candidate.c.commit_url)).all()
    for row_id, url in rows:
        connection.execute(
            candidate.update()
            .where(candidate.c.id == row_id)
            .values(commit_urls=[url])
        )

    with op.batch_alter_table("patch2vuln_candidate", schema=None) as batch_op:
        batch_op.alter_column("commit_urls", existing_type=sa.JSON(), nullable=False)
        batch_op.drop_column("commit_url")


def downgrade():
    with op.batch_alter_table("patch2vuln_candidate", schema=None) as batch_op:
        batch_op.add_column(sa.Column("commit_url", sa.String(length=512), nullable=True))

    # Only the first commit of a group survives the downgrade.
    connection = op.get_bind()
    rows = connection.execute(sa.select(candidate.c.id, candidate.c.commit_urls)).all()
    for row_id, urls in rows:
        connection.execute(
            candidate.update()
            .where(candidate.c.id == row_id)
            .values(commit_url=urls[0])
        )

    with op.batch_alter_table("patch2vuln_candidate", schema=None) as batch_op:
        batch_op.alter_column(
            "commit_url", existing_type=sa.String(length=512), nullable=False
        )
        batch_op.drop_column("commit_urls")
