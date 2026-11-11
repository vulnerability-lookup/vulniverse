"""GCVE-BCP-05 extensions: the ``extensions`` object of every ``x_gcve`` entry.

The extension schemas are registered in ``schemas/extensions/gcve/``. They
are added to the authoring schema of profiles with the ``gcve-extensions``
augmenter, and bundled once for the frontend's read-only preview.
"""

import copy
from pathlib import Path
from typing import Any

from .errors import GenerationError
from .files import load_json_object
from .jsontypes import JsonObject, require_dict, require_str

# Relative to the project root.
FRONTEND_BUNDLE = Path("frontend/src/generated/gcve/extension-schemas.json")

DEFAULT_EXTENSIONS_SCHEMA: JsonObject = {
    "type": "object",
    "title": "GCVE extensions",
    "properties": {},
    "additionalProperties": True,
}


def load_extension_schemas(schemas_root: Path) -> dict[str, JsonObject]:
    """``{extension id: schema}`` from ``extensions/gcve/registry.json``."""
    registry = load_json_object(schemas_root / "extensions" / "gcve" / "registry.json")
    result: dict[str, JsonObject] = {}

    for extension_id, config in registry.items():
        config = require_dict(
            config, f"GCVE extension configuration {extension_id}", GenerationError
        )
        path = require_str(config.get("schema"), f"{extension_id} schema path", GenerationError)
        schema = load_json_object(schemas_root / path)
        # The schema is embedded below another root schema.
        schema.pop("$id", None)
        schema.pop("$schema", None)
        result[extension_id] = schema

    return result


def add_extension_schemas(node: Any, extension_schemas: dict[str, JsonObject]) -> None:
    """Declare every registered extension under each ``x_gcve`` entry, in place."""
    if isinstance(node, list):
        for item in node:
            add_extension_schemas(item, extension_schemas)
        return

    if not isinstance(node, dict):
        return

    entry = _x_gcve_entry_schema(node)

    if entry is not None:
        item_properties = entry.setdefault("properties", {})

        if isinstance(item_properties, dict):
            extensions = require_dict(
                item_properties.setdefault("extensions", copy.deepcopy(DEFAULT_EXTENSIONS_SCHEMA)),
                "GCVE extensions schema",
                GenerationError,
            )
            properties = require_dict(
                extensions.setdefault("properties", {}),
                "GCVE extension properties",
                GenerationError,
            )
            for extension_id, schema in extension_schemas.items():
                properties[extension_id] = copy.deepcopy(schema)

            # Unknown future extensions must survive.
            extensions["additionalProperties"] = True

    for child in node.values():
        add_extension_schemas(child, extension_schemas)


def _x_gcve_entry_schema(node: JsonObject) -> JsonObject | None:
    """The item schema of ``node.properties.x_gcve``, if it has one."""
    properties = node.get("properties")
    x_gcve = properties.get("x_gcve") if isinstance(properties, dict) else None
    items = x_gcve.get("items") if isinstance(x_gcve, dict) else None
    return items if isinstance(items, dict) else None


def augment(authoring_schema: JsonObject, schemas_root: Path, _profile: JsonObject) -> None:
    """The ``gcve-extensions`` editor augmenter."""
    add_extension_schemas(authoring_schema, load_extension_schemas(schemas_root))
