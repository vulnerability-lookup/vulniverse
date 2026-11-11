"""The authoring schema: what the editor validates and renders a record with.

Built from the profile's upstream schema in four steps:

1. pick the editor's variant (CVE's root ``oneOf`` branch "Published") or,
   without one, take the whole schema; inline every ``$ref`` either way,
2. strip nested ``$id`` values,
3. merge the profile's ``schemaOverlay`` on top,
4. run the profile's ``editor.augmenters``.
"""

import copy
from collections.abc import Callable
from pathlib import Path

from . import gcve
from .errors import GenerationError
from .files import load_json_object
from .jsontypes import JsonObject, as_dict, require_dict, require_str, str_list
from .refs import dereference, drop_unused_definitions, strip_nested_ids

# Ajv only speaks draft-07. Inlined $refs leave plain draft-07 keywords.
# shortcut: 2020-12-only keywords (prefixItems, unevaluated*) would be
# ignored by the editor; switch editorAjv to Ajv2020 if a profile needs them.
EDITOR_DIALECT = "http://json-schema.org/draft-07/schema#"

# (authoring schema, schemas/ folder, profile), changing the schema in place.
EditorAugmenter = Callable[[JsonObject, Path, JsonObject], None]

AUGMENTERS: dict[str, EditorAugmenter] = {
    "gcve-extensions": gcve.augment,
}


def select_variant(official_schema: JsonObject, title: str) -> JsonObject:
    """The root ``oneOf`` branch titled ``title``, dereferenced."""
    variants = official_schema.get("oneOf")

    if not isinstance(variants, list):
        raise GenerationError("Official schema has no root oneOf variants.")

    for candidate in variants:
        if isinstance(candidate, dict) and candidate.get("title") == title:
            return require_dict(
                dereference(candidate, official_schema),
                "Expanded schema variant",
                GenerationError,
            )

    raise GenerationError(f"Schema variant was not found: {title}")


def expand_whole_schema(
    official_schema: JsonObject, schemas_root: Path, profile: JsonObject
) -> JsonObject:
    """The whole schema with references inlined, including ``schemaResources``."""
    resources = {
        url: load_json_object(schemas_root / path)
        for url, path in as_dict(profile.get("schemaResources")).items()
    }
    expanded = require_dict(
        dereference(official_schema, official_schema, resources=resources),
        "Expanded root schema",
        GenerationError,
    )
    drop_unused_definitions(expanded)
    return expanded


def deep_merge(base: JsonObject, overlay: JsonObject) -> JsonObject:
    """``base`` with ``overlay`` merged in; nested objects merge, not replace."""
    merged = copy.deepcopy(base)

    for key, value in overlay.items():
        existing = merged.get(key)

        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge(existing, value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


def apply_overlay(schema: JsonObject, schemas_root: Path, profile: JsonObject) -> JsonObject:
    overlay_config = profile.get("schemaOverlay")

    if overlay_config is None:
        return schema

    overlay_config = require_dict(overlay_config, "schemaOverlay", GenerationError)
    path = require_str(overlay_config.get("path"), "schemaOverlay.path", GenerationError)

    # Backend validation may apply the overlay to each root oneOf branch.
    # The authoring schema has already selected or expanded its root, so
    # here the overlay belongs directly on it.
    return deep_merge(schema, load_json_object(schemas_root / path))


def augmenter_ids(editor_config: JsonObject) -> list[str]:
    return str_list(editor_config.get("augmenters", []), "editor.augmenters", GenerationError)


def run_augmenters(
    schema: JsonObject, schemas_root: Path, profile: JsonObject, editor_config: JsonObject
) -> None:
    for augmenter_id in augmenter_ids(editor_config):
        augmenter = AUGMENTERS.get(augmenter_id)

        if augmenter is None:
            raise GenerationError(f"Unknown editor augmenter: {augmenter_id}")

        augmenter(schema, schemas_root, profile)


def create_authoring_schema(profile_id: str, profile: JsonObject, schemas_root: Path) -> JsonObject:
    """The complete authoring schema of one profile."""
    editor_config = require_dict(
        profile.get("editor"), f"{profile_id} editor configuration", GenerationError
    )
    official_schema = load_json_object(
        schemas_root
        / require_str(profile.get("baseSchema"), f"{profile_id} baseSchema", GenerationError)
    )
    variant = editor_config.get("variant")

    if variant is None:
        schema = expand_whole_schema(official_schema, schemas_root, profile)
    else:
        variant = require_str(variant, "editor.variant", GenerationError)
        schema = select_variant(official_schema, variant)

    strip_nested_ids(schema)
    schema = apply_overlay(schema, schemas_root, profile)
    run_augmenters(schema, schemas_root, profile, editor_config)

    label = profile.get("label")
    label = label if isinstance(label, str) else profile_id
    variant_suffix = f" {variant}" if variant else ""

    schema["$schema"] = EDITOR_DIALECT
    schema["$id"] = f"https://vulniverse.invalid/schemas/{profile_id}/authoring.schema.json"
    schema["title"] = f"Vulniverse {label}{variant_suffix} authoring schema"
    return schema
