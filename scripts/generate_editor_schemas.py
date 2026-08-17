#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any


JsonObject = dict[str, Any]


class GenerationError(RuntimeError):
    pass


def load_json(path: Path) -> JsonObject:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise GenerationError(f"File does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise GenerationError(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(value, dict):
        raise GenerationError(f"Expected a JSON object in {path}")

    return value


def write_json(
    path: Path,
    value: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )


def decode_pointer_token(
    token: str,
) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_json_pointer(
    document: Any,
    pointer: str,
) -> Any:
    if pointer == "#":
        return document

    if not pointer.startswith("#/"):
        raise GenerationError(
            f"Only local JSON references are supported: {pointer}")

    current = document

    for raw_token in pointer[2:].split("/"):
        token = decode_pointer_token(raw_token)

        if isinstance(current, dict):
            if token not in current:
                raise GenerationError(f"Reference does not exist: {pointer}")

            current = current[token]

        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (
                ValueError,
                IndexError,
            ) as error:
                raise GenerationError(f"Invalid list reference: {
                                      pointer}") from error

        else:
            raise GenerationError(f"Reference cannot be traversed: {pointer}")

    return current


def dereference(
    node: Any,
    root: JsonObject,
    active_refs: tuple[str, ...] = (),
) -> Any:
    """
    Resolve local $ref values for the generated authoring schema.

    The official schema remains untouched. The expanded schema is
    only used for form generation.
    """

    if isinstance(node, list):
        return [
            dereference(
                item,
                root,
                active_refs,
            )
            for item in node
        ]

    if not isinstance(node, dict):
        return copy.deepcopy(node)

    reference = node.get("$ref")

    if isinstance(reference, str):
        if not reference.startswith("#/"):
            # Keep external references unchanged.
            return {
                key: dereference(
                    value,
                    root,
                    active_refs,
                )
                for key, value in node.items()
            }

        if reference in active_refs:
            # Preserve the reference if a recursive schema is found.
            return copy.deepcopy(node)

        referenced_node = resolve_json_pointer(
            root,
            reference,
        )

        expanded = dereference(
            referenced_node,
            root,
            active_refs + (reference,),
        )

        if not isinstance(expanded, dict):
            return expanded

        result = copy.deepcopy(expanded)

        # The authoring schema also preserves useful annotations
        # placed next to $ref values.
        for key, value in node.items():
            if key == "$ref":
                continue

            result[key] = dereference(
                value,
                root,
                active_refs,
            )

        return result

    return {
        key: dereference(
            value,
            root,
            active_refs,
        )
        for key, value in node.items()
    }


def strip_nested_ids(
    node: Any,
    is_root: bool = True,
) -> None:
    """
    Remove $id from every subschema except the document root.

    The authoring schema is fully dereferenced, so no $ref remains
    to resolve against a nested $id. A definition referenced from
    more than one place (e.g. "reference") would otherwise carry
    the same $id into multiple inlined copies, and ajv raises
    "resolves to more than one schema" for the duplicate.
    """

    if isinstance(node, list):
        for item in node:
            strip_nested_ids(item, is_root=False)

        return

    if not isinstance(node, dict):
        return

    if not is_root:
        node.pop("$id", None)

    for value in node.values():
        strip_nested_ids(value, is_root=False)


def select_variant(
    official_schema: JsonObject,
    title: str,
) -> JsonObject:
    variants = official_schema.get("oneOf")

    if not isinstance(variants, list):
        raise GenerationError("Official schema has no root oneOf variants.")

    for candidate in variants:
        if isinstance(candidate, dict) and candidate.get("title") == title:
            expanded = dereference(
                candidate,
                official_schema,
            )

            if not isinstance(expanded, dict):
                raise GenerationError("Expanded variant is not an object.")

            return expanded

    raise GenerationError(f"Schema variant was not found: {title}")


def schema_for_data_path(
    schema: JsonObject,
    data_path: str,
) -> JsonObject | None:
    current: Any = schema

    if not data_path:
        return schema

    for part in data_path.split("."):
        if not isinstance(current, dict):
            return None

        properties = current.get("properties")

        if not isinstance(properties, dict):
            return None

        current = properties.get(part)

        if current is None:
            return None

    return current if isinstance(current, dict) else None


def scope_for_data_path(
    data_path: str,
) -> str:
    parts = data_path.split(".")

    return "#/" + "/".join(
        item
        for part in parts
        for item in (
            "properties",
            part.replace("~", "~0").replace("/", "~1"),
        )
    )


def humanize(
    value: str,
) -> str:
    result: list[str] = []

    for index, character in enumerate(value):
        if index > 0 and character.isupper() and not value[index - 1].isupper():
            result.append(" ")

        result.append(character)

    return "".join(result).replace("_", " ").capitalize()


def make_control(
    schema: JsonObject,
    data_path: str,
    control_options: dict[str, Any],
) -> JsonObject | None:
    field_schema = schema_for_data_path(
        schema,
        data_path,
    )

    if field_schema is None:
        return None

    final_part = data_path.split(".")[-1]

    label = (
        field_schema.get("title")
        if isinstance(
            field_schema.get("title"),
            str,
        )
        else humanize(final_part)
    )

    control: JsonObject = {
        "type": "Control",
        "scope": scope_for_data_path(
            data_path,
        ),
        "label": label,
    }

    configured_options = control_options.get(
        data_path,
        {},
    )

    options: JsonObject = {}

    if field_schema.get("type") == "array":
        options.update(
            {
                "detail": "GENERATED",
                "showSortButtons": True,
            }
        )

    if isinstance(configured_options, dict):
        options.update(copy.deepcopy(configured_options))

    if options:
        control["options"] = options

    return control


def cna_property_names(
    authoring_schema: JsonObject,
) -> list[str]:
    cna_schema = schema_for_data_path(
        authoring_schema,
        "containers.cna",
    )

    if not cna_schema:
        return []

    properties = cna_schema.get("properties")

    if not isinstance(properties, dict):
        return []

    return sorted(properties)


def collect_field_catalog(
    schema: JsonObject,
    path: str = "",
    parent_required: set[str] | None = None,
) -> list[JsonObject]:
    parent_required = parent_required or set()
    fields: list[JsonObject] = []

    properties = schema.get("properties")

    if not isinstance(properties, dict):
        return fields

    required = schema.get("required")
    required_names = set(required) if isinstance(required, list) else set()

    for name, child in properties.items():
        if not isinstance(child, dict):
            continue

        child_path = f"{path}.{name}" if path else name

        field_type = child.get("type")

        if not isinstance(field_type, str):
            if "enum" in child:
                field_type = "string"
            elif "properties" in child:
                field_type = "object"
            elif "items" in child:
                field_type = "array"
            else:
                field_type = "unknown"

        fields.append(
            {
                "path": child_path,
                "scope": scope_for_data_path(
                    child_path,
                ),
                "type": field_type,
                "required": name in required_names,
                "title": child.get("title"),
                "description": child.get("description"),
                "enum": child.get("enum"),
                "format": child.get("format"),
            }
        )

        if field_type == "object":
            fields.extend(
                collect_field_catalog(
                    child,
                    child_path,
                    required_names,
                )
            )

        elif field_type == "array":
            items = child.get("items")

            if isinstance(items, dict) and items.get("type") == "object":
                fields.extend(
                    collect_field_catalog(
                        items,
                        child_path + "[]",
                    )
                )

    return fields


def generate(
    project_root: Path,
    profile_id: str,
    strict: bool,
) -> None:
    schemas_root = project_root / "schemas"

    manifest = load_json(schemas_root / "manifest.json")

    profiles = manifest.get("profiles")

    if not isinstance(profiles, dict):
        raise GenerationError("manifest.json has no profiles object.")

    profile = profiles.get(profile_id)

    if not isinstance(profile, dict):
        raise GenerationError(f"Unknown schema profile: {profile_id}")

    base_schema_value = profile.get("baseSchema")

    if not isinstance(base_schema_value, str):
        raise GenerationError(f"{profile_id} has no baseSchema.")

    version = profile.get("version")

    if not isinstance(version, str):
        version = profile_id.removeprefix("cve-")

    official_path = schemas_root / base_schema_value

    official_schema = load_json(official_path)

    kind = profile.get("kind", "cve")

    layout_config = load_json(
        schemas_root / "editor" / "cve.layout.json",
    )

    if kind == "gcve":
        # Every gcve-kind profile builds on the same CVE container
        # shape, so it reuses cve.layout.json as a base and only adds
        # the handful of extra sections/controlOptions it needs — not
        # a full duplicate copy that would silently drift from the
        # base layout whenever that one changes.
        extra_layout = load_json(
            schemas_root / "editor" / "gcve.layout-extra.json",
        )

        layout_config = {
            **layout_config,
            "sections": [
                *layout_config.get("sections", []),
                *extra_layout.get("sections", []),
            ],
            "controlOptions": {
                **layout_config.get("controlOptions", {}),
                **extra_layout.get("controlOptions", {}),
            },
        }

    variant = layout_config.get(
        "variant",
        "Published",
    )

    if not isinstance(variant, str):
        raise GenerationError("variant must be a string.")

    authoring_schema = select_variant(
        official_schema,
        variant,
    )

    strip_nested_ids(authoring_schema)

    overlay_path = schemas_root / "overlays" / f"{profile_id}.json"

    if overlay_path.exists():
        # File-presence-driven, not an if-profile-equals special
        # case: cve-5.2.0 has no overlay file, so its output is
        # byte-for-byte unaffected. The overlay's only job is to
        # legalize extension properties (e.g. x_gcve) that the base
        # official schema doesn't define — it must stay permissive;
        # real strictness belongs in the extension schema itself
        # (see backend/.../record_validation.py's get_gcve_validator,
        # which is the actual authority validating x_gcve content).
        overlay = load_json(overlay_path)

        authoring_schema.setdefault("properties", {}).update(
            copy.deepcopy(overlay.get("properties", {})),
        )

    authoring_schema["$schema"] = official_schema.get("$schema")

    if kind == "gcve":
        base_profile_id = profile.get("baseProfile")
        base_version = None

        if isinstance(base_profile_id, str):
            base_profile = profiles.get(base_profile_id)

            if isinstance(base_profile, dict):
                base_version = base_profile.get("version")

        schema_label = f"{profile.get('bcp', 'GCVE')}/{version}"

        if base_version:
            schema_label += f" (CVE {base_version})"
    else:
        schema_label = f"CVE {version}"

    authoring_schema["$id"] = (
        f"https://vulniverse.invalid/schemas/{
            profile_id}/authoring.schema.json"
    )

    authoring_schema["title"] = (
        f"Vulniverse {schema_label} {variant} authoring schema"
    )

    authoring_schema["x-vulniverse-source"] = {
        "profile": profile_id,
        "officialSchema": (base_schema_value),
        "variant": variant,
    }

    sections = layout_config.get("sections")

    if not isinstance(sections, list):
        raise GenerationError("layout sections must be an array.")

    hidden_paths = set(
        layout_config.get(
            "hiddenPaths",
            [],
        )
    )

    control_options = layout_config.get(
        "controlOptions",
        {},
    )

    if not isinstance(control_options, dict):
        raise GenerationError("controlOptions must be an object.")

    categories: list[JsonObject] = []
    configured_paths: set[str] = set()
    missing_paths: list[str] = []

    for section in sections:
        if not isinstance(section, dict):
            continue

        section_id = section.get("id")
        section_label = section.get("label")
        paths = section.get("paths")

        if (
            not isinstance(section_id, str)
            or not isinstance(section_label, str)
            or not isinstance(paths, list)
        ):
            raise GenerationError("Invalid section configuration.")

        controls: list[JsonObject] = []

        for value in paths:
            if not isinstance(value, str):
                continue

            configured_paths.add(value)

            if value in hidden_paths:
                continue

            control = make_control(
                authoring_schema,
                value,
                control_options,
            )

            if control is None:
                missing_paths.append(value)
                continue

            controls.append(control)

        if controls:
            categories.append(
                {
                    "type": "Category",
                    "id": section_id,
                    "label": section_label,
                    "elements": controls,
                }
            )

    automatically_added: list[str] = []

    for property_name in cna_property_names(authoring_schema):
        path = "containers.cna." + property_name

        if path in configured_paths or path in hidden_paths:
            continue

        control = make_control(
            authoring_schema,
            path,
            control_options,
        )

        if control is not None:
            automatically_added.append(path)

    if automatically_added:
        categories.append(
            {
                "type": "Category",
                "id": "additional",
                "label": "Additional fields",
                "elements": [
                    make_control(
                        authoring_schema,
                        path,
                        control_options,
                    )
                    for path in automatically_added
                ],
            }
        )

    ui_schema: JsonObject = {
        "type": "Categorization",
        "elements": categories,
    }

    # Keyed by profile_id, not "cve"/version: a gcve-kind profile's
    # `version` is its BCP spec version (e.g. "1.7"), not a CVE
    # version, and would otherwise collide with CVE-version-numbered
    # output paths. profile_id already equals f"cve-{version}" for
    # every cve-kind profile, so this is a no-op rename for those.
    output_directory = schemas_root / "generated" / profile_id

    frontend_directory = (
        project_root / "frontend" / "src" /
        "generated" / "schemas" / profile_id
    )

    write_json(
        output_directory / "authoring.schema.json",
        authoring_schema,
    )

    write_json(
        output_directory / "ui.schema.json",
        ui_schema,
    )

    write_json(
        output_directory / "fields.json",
        collect_field_catalog(authoring_schema),
    )

    report = {
        "profile": profile_id,
        "variant": variant,
        "officialSchema": str(official_path.relative_to(project_root)),
        "categories": [category.get("id") for category in categories],
        "missingConfiguredPaths": sorted(set(missing_paths)),
        "automaticallyAddedPaths": (automatically_added),
    }

    write_json(
        output_directory / "generation-report.json",
        report,
    )

    frontend_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for filename in (
        "authoring.schema.json",
        "ui.schema.json",
    ):
        shutil.copy2(
            output_directory / filename,
            frontend_directory / filename,
        )

    print(f"Generated {profile_id} editor schemas.")

    if missing_paths:
        print(
            "Configured paths not present:",
            file=sys.stderr,
        )

        for path in sorted(set(missing_paths)):
            print(
                f"  - {path}",
                file=sys.stderr,
            )

        if strict:
            raise GenerationError("Schema generation found missing paths.")


def parse_arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Generate Vulniverse editor schemas from an official CVE schema.")
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
    )

    parser.add_argument(
        "--profile",
        default=None,
        help=(
            "Schema profile from schemas/manifest.json. "
            "Defaults to currentProfiles.cve."
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help=("Fail if configured layout paths do not exist in the official schema."),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    root = args.project_root.resolve()

    if args.profile:
        profile = args.profile
    else:
        manifest = load_json(root / "schemas" / "manifest.json")

        current_profiles = manifest.get("currentProfiles")

        if not isinstance(
            current_profiles,
            dict,
        ):
            raise GenerationError("No currentProfiles in manifest.")

        profile = current_profiles.get("cve")

        if not isinstance(profile, str):
            raise GenerationError("No current CVE profile configured.")

    generate(
        root,
        profile,
        args.strict,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GenerationError as error:
        print(
            f"Schema generation failed: {error}",
            file=sys.stderr,
        )

        raise SystemExit(2)
