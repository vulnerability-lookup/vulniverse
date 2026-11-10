"""enforce identifier uniqueness case-insensitively

The existing unique constraint on vulnerability_record.identifier is
case-sensitive, while the app treats GCVE-… and gcve-… as the same
record. An index on lower(identifier) makes the database agree.
Runs after d4e2b7c9a1f0, which uppercased existing CVE/GCVE prefixes;
remaining case-only duplicates, if any, make this fail rather than be
merged silently.

Revision ID: e7a3c1d5b9f2
Revises: d4e2b7c9a1f0
Create Date: 2026-11-10 11:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e7a3c1d5b9f2'
down_revision = 'd4e2b7c9a1f0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        'uq_vulnerability_record_identifier_lower',
        'vulnerability_record',
        [sa.text('lower(identifier)')],
        unique=True,
    )


def downgrade():
    op.drop_index(
        'uq_vulnerability_record_identifier_lower',
        table_name='vulnerability_record',
    )
