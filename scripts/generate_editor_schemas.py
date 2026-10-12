#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

from helper.console import Console
from helper.errors import ScriptError
from helper.json import load_json_object, write_json


JsonObject = dict[str, Any]

console = Console(
    "vulniverse-schema-generator"
)


class GenerationError(ScriptError):
    """Generating editor schemas failed."""


def load_gcve_extension_schemas(
    schemas_root: Path,
) -> dict[str, JsonObject]:
    registry_path = (
        schemas_root
        / "extensions"
        / "gcve"
        / "registry.json"
    )

    registry = load_json_object(
        registry_path
    )

    result: dict[
        str,
        JsonObject,
    ] = {}

    for extension_id, config in registry.items():
        if not isinstance(
            config,
            dict,
        ):
            raise GenerationError(
                "Invalid GCVE extension configuration: "
                f"{extension_id}"
            )

        schema_value = config.get(
            "schema"
        )

        if not isinstance(
            schema_value,
            str,
        ):
            raise GenerationError(
                f"{extension_id} has no schema path."
            )

        extension_schema = (
            load_json_object(
                schemas_root
                / schema_value
            )
        )

        # The schema is embedded below another root schema.
        extension_schema.pop(
            "$id",
            None,
        )

        extension_schema.pop(
            "$schema",
            None,
        )

        result[
            extension_id
        ] = extension_schema

    return result


def add_gcve_extension_schemas(
    node: Any,
    extension_schemas: dict[
        str,
        JsonObject,
    ],
) -> None:
    if isinstance(
        node,
        list,
    ):
        for item in node:
            add_gcve_extension_schemas(
                item,
                extension_schemas,
            )

        return

    if not isinstance(
        node,
        dict,
    ):
        return

    properties = node.get(
        "properties"
    )

    if isinstance(
        properties,
        dict,
    ):
        x_gcve = properties.get(
            "x_gcve"
        )

        if isinstance(
            x_gcve,
            dict,
        ):
            items = x_gcve.get(
                "items"
            )

            if isinstance(
                items,
                dict,
            ):
                item_properties = (
                    items.setdefault(
                        "properties",
                        {},
                    )
                )

                if isinstance(
                    item_properties,
                    dict,
                ):
                    extensions = (
                        item_properties.setdefault(
                            "extensions",
                            {
                                "type": "object",
                                "title": "GCVE extensions",
                                "properties": {},
                                "additionalProperties": True,
                            },
                        )
                    )

                    if not isinstance(
                        extensions,
                        dict,
                    ):
                        raise GenerationError(
                            "GCVE extensions schema is not an object."
                        )

                    extension_properties = (
                        extensions.setdefault(
                            "properties",
                            {},
                        )
                    )

                    if not isinstance(
                        extension_properties,
                        dict,
                    ):
                        raise GenerationError(
                            "GCVE extension properties are not an object."
                        )

                    for (
                        extension_id,
                        schema,
                    ) in extension_schemas.items():
                        extension_properties[
                            extension_id
                        ] = copy.deepcopy(
                            schema
                        )

                    # Unknown future extensions must survive.
                    extensions[
                        "additionalProperties"
                    ] = True

    for child in node.values():
        add_gcve_extension_schemas(
            child,
            extension_schemas,
        )


def augment_gcve_extensions(
    authoring_schema: JsonObject,
    schemas_root: Path,
    _profile: JsonObject,
) -> None:
    extension_schemas = (
        load_gcve_extension_schemas(
            schemas_root
        )
    )

    add_gcve_extension_schemas(
        authoring_schema,
        extension_schemas,
    )


EditorAugmenter = Callable[
    [
        JsonObject,
        Path,
        JsonObject,
    ],
    None,
]


EDITOR_AUGMENTERS: dict[
    str,
    EditorAugmenter,
] = {
    "gcve-extensions":
        augment_gcve_extensions,
}


def decode_pointer_token(
    token: str,
) -> str:
    return (
        token
        .replace(
            "~1",
            "/",
        )
        .replace(
            "~0",
            "~",
        )
    )


def resolve_json_pointer(
    document: Any,
    pointer: str,
) -> Any:
    if pointer == "#":
        return document

    if not pointer.startswith(
        "#/"
    ):
        raise GenerationError(
            "Only local JSON references are supported: "
            f"{pointer}"
        )

    current = document

    for raw_token in (
        pointer[2:].split("/")
    ):
        token = decode_pointer_token(
            raw_token
        )

        if isinstance(
            current,
            dict,
        ):
            if token not in current:
                raise GenerationError(
                    "Reference does not exist: "
                    f"{pointer}"
                )

            current = current[
                token
            ]

        elif isinstance(
            current,
            list,
        ):
            try:
                current = current[
                    int(token)
                ]

            except (
                ValueError,
                IndexError,
            ) as error:
                raise GenerationError(
                    "Invalid list reference: "
                    f"{pointer}"
                ) from error

        else:
            raise GenerationError(
                "Reference cannot be traversed: "
                f"{pointer}"
            )

    return current


def dereference(
    node: Any,
    root: JsonObject,
    active_refs: tuple[
        str,
        ...,
    ] = (),
) -> Any:
    """
    Resolve local $ref values for the generated authoring schema.

    External references and recursive local references remain unchanged.
    """

    if isinstance(
        node,
        list,
    ):
        return [
            dereference(
                item,
                root,
                active_refs,
            )
            for item in node
        ]

    if not isinstance(
        node,
        dict,
    ):
        return copy.deepcopy(
            node
        )

    reference = node.get(
        "$ref"
    )

    if isinstance(
        reference,
        str,
    ):
        if not reference.startswith(
            "#/"
        ):
            return {
                key:
                    dereference(
                        value,
                        root,
                        active_refs,
                    )

                for key, value
                in node.items()
            }

        if reference in active_refs:
            return copy.deepcopy(
                node
            )

        referenced_node = (
            resolve_json_pointer(
                root,
                reference,
            )
        )

        expanded = dereference(
            referenced_node,
            root,
            active_refs
            + (reference,),
        )

        if not isinstance(
            expanded,
            dict,
        ):
            return expanded

        result = copy.deepcopy(
            expanded
        )

        for key, value in node.items():
            if key == "$ref":
                continue

            result[
                key
            ] = dereference(
                value,
                root,
                active_refs,
            )

        return result

    return {
        key:
            dereference(
                value,
                root,
                active_refs,
            )

        for key, value
        in node.items()
    }


def strip_nested_ids(
    node: Any,
    *,
    is_root: bool = True,
) -> None:
    """
    Remove $id values from inlined subschemas.

    Repeated $id values in dereferenced subschemas cause AJV to report
    that one identifier resolves to multiple schemas.
    """

    if isinstance(
        node,
        list,
    ):
        for item in node:
            strip_nested_ids(
                item,
                is_root=False,
            )

        return

    if not isinstance(
        node,
        dict,
    ):
        return

    if not is_root:
        node.pop(
            "$id",
            None,
        )

    for value in node.values():
        strip_nested_ids(
            value,
            is_root=False,
        )


def select_variant(
    official_schema: JsonObject,
    title: str,
) -> JsonObject:
    variants = official_schema.get(
        "oneOf"
    )

    if not isinstance(
        variants,
        list,
    ):
        raise GenerationError(
            "Official schema has no root oneOf variants."
        )

    for candidate in variants:
        if (
            isinstance(
                candidate,
                dict,
            )
            and candidate.get(
                "title"
            ) == title
        ):
            expanded = dereference(
                candidate,
                official_schema,
            )

            if not isinstance(
                expanded,
                dict,
            ):
                raise GenerationError(
                    "Expanded schema variant is not an object."
                )

            return expanded

    raise GenerationError(
        f"Schema variant was not found: {title}"
    )


def schema_for_data_path(
    schema: JsonObject,
    data_path: str,
) -> JsonObject | None:
    current: Any = schema

    if not data_path:
        return schema

    for part in data_path.split(
        "."
    ):
        if not isinstance(
            current,
            dict,
        ):
            return None

        properties = current.get(
            "properties"
        )

        if not isinstance(
            properties,
            dict,
        ):
            return None

        current = properties.get(
            part
        )

        if current is None:
            return None

    return (
        current
        if isinstance(
            current,
            dict,
        )
        else None
    )


def scope_for_data_path(
    data_path: str,
) -> str:
    parts = data_path.split(
        "."
    )

    return "#/" + "/".join(
        item

        for part in parts

        for item in (
            "properties",
            part
            .replace(
                "~",
                "~0",
            )
            .replace(
                "/",
                "~1",
            ),
        )
    )


def humanize(
    value: str,
) -> str:
    result: list[str] = []

    for index, character in enumerate(
        value
    ):
        if (
            index > 0
            and character.isupper()
            and not value[
                index - 1
            ].isupper()
        ):
            result.append(
                " "
            )

        result.append(
            character
        )

    return (
        "".join(result)
        .replace(
            "_",
            " ",
        )
        .capitalize()
    )


def make_control(
    schema: JsonObject,
    data_path: str,
    control_options: dict[
        str,
        Any,
    ],
) -> JsonObject | None:
    field_schema = (
        schema_for_data_path(
            schema,
            data_path,
        )
    )

    if field_schema is None:
        return None

    final_part = (
        data_path
        .split(".")[-1]
    )

    title = field_schema.get(
        "title"
    )

    label = (
        title
        if isinstance(
            title,
            str,
        )
        else humanize(
            final_part
        )
    )

    control: JsonObject = {
        "type": "Control",
        "scope":
            scope_for_data_path(
                data_path
            ),
        "label": label,
    }

    configured_options = (
        control_options.get(
            data_path,
            {},
        )
    )

    options: JsonObject = {}

    if (
        field_schema.get(
            "type"
        ) == "array"
    ):
        options.update(
            {
                "detail":
                    "GENERATED",

                "showSortButtons":
                    True,
            }
        )

    if isinstance(
        configured_options,
        dict,
    ):
        options.update(
            copy.deepcopy(
                configured_options
            )
        )

    if options:
        control[
            "options"
        ] = options

    return control


def property_names_at_path(
    schema: JsonObject,
    data_path: str,
) -> list[str]:
    object_schema = (
        schema_for_data_path(
            schema,
            data_path,
        )
    )

    if object_schema is None:
        return []

    properties = object_schema.get(
        "properties"
    )

    if not isinstance(
        properties,
        dict,
    ):
        return []

    return sorted(
        properties
    )


def collect_field_catalog(
    schema: JsonObject,
    path: str = "",
) -> list[JsonObject]:
    fields: list[
        JsonObject
    ] = []

    properties = schema.get(
        "properties"
    )

    if not isinstance(
        properties,
        dict,
    ):
        return fields

    required = schema.get(
        "required"
    )

    required_names = (
        set(required)
        if isinstance(
            required,
            list,
        )
        else set()
    )

    for name, child in properties.items():
        if not isinstance(
            child,
            dict,
        ):
            continue

        child_path = (
            f"{path}.{name}"
            if path
            else name
        )

        field_type = child.get(
            "type"
        )

        if not isinstance(
            field_type,
            str,
        ):
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
                "path":
                    child_path,

                "scope":
                    scope_for_data_path(
                        child_path
                    ),

                "type":
                    field_type,

                "required":
                    name
                    in required_names,

                "title":
                    child.get(
                        "title"
                    ),

                "description":
                    child.get(
                        "description"
                    ),

                "enum":
                    child.get(
                        "enum"
                    ),

                "format":
                    child.get(
                        "format"
                    ),
            }
        )

        if field_type == "object":
            fields.extend(
                collect_field_catalog(
                    child,
                    child_path,
                )
            )

        elif field_type == "array":
            items = child.get(
                "items"
            )

            if (
                isinstance(
                    items,
                    dict,
                )
                and (
                    items.get(
                        "type"
                    ) == "object"
                    or "properties"
                    in items
                )
            ):
                fields.extend(
                    collect_field_catalog(
                        items,
                        child_path
                        + "[]",
                    )
                )

    return fields


def frontend_path_catalog(
    field_catalog: list[
        JsonObject
    ],
) -> list[JsonObject]:
    """
    Return only scalar field information required by Templates path
    autocomplete.
    """

    return [
        {
            "path":
                field[
                    "path"
                ],

            "title":
                field.get(
                    "title"
                ),

            "type":
                field[
                    "type"
                ],
        }

        for field
        in field_catalog

        if field[
            "type"
        ] not in (
            "object",
            "array",
            "unknown",
        )
    ]


def deep_merge(
    base: JsonObject,
    overlay: JsonObject,
) -> JsonObject:
    """
    Recursively merge an overlay without replacing sibling properties.
    """

    merged = copy.deepcopy(
        base
    )

    for key, value in overlay.items():
        existing = merged.get(
            key
        )

        if (
            isinstance(
                existing,
                dict,
            )
            and isinstance(
                value,
                dict,
            )
        ):
            merged[
                key
            ] = deep_merge(
                existing,
                value,
            )

        else:
            merged[
                key
            ] = copy.deepcopy(
                value
            )

    return merged


def merge_layout(
    base: JsonObject,
    extra: JsonObject,
) -> JsonObject:
    result = copy.deepcopy(
        base
    )

    base_sections = result.get(
        "sections",
        [],
    )

    extra_sections = extra.get(
        "sections",
        [],
    )

    if (
        not isinstance(
            base_sections,
            list,
        )
        or not isinstance(
            extra_sections,
            list,
        )
    ):
        raise GenerationError(
            "Layout sections must be arrays."
        )

    result[
        "sections"
    ] = [
        *base_sections,
        *extra_sections,
    ]

    base_hidden = result.get(
        "hiddenPaths",
        [],
    )

    extra_hidden = extra.get(
        "hiddenPaths",
        [],
    )

    if (
        not isinstance(
            base_hidden,
            list,
        )
        or not isinstance(
            extra_hidden,
            list,
        )
    ):
        raise GenerationError(
            "Layout hiddenPaths must be arrays."
        )

    result[
        "hiddenPaths"
    ] = [
        *base_hidden,
        *extra_hidden,
    ]

    base_options = result.get(
        "controlOptions",
        {},
    )

    extra_options = extra.get(
        "controlOptions",
        {},
    )

    if (
        not isinstance(
            base_options,
            dict,
        )
        or not isinstance(
            extra_options,
            dict,
        )
    ):
        raise GenerationError(
            "Layout controlOptions must be objects."
        )

    result[
        "controlOptions"
    ] = {
        **base_options,
        **extra_options,
    }

    return result


def load_editor_layout(
    schemas_root: Path,
    editor_config: JsonObject,
) -> JsonObject:
    layout_value = (
        editor_config.get(
            "layout"
        )
    )

    if not isinstance(
        layout_value,
        str,
    ):
        raise GenerationError(
            "Profile editor configuration has no layout."
        )

    layout = load_json_object(
        schemas_root
        / layout_value
    )

    extras = editor_config.get(
        "layoutExtras",
        [],
    )

    if not isinstance(
        extras,
        list,
    ):
        raise GenerationError(
            "editor.layoutExtras must be an array."
        )

    for extra_value in extras:
        if not isinstance(
            extra_value,
            str,
        ):
            raise GenerationError(
                "editor.layoutExtras entries must be strings."
            )

        extra = load_json_object(
            schemas_root
            / extra_value
        )

        layout = merge_layout(
            layout,
            extra,
        )

    return layout


def create_authoring_schema(
    *,
    schemas_root: Path,
    profile: JsonObject,
    official_schema: JsonObject,
    editor_config: JsonObject,
) -> tuple[
    JsonObject,
    str | None,
]:
    variant = editor_config.get(
        "variant"
    )

    if variant is None:
        expanded = dereference(
            official_schema,
            official_schema,
        )

        if not isinstance(
            expanded,
            dict,
        ):
            raise GenerationError(
                "Expanded root schema is not an object."
            )

        authoring_schema = expanded

    elif isinstance(
        variant,
        str,
    ):
        authoring_schema = (
            select_variant(
                official_schema,
                variant,
            )
        )

    else:
        raise GenerationError(
            "editor.variant must be a string when present."
        )

    strip_nested_ids(
        authoring_schema
    )

    overlay_config = profile.get(
        "schemaOverlay"
    )

    if overlay_config is not None:
        if not isinstance(
            overlay_config,
            dict,
        ):
            raise GenerationError(
                "schemaOverlay must be an object."
            )

        overlay_value = (
            overlay_config.get(
                "path"
            )
        )

        if not isinstance(
            overlay_value,
            str,
        ):
            raise GenerationError(
                "schemaOverlay.path must be a string."
            )

        overlay = load_json_object(
            schemas_root
            / overlay_value
        )

        # Backend validation may apply the same overlay to each root
        # oneOf branch. The editor schema has already selected or
        # expanded its root, so here the overlay belongs directly on
        # the resulting authoring schema.
        authoring_schema = (
            deep_merge(
                authoring_schema,
                overlay,
            )
        )

    augmenter_ids = (
        editor_config.get(
            "augmenters",
            [],
        )
    )

    if not isinstance(
        augmenter_ids,
        list,
    ):
        raise GenerationError(
            "editor.augmenters must be an array."
        )

    for augmenter_id in augmenter_ids:
        if not isinstance(
            augmenter_id,
            str,
        ):
            raise GenerationError(
                "Editor augmenter IDs must be strings."
            )

        augmenter = (
            EDITOR_AUGMENTERS.get(
                augmenter_id
            )
        )

        if augmenter is None:
            raise GenerationError(
                "Unknown editor augmenter: "
                f"{augmenter_id}"
            )

        augmenter(
            authoring_schema,
            schemas_root,
            profile,
        )

    return (
        authoring_schema,
        variant,
    )


def build_ui_schema(
    *,
    authoring_schema: JsonObject,
    layout_config: JsonObject,
    editor_config: JsonObject,
) -> tuple[
    JsonObject,
    list[str],
]:
    sections = layout_config.get(
        "sections"
    )

    if not isinstance(
        sections,
        list,
    ):
        raise GenerationError(
            "Layout sections must be an array."
        )

    hidden_values = (
        layout_config.get(
            "hiddenPaths",
            [],
        )
    )

    if not isinstance(
        hidden_values,
        list,
    ):
        raise GenerationError(
            "Layout hiddenPaths must be an array."
        )

    hidden_paths = {
        value

        for value
        in hidden_values

        if isinstance(
            value,
            str,
        )
    }

    control_options = (
        layout_config.get(
            "controlOptions",
            {},
        )
    )

    if not isinstance(
        control_options,
        dict,
    ):
        raise GenerationError(
            "Layout controlOptions must be an object."
        )

    categories: list[
        JsonObject
    ] = []

    configured_paths: set[
        str
    ] = set()

    missing_paths: list[
        str
    ] = []

    for section in sections:
        if not isinstance(
            section,
            dict,
        ):
            raise GenerationError(
                "Layout section must be an object."
            )

        section_id = section.get(
            "id"
        )

        section_label = section.get(
            "label"
        )

        paths = section.get(
            "paths"
        )

        if (
            not isinstance(
                section_id,
                str,
            )
            or not isinstance(
                section_label,
                str,
            )
            or not isinstance(
                paths,
                list,
            )
        ):
            raise GenerationError(
                "Invalid section configuration."
            )

        controls: list[
            JsonObject
        ] = []

        for value in paths:
            if not isinstance(
                value,
                str,
            ):
                raise GenerationError(
                    "Section paths must be strings."
                )

            configured_paths.add(
                value
            )

            if value in hidden_paths:
                continue

            control = make_control(
                authoring_schema,
                value,
                control_options,
            )

            if control is None:
                missing_paths.append(
                    value
                )

                continue

            controls.append(
                control
            )

        if controls:
            categories.append(
                {
                    "type":
                        "Category",

                    "id":
                        section_id,

                    "label":
                        section_label,

                    "elements":
                        controls,
                }
            )

    automatic_root = (
        editor_config.get(
            "autoAdditionalPropertiesFrom"
        )
    )

    automatically_added: list[
        str
    ] = []

    if automatic_root is not None:
        if not isinstance(
            automatic_root,
            str,
        ):
            raise GenerationError(
                "editor.autoAdditionalPropertiesFrom "
                "must be a string when present."
            )

        for property_name in (
            property_names_at_path(
                authoring_schema,
                automatic_root,
            )
        ):
            path = (
                f"{automatic_root}."
                f"{property_name}"
            )

            if (
                path
                in configured_paths
                or path
                in hidden_paths
            ):
                continue

            control = make_control(
                authoring_schema,
                path,
                control_options,
            )

            if control is not None:
                automatically_added.append(
                    path
                )

    if automatically_added:
        controls = [
            control

            for path
            in automatically_added

            if (
                control := make_control(
                    authoring_schema,
                    path,
                    control_options,
                )
            ) is not None
        ]

        categories.append(
            {
                "type":
                    "Category",

                "id":
                    "additional",

                "label":
                    "Additional fields",

                "elements":
                    controls,
            }
        )

    return (
        {
            "type":
                "Categorization",

            "elements":
                categories,
        },
        missing_paths,
    )


def resolve_profile(
    manifest: JsonObject,
    profile_id: str,
) -> JsonObject:
    profiles = manifest.get(
        "profiles"
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise GenerationError(
            "manifest.json has no profiles object."
        )

    profile = profiles.get(
        profile_id
    )

    if not isinstance(
        profile,
        dict,
    ):
        raise GenerationError(
            f"Unknown schema profile: {profile_id}"
        )

    return profile


def generate(
    project_root: Path,
    profile_id: str,
    strict: bool,
) -> None:
    schemas_root = (
        project_root
        / "schemas"
    )

    manifest = load_json_object(
        schemas_root
        / "manifest.json"
    )

    profile = resolve_profile(
        manifest,
        profile_id,
    )

    base_schema_value = (
        profile.get(
            "baseSchema"
        )
    )

    if not isinstance(
        base_schema_value,
        str,
    ):
        raise GenerationError(
            f"{profile_id} has no baseSchema."
        )

    editor_config = profile.get(
        "editor"
    )

    if not isinstance(
        editor_config,
        dict,
    ):
        raise GenerationError(
            f"{profile_id} has no editor configuration."
        )

    official_path = (
        schemas_root
        / base_schema_value
    )

    official_schema = (
        load_json_object(
            official_path
        )
    )

    layout_config = (
        load_editor_layout(
            schemas_root,
            editor_config,
        )
    )

    (
        authoring_schema,
        variant,
    ) = create_authoring_schema(
        schemas_root=schemas_root,
        profile=profile,
        official_schema=official_schema,
        editor_config=editor_config,
    )

    authoring_schema[
        "$schema"
    ] = official_schema.get(
        "$schema"
    )

    authoring_schema[
        "$id"
    ] = (
        "https://vulniverse.invalid/"
        f"schemas/{profile_id}/"
        "authoring.schema.json"
    )

    label = profile.get(
        "label"
    )

    if not isinstance(
        label,
        str,
    ):
        label = profile_id

    variant_suffix = (
        f" {variant}"
        if variant
        else ""
    )

    authoring_schema[
        "title"
    ] = (
        f"Vulniverse {label}"
        f"{variant_suffix} "
        "authoring schema"
    )

    (
        ui_schema,
        missing_paths,
    ) = build_ui_schema(
        authoring_schema=authoring_schema,
        layout_config=layout_config,
        editor_config=editor_config,
    )

    field_catalog = (
        collect_field_catalog(
            authoring_schema
        )
    )

    frontend_directory = (
        project_root
        / "frontend"
        / "src"
        / "generated"
        / "schemas"
        / profile_id
    )

    write_json(
        frontend_directory
        / "authoring.schema.json",
        authoring_schema,
    )

    write_json(
        frontend_directory
        / "ui.schema.json",
        ui_schema,
    )

    write_json(
        frontend_directory
        / "field-paths.json",
        frontend_path_catalog(
            field_catalog
        ),
    )

    console.info(
        f"Generated editor schema for {profile_id}."
    )

    if missing_paths:
        console.warning(
            "Configured layout paths were not present:"
        )

        for path in sorted(
            set(
                missing_paths
            )
        ):
            console.warning(
                f"  - {path}"
            )

        if strict:
            raise GenerationError(
                "Schema generation found missing paths."
            )


def parse_arguments() -> argparse.Namespace:
    project_root = (
        Path(__file__)
        .resolve()
        .parents[1]
    )

    parser = argparse.ArgumentParser(
        description=(
            "Generate Vulniverse editor schemas "
            "from a configured schema profile."
        )
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help=(
            "Vulniverse repository root."
        ),
    )

    parser.add_argument(
        "--profile",
        default=None,
        help=(
            "Profile ID from schemas/manifest.json. "
            "Defaults to currentProfiles.cve."
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Fail if configured layout paths "
            "do not exist in the schema."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    project_root = (
        args.project_root
        .expanduser()
        .resolve()
    )

    if args.profile:
        profile_id = (
            args.profile
        )

    else:
        manifest = load_json_object(
            project_root
            / "schemas"
            / "manifest.json"
        )

        current_profiles = (
            manifest.get(
                "currentProfiles"
            )
        )

        if not isinstance(
            current_profiles,
            dict,
        ):
            raise GenerationError(
                "No currentProfiles object in manifest."
            )

        profile_id = (
            current_profiles.get(
                "cve"
            )
        )

        if not isinstance(
            profile_id,
            str,
        ):
            raise GenerationError(
                "No current CVE profile configured."
            )

    generate(
        project_root,
        profile_id,
        args.strict,
    )

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(
            main()
        )

    except ScriptError as error:
        console.error(
            str(error)
        )

        raise SystemExit(2)
