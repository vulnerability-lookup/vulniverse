"""cna publication: posted flag and last_sent_at; published_at only
means published

Revision ID: d9e4a1f6b7c2
Revises: c5d2e8a7f913
Create Date: 2026-11-18 16:00:00.000000

"""

from datetime import UTC, timedelta

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d9e4a1f6b7c2"
down_revision = "c5d2e8a7f913"
branch_labels = None
depends_on = None

publication = sa.table(
    "cna_publication",
    sa.column("id"),
    sa.column("status"),
    sa.column("published_at", sa.DateTime(timezone=True)),
    sa.column("rejected_at", sa.DateTime(timezone=True)),
    sa.column("posted", sa.Boolean()),
    sa.column("last_sent_at", sa.DateTime(timezone=True)),
)

# A reject without a prior publish set published_at and rejected_at at
# the same moment (published_at was the "POST sent" marker).
SAME_MOMENT = timedelta(seconds=5)


def _aware(moment):
    return moment if moment is None or moment.tzinfo else moment.replace(tzinfo=UTC)


def upgrade():
    with op.batch_alter_table("cna_publication") as batch_op:
        batch_op.add_column(
            sa.Column("posted", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(
            sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True)
        )

    connection = op.get_bind()
    rows = connection.execute(
        sa.select(
            publication.c.id,
            publication.c.status,
            publication.c.published_at,
            publication.c.rejected_at,
        ).where(publication.c.published_at.is_not(None))
    ).all()

    for row_id, status, published_at, rejected_at in rows:
        published_at, rejected_at = _aware(published_at), _aware(rejected_at)
        only_marker = (
            status == "REJECTED"
            and rejected_at is not None
            and abs(rejected_at - published_at) < SAME_MOMENT
        )
        connection.execute(
            publication.update()
            .where(publication.c.id == row_id)
            .values(
                posted=True,
                published_at=None if only_marker else published_at,
                last_sent_at=max(m for m in (published_at, rejected_at) if m),
            )
        )


def downgrade():
    # published_at was also the "POST sent" marker: restore it from posted.
    connection = op.get_bind()
    connection.execute(
        publication.update()
        .where(publication.c.posted.is_(True), publication.c.published_at.is_(None))
        .values(published_at=sa.func.coalesce(publication.c.rejected_at, sa.func.now()))
    )

    with op.batch_alter_table("cna_publication") as batch_op:
        batch_op.drop_column("last_sent_at")
        batch_op.drop_column("posted")
