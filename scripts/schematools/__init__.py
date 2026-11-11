"""Maintenance tools for Vulniverse's schemas.

Two command-line scripts use this package:

- ``scripts/update_schemas.py`` vendors the upstream schemas into
  ``schemas/upstream/`` and records them in ``schemas/manifest.json``
  (see :mod:`schematools.update` and :mod:`schematools.sources`).
- ``scripts/generate_editor_schemas.py`` turns a manifest profile into the
  editor's generated files under ``frontend/src/generated/`` (see
  :mod:`schematools.generate`).
"""
