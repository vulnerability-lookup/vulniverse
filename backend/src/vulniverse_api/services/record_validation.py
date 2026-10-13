from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker
from jsonschema.exceptions import ValidationError
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for

from .profiles import (
    SCHEMAS_ROOT,
    UnknownProfileError,
    resolve_profile,
    known_profiles
)


GCVE_EXTENSION_REGISTRY_PATH = SCHEMAS_ROOT / "extensions" / "gcve" / "registry.json"


@lru_cache(maxsize=1)
def get_gcve_extension_validators() -> dict[str, Validator]:
    with GCVE_EXTENSION_REGISTRY_PATH.open(encoding="utf-8") as registry_file:
        registry = json.load(registry_file)

    validators: dict[str, Validator] = {}

    for extension_id, config in registry.items():
        if not isinstance(config, dict):
            continue

        schema_path = config.get("schema")

        if not isinstance(schema_path, str):
            continue

        with (SCHEMAS_ROOT / schema_path).open(encoding="utf-8") as schema_file:
            schema = json.load(schema_file)

        validator_class = validator_for(schema)
        validator_class.check_schema(schema)

        validators[extension_id] = validator_class(
            schema,
            format_checker=FormatChecker(),
        )

    return validators


def deep_merge_properties(
    base: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    """Recursively merge overlay into base, overlay values winning on
    conflict except where both sides have a dict at the same key
    (merged recursively too). A plain dict.update() would let an
    overlay legalizing a nested property (e.g.
    containers.properties.cna.properties.x_gcve) silently clobber
    every *other* sibling property already declared at that same
    level — mirrors scripts/generate_editor_schemas.py's identical
    helper, which has the same bug for the same reason.
    """
    merged = dict(base)

    for key, value in overlay.items():
        existing = merged.get(key)

        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = deep_merge_properties(existing, value)
        else:
            merged[key] = copy.deepcopy(value)

    return merged


def apply_schema_overlay(
    schema: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    overlay_config = profile.get("schemaOverlay")

    if overlay_config is None:
        return schema

    if not isinstance(
        overlay_config,
        dict,
    ):
        raise ValueError("schemaOverlay must be an object.")

    overlay_path = overlay_config.get("path")

    if not isinstance(
        overlay_path,
        str,
    ):
        raise ValueError("schemaOverlay.path must be a string.")

    with (SCHEMAS_ROOT / overlay_path).open(
        encoding="utf-8",
    ) as overlay_file:
        overlay = json.load(overlay_file)

    if not isinstance(
        overlay,
        dict,
    ):
        raise ValueError("Schema overlay root must be an object.")

    apply_to = overlay_config.get(
        "applyTo",
        "root",
    )

    if apply_to == "root":
        return deep_merge_properties(
            schema,
            overlay,
        )

    if apply_to == "rootOneOfBranches":
        branches = schema.get("oneOf")

        if not isinstance(
            branches,
            list,
        ):
            raise ValueError(
                "schemaOverlay.applyTo=rootOneOfBranches requires a root oneOf."
            )

        result = copy.deepcopy(schema)

        result_branches = result["oneOf"]

        for index, branch in enumerate(result_branches):
            if not isinstance(
                branch,
                dict,
            ):
                continue

            result_branches[index] = deep_merge_properties(
                branch,
                overlay,
            )

        return result

    raise ValueError(f"Unsupported schemaOverlay.applyTo value: {apply_to!r}")


@lru_cache(maxsize=8)
def get_profile_validator(
    profile_id: str,
) -> Validator:
    profile = resolve_profile(profile_id)

    base_schema_path = profile.get("baseSchema")

    if not isinstance(
        base_schema_path,
        str,
    ):
        raise ValueError(f"Profile {profile_id!r} has no baseSchema.")

    with (SCHEMAS_ROOT / base_schema_path).open(
        encoding="utf-8",
    ) as schema_file:
        schema = json.load(schema_file)

    if not isinstance(
        schema,
        dict,
    ):
        raise ValueError(f"Schema for {profile_id!r} is not an object.")

    schema = apply_schema_overlay(
        schema,
        profile,
    )

    validator_class = validator_for(schema)

    validator_class.check_schema(schema)

    return validator_class(
        schema,
        format_checker=FormatChecker(),
    )


def preferred_root_branch(
    profile: dict[str, Any],
) -> tuple[str, int] | None:
    validation = profile.get("validation")

    if not isinstance(
        validation,
        dict,
    ):
        return None

    preferred = validation.get("preferredRootBranch")

    if not isinstance(
        preferred,
        dict,
    ):
        return None

    keyword = preferred.get("keyword")

    index = preferred.get("index")

    if not isinstance(
        keyword,
        str,
    ) or not isinstance(
        index,
        int,
    ):
        return None

    return (
        keyword,
        index,
    )


@lru_cache(maxsize=8)
def get_gcve_validator(profile_id: str) -> Validator:
    """
    Validates directly against $defs.GCVEExtension rather than the
    vendored GCVE schema's own top-level oneOf (single object vs.
    array of objects) — that wrapper exists for the upstream CLI's
    whole-document/whole-directory validation mode, not Vulniverse's
    single already-located x_gcve-array model, and skipping it avoids
    ever needing expand_composite_error to disambiguate that branch.
    """
    profile = resolve_profile(profile_id)

    extension_schemas = profile.get("extensionSchemas")

    if not isinstance(extension_schemas, list) or not extension_schemas:
        raise UnknownProfileError(profile_id)

    with (SCHEMAS_ROOT / extension_schemas[0]).open(
        encoding="utf-8",
    ) as schema_file:
        extension_schema = json.load(schema_file)

    definitions = extension_schema.get("$defs", {})

    if "GCVEExtension" not in definitions:
        raise UnknownProfileError(profile_id)

    synthetic_schema = {
        "$schema": extension_schema.get("$schema"),
        "$defs": definitions,
        "type": "array",
        "items": {"$ref": "#/$defs/GCVEExtension"},
    }

    validator_class = validator_for(synthetic_schema)
    validator_class.check_schema(synthetic_schema)

    return validator_class(
        synthetic_schema,
        format_checker=FormatChecker(),
    )


REQUIRED_PROPERTY_MESSAGE = re.compile(r"^'(.+)' is a required property$")


def is_discriminator_miss(
    error: ValidationError,
) -> bool:
    """
    True if this error means the document isn't even attempting to
    satisfy this branch's identifying property — either because a
    present value doesn't match a fixed enum/const, or because a
    required property that itself must hold a fixed enum/const
    value (e.g. cveMetadata.state) is missing outright.
    """

    if error.validator in ("enum", "const"):
        return True

    if error.validator != "required":
        return False

    match = REQUIRED_PROPERTY_MESSAGE.match(error.message)

    if not match:
        return False

    schema = error.schema if isinstance(error.schema, dict) else {}
    properties = schema.get("properties")

    if not isinstance(properties, dict):
        return False

    property_schema = properties.get(match.group(1))

    return isinstance(property_schema, dict) and (
        "enum" in property_schema or "const" in property_schema
    )


def expand_composite_error(
    error: ValidationError,
    *,
    tie_break_key: Any = None,
) -> list[ValidationError]:
    """
    Replace a oneOf/anyOf failure with the specific errors from
    whichever candidate schema came closest to matching, instead
    of the single generic "is not valid under any of the given
    schemas" message that hides all of them.

    A branch that fails on its own discriminator (e.g. CVE's
    cveMetadata.state enum picking between the published/rejected
    variants) failed for the trivial reason that the document
    wasn't attempting to satisfy that branch at all — such a
    branch can look "closest" by raw error count purely because it
    happens to be a smaller/more permissive schema, hiding the
    real errors from the branch the document actually matches.
    Branches without such a miss are preferred.

    If every branch has one — the discriminator property is absent
    from the document altogether, so no branch's condition is even
    approximately satisfied — raw error count alone would still
    systematically favor whichever branch's schema is structurally
    smaller/less demanding (e.g. Rejected over Published, for any
    substantially incomplete draft record). `tie_break_key`, when
    given and present among the branches, is preferred in exactly
    that situation instead. It only applies to this top-level call
    — it is deliberately not propagated to the recursive calls this
    function makes on nested composite errors, since a nested oneOf/
    anyOf (e.g. an affected item's vendor+product vs collectionURL+
    packageName) has no such caller-known preferred branch.
    """

    if not error.context:
        return [error]

    branches: dict[Any, list[ValidationError]] = {}

    for sub_error in error.context:
        branch_key = tuple(sub_error.absolute_schema_path)[:2]
        branches.setdefault(branch_key, []).append(sub_error)

    non_miss_keys = [
        key
        for key, branch_errors in branches.items()
        if not any(is_discriminator_miss(sub_error) for sub_error in branch_errors)
    ]

    if non_miss_keys:
        candidates = [branches[key] for key in non_miss_keys]
    elif tie_break_key in branches:
        candidates = [branches[tie_break_key]]
    else:
        candidates = list(branches.values())

    closest_branch = min(
        candidates,
        key=len,
    )

    expanded: list[ValidationError] = []

    for sub_error in closest_branch:
        expanded.extend(
            expand_composite_error(sub_error),
        )

    return expanded


def shape_error(
    error: ValidationError,
    *,
    path_prefix: tuple[Any, ...] = (),
    severity: str = "error",
) -> dict[str, Any]:
    return {
        "path": [*path_prefix, *error.absolute_path],
        "schemaPath": list(error.absolute_schema_path),
        "message": error.message,
        "validator": error.validator,
        "severity": severity,
    }


def find_x_gcve_occurrences(
    document: Any,
    path: tuple[Any, ...] = (),
) -> list[tuple[tuple[Any, ...], Any]]:
    """
    x_gcve is validated wherever it appears — record root,
    containers.cna.x_gcve, containers.adp[*].x_gcve, other nested x_
    namespaces — per GCVE-BCP-05's "location-agnostic" rule, rather
    than special-cased per container.
    """
    occurrences: list[tuple[tuple[Any, ...], Any]] = []

    if isinstance(document, dict):
        for key, value in document.items():
            child_path = (*path, key)

            if key == "x_gcve":
                occurrences.append((child_path, value))

            occurrences.extend(
                find_x_gcve_occurrences(value, child_path),
            )
    elif isinstance(document, list):
        for index, item in enumerate(document):
            occurrences.extend(
                find_x_gcve_occurrences(item, (*path, index)),
            )

    return occurrences


# recordType values that GCVE-BCP-05 requires a non-empty
# relationships array for.
MANDATORY_RELATIONSHIP_RECORD_TYPES = {
    "update",
    "analysis",
    "metadata",
    "reference",
    "comment",
    "statement",
    "remediation",
    "deprecation",
    "detection",
    "translation",
}

# BCP-05's recommended VXREF-derived relationship types. Unknown
# values are forward-compatible (allowed) but warned about.
RECOMMENDED_RELATIONSHIP_TYPES = {
    "possibly_related",
    "related",
    "not equal",
    "equal",
    "superset",
    "subset",
    "overlap",
    "opposes",
    "not_applicable",
}


def validate_gcve_semantics(
    record: dict[str, Any],
    profile_id: str,
) -> list[dict[str, Any]]:
    validator = get_gcve_validator(profile_id)
    extension_validators = get_gcve_extension_validators()
    errors: list[dict[str, Any]] = []

    for path, value in find_x_gcve_occurrences(record):
        if not isinstance(value, list):
            # Base schema validation already flags a type mismatch
            # here (x_gcve must be an array).
            continue

        for schema_error in validator.iter_errors(value):
            for expanded in expand_composite_error(schema_error):
                errors.append(
                    shape_error(expanded, path_prefix=path),
                )

        for index, entry in enumerate(value):
            if not isinstance(entry, dict):
                continue

            entry_path = (*path, index)

            extensions = entry.get("extensions")

            if extensions is not None:
                if not isinstance(extensions, dict):
                    errors.append(
                        {
                            "path": [
                                *entry_path,
                                "extensions",
                            ],
                            "schemaPath": [],
                            "message": ("extensions must be an object."),
                            "validator": "gcve-extension",
                            "severity": "error",
                        }
                    )
                else:
                    for extension_id, extension_value in extensions.items():
                        extension_validator = extension_validators.get(extension_id)

                        # Unknown extensions remain valid /
                        # forward-compatible.
                        if extension_validator is None:
                            continue

                        for schema_error in extension_validator.iter_errors(
                            extension_value
                        ):
                            for expanded in expand_composite_error(schema_error):
                                errors.append(
                                    shape_error(
                                        expanded,
                                        path_prefix=(
                                            *entry_path,
                                            "extensions",
                                            extension_id,
                                        ),
                                    )
                                )
            record_type = entry.get("recordType")
            relationships = entry.get("relationships")

            if record_type in MANDATORY_RELATIONSHIP_RECORD_TYPES and not relationships:
                errors.append(
                    {
                        "path": [*entry_path, "relationships"],
                        "schemaPath": [],
                        "message": (
                            f"recordType {record_type!r} requires a "
                            "non-empty relationships array."
                        ),
                        "validator": "gcve-bcp-05",
                        "severity": "error",
                    }
                )

            if record_type == "translation" and not entry.get("language"):
                errors.append(
                    {
                        "path": [*entry_path, "language"],
                        "schemaPath": [],
                        "message": (
                            "recordType 'translation' requires a language field."
                        ),
                        "validator": "gcve-bcp-05",
                        "severity": "error",
                    }
                )

            if not isinstance(relationships, list):
                continue

            for relationship_index, relationship in enumerate(
                relationships,
            ):
                if not isinstance(relationship, dict):
                    continue

                relationship_type = relationship.get("type")

                if (
                    relationship_type is not None
                    and relationship_type not in RECOMMENDED_RELATIONSHIP_TYPES
                ):
                    errors.append(
                        {
                            "path": [
                                *entry_path,
                                "relationships",
                                relationship_index,
                                "type",
                            ],
                            "schemaPath": [],
                            "message": (
                                f"{relationship_type!r} is not one of "
                                "the BCP-05 recommended relationship "
                                "types."
                            ),
                            "validator": "gcve-bcp-05",
                            "severity": "warning",
                        }
                    )

    return errors


# Dispatches on manifest.json's per-profile "semanticValidator" id,
# rather than a "profile.startswith('gcve-')" string check, so a
# future profile only needs a manifest entry + a registry entry here.
SEMANTIC_VALIDATORS: dict[
    str,
    Callable[[dict[str, Any], str], list[dict[str, Any]]],
] = {
    "gcve-bcp-05": validate_gcve_semantics,
}


def validate_record(
    record: dict[str, Any],
    profile_id: str,
) -> list[dict[str, Any]]:
    profile = resolve_profile(profile_id)

    validator = get_profile_validator(profile_id)

    tie_break_key = preferred_root_branch(profile)

    base_errors: list[ValidationError] = []

    for error in validator.iter_errors(record):
        base_errors.extend(
            expand_composite_error(
                error,
                tie_break_key=tie_break_key,
            )
        )

    errors = [shape_error(error) for error in base_errors]

    semantic_validator_id = profile.get("semanticValidator")

    semantic_validator = (
        SEMANTIC_VALIDATORS.get(semantic_validator_id)
        if isinstance(
            semantic_validator_id,
            str,
        )
        else None
    )

    if semantic_validator:
        errors.extend(
            semantic_validator(
                record,
                profile_id,
            )
        )

    errors.sort(key=lambda error: error["path"])

    return errors
