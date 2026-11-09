"""address records by id, not by vulnerability identifier

Revision ID: c3f1a8d2e6b4
Revises: e658c4b83c4b
Create Date: 2026-11-09 10:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c3f1a8d2e6b4'
down_revision = 'e658c4b83c4b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('cna_publication', schema=None) as batch_op:
        batch_op.add_column(sa.Column('record_id', sa.Integer(), nullable=True))

    # Same case-insensitive match the old string lookups used.
    op.execute(
        "UPDATE cna_publication SET record_id = ("
        " SELECT vulnerability_record.id FROM vulnerability_record"
        " WHERE lower(vulnerability_record.identifier)"
        " = lower(cna_publication.record_identifier))"
    )
    # Rows whose record no longer exists were unreachable already.
    op.execute("DELETE FROM cna_publication WHERE record_id IS NULL")

    with op.batch_alter_table('cna_publication', schema=None) as batch_op:
        batch_op.drop_constraint('uq_cna_publication_record_target', type_='unique')
        batch_op.drop_index(batch_op.f('ix_cna_publication_record_identifier'))
        batch_op.drop_column('record_identifier')
        batch_op.alter_column('record_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_cna_publication_record_id', 'vulnerability_record', ['record_id'], ['id'],
        )
        batch_op.create_index(batch_op.f('ix_cna_publication_record_id'), ['record_id'], unique=False)
        batch_op.create_unique_constraint(
            'uq_cna_publication_record_target', ['record_id', 'target'],
        )

    with op.batch_alter_table('vulnerability_record', schema=None) as batch_op:
        batch_op.alter_column('identifier', existing_type=sa.String(length=128), nullable=True)

    # Drafts without a real vulnerability identifier no longer need one.
    op.execute(
        "UPDATE vulnerability_record SET identifier = NULL"
        " WHERE identifier LIKE 'draft-%' OR identifier LIKE 'vulniverse-draft-%'"
    )


def downgrade():
    op.execute(
        "UPDATE vulnerability_record SET identifier = 'draft-' || id"
        " WHERE identifier IS NULL"
    )

    with op.batch_alter_table('vulnerability_record', schema=None) as batch_op:
        batch_op.alter_column('identifier', existing_type=sa.String(length=128), nullable=False)

    with op.batch_alter_table('cna_publication', schema=None) as batch_op:
        batch_op.add_column(sa.Column('record_identifier', sa.String(length=128), nullable=True))

    op.execute(
        "UPDATE cna_publication SET record_identifier = ("
        " SELECT vulnerability_record.identifier FROM vulnerability_record"
        " WHERE vulnerability_record.id = cna_publication.record_id)"
    )

    with op.batch_alter_table('cna_publication', schema=None) as batch_op:
        batch_op.drop_constraint('uq_cna_publication_record_target', type_='unique')
        batch_op.drop_index(batch_op.f('ix_cna_publication_record_id'))
        batch_op.drop_constraint('fk_cna_publication_record_id', type_='foreignkey')
        batch_op.drop_column('record_id')
        batch_op.alter_column('record_identifier', existing_type=sa.String(length=128), nullable=False)
        batch_op.create_index(batch_op.f('ix_cna_publication_record_identifier'), ['record_identifier'], unique=False)
        batch_op.create_unique_constraint(
            'uq_cna_publication_record_target', ['record_identifier', 'target'],
        )
