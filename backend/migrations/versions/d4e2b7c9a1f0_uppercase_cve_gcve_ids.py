"""uppercase lowercased CVE and GCVE identifiers

Vulnerability-Lookup returned reserved GCVE IDs lowercased (its
internal key form), and Vulniverse stored them as-is: in the record's
identifier, x_gcve[].vulnId, cveMetadata.vulnId and the publication's
cve_id. New reservations are uppercased; this fixes existing data.
Only the cve/gcve prefix of values shaped like CVE/GCVE IDs changes;
the rest of the ID is kept, and OSV IDs such as GHSA-xxxx-xxxx-xxxx,
whose lowercase parts are canonical, are never touched.

Revision ID: d4e2b7c9a1f0
Revises: c3f1a8d2e6b4
Create Date: 2026-11-10 10:00:00.000000

"""
import re

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd4e2b7c9a1f0'
down_revision = 'c3f1a8d2e6b4'
branch_labels = None
depends_on = None

ID = re.compile(r"^(?:cve|gcve-[0-9]+)-[0-9]{4}-", re.IGNORECASE)

PREFIX = re.compile(r"^g?cve", re.IGNORECASE)

records = sa.table(
    'vulnerability_record',
    sa.column('id', sa.Integer),
    sa.column('identifier', sa.String),
    sa.column('document', sa.JSON),
)

publications = sa.table(
    'cna_publication',
    sa.column('id', sa.Integer),
    sa.column('cve_id', sa.String),
)


def canonical(value):
    """Uppercases only the cve/gcve prefix of a CVE/GCVE-shaped ID."""
    if isinstance(value, str) and ID.match(value):
        return PREFIX.sub(lambda match: match.group().upper(), value)

    return value


def uppercase_ids(document):
    """Uppercased copy of the document's ID fields, or None if unchanged."""
    if not isinstance(document, dict):
        return None

    changed = False
    metadata = document.get('cveMetadata')

    if isinstance(metadata, dict):
        for key in ('cveId', 'vulnId'):
            if canonical(metadata.get(key)) != metadata.get(key):
                metadata[key] = canonical(metadata[key])
                changed = True

    cna = (document.get('containers') or {}).get('cna')
    entries = cna.get('x_gcve') if isinstance(cna, dict) else None

    for entry in entries if isinstance(entries, list) else []:
        if isinstance(entry, dict) and canonical(entry.get('vulnId')) != entry.get('vulnId'):
            entry['vulnId'] = canonical(entry['vulnId'])
            changed = True

    return document if changed else None


def upgrade():
    bind = op.get_bind()

    for row in bind.execute(sa.select(records)).mappings().all():
        values = {}

        if canonical(row['identifier']) != row['identifier']:
            values['identifier'] = canonical(row['identifier'])

        document = uppercase_ids(row['document'])

        if document is not None:
            values['document'] = document

        if values:
            bind.execute(records.update().where(records.c.id == row['id']).values(**values))

    for row in bind.execute(sa.select(publications)).mappings().all():
        if canonical(row['cve_id']) != row['cve_id']:
            bind.execute(
                publications.update()
                .where(publications.c.id == row['id'])
                .values(cve_id=canonical(row['cve_id'])),
            )


def downgrade():
    # The original lowercase spelling isn't recorded, and IDs are
    # compared case-insensitively everywhere, so there is nothing to undo.
    pass
