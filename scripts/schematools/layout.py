"""The UI schema: which fields the editor shows, in which section, how.

A layout file (``schemas/editor/*.layout.json``) lists sections of
dot-separated data paths (``containers.cna.title``)::

    {
      "sections": [{"id": "basics", "label": "Basics", "paths": ["..."]}],
      "hiddenPaths": ["..."],
      "controlOptions": {"<path>": {"label": "...", "width": "medium"}}
    }

Each section becomes a JSON Forms ``Category`` of ``Control`` elements.
``editor.layoutExtras`` add sections to a base layout, and
``editor.autoAdditionalPropertiesFrom`` adds a final "Additional fields"
section for properties the layout does not mention.
"""

import copy
from pathlib import Path
from typing import Any

from .errors import GenerationError
from .files import load_json_object
from .jsontypes import JsonObject, as_dict, require_dict, require_list, require_str, str_list


def schema_for_data_path(schema: JsonObject, data_path: str) -> JsonObject | None:
    """The subschema at ``data_path`` following ``properties``, if it exists."""
    current: Any = schema

    if not data_path:
        return schema

    for part in data_path.split("."):
        current = as_dict(current).get("properties")
        current = current.get(part) if isinstance(current, dict) else None

        if current is None:
            return None

    return current if isinstance(current, dict) else None


def scope_for_data_path(data_path: str) -> str:
    """``a.b`` → ``#/properties/a/properties/b``, escaped as a JSON pointer."""
    tokens = (part.replace("~", "~0").replace("/", "~1") for part in data_path.split("."))
    return "#/" + "/".join(f"properties/{token}" for token in tokens)


def humanize(value: str) -> str:
    """``assignerShortName`` → ``Assigner short name``, for untitled fields."""
    result: list[str] = []

    for index, character in enumerate(value):
        if index > 0 and character.isupper() and not value[index - 1].isupper():
            result.append(" ")
        result.append(character)

    return "".join(result).replace("_", " ").capitalize()


def make_control(
    schema: JsonObject, data_path: str, control_options: JsonObject
) -> JsonObject | None:
    """The JSON Forms control for one field, or None if the path doesn't exist."""
    field_schema = schema_for_data_path(schema, data_path)

    if field_schema is None:
        return None

    title = field_schema.get("title")
    label = title if isinstance(title, str) else humanize(data_path.split(".")[-1])
    control: JsonObject = {
        "type": "Control",
        "scope": scope_for_data_path(data_path),
        "label": label,
    }

    options: JsonObject = {}

    if field_schema.get("type") == "array":
        options.update({"detail": "GENERATED", "showSortButtons": True})

    configured = control_options.get(data_path, {})
    if isinstance(configured, dict):
        options.update(copy.deepcopy(configured))

    # A layout "label" names the control instead of the schema title.
    control["label"] = options.pop("label", label)

    if options:
        control["options"] = options

    return control


def merge_layout(base: JsonObject, extra: JsonObject) -> JsonObject:
    """``base`` with the sections, hidden paths and options of ``extra`` added."""
    result = copy.deepcopy(base)

    for key in ("sections", "hiddenPaths"):
        result[key] = [
            *require_list(result.get(key, []), f"Layout {key}", GenerationError),
            *require_list(extra.get(key, []), f"Layout {key}", GenerationError),
        ]

    result["controlOptions"] = {
        **require_dict(result.get("controlOptions", {}), "Layout controlOptions", GenerationError),
        **require_dict(extra.get("controlOptions", {}), "Layout controlOptions", GenerationError),
    }
    return result


def load_editor_layout(schemas_root: Path, editor_config: JsonObject) -> JsonObject:
    """The profile's layout with its ``layoutExtras`` merged in."""
    path = require_str(
        editor_config.get("layout"), "Profile editor configuration layout", GenerationError
    )
    layout = load_json_object(schemas_root / path)

    for extra in str_list(
        editor_config.get("layoutExtras", []), "editor.layoutExtras", GenerationError
    ):
        layout = merge_layout(layout, load_json_object(schemas_root / extra))

    return layout


def category(category_id: str, label: str, controls: list[JsonObject]) -> JsonObject:
    return {"type": "Category", "id": category_id, "label": label, "elements": controls}


def build_ui_schema(
    authoring_schema: JsonObject, layout: JsonObject, editor_config: JsonObject
) -> tuple[JsonObject, list[str]]:
    """The UI schema, and the layout paths missing from the authoring schema."""
    sections = require_list(layout.get("sections"), "Layout sections", GenerationError)
    hidden_paths = {
        value
        for value in require_list(
            layout.get("hiddenPaths", []), "Layout hiddenPaths", GenerationError
        )
        if isinstance(value, str)
    }
    control_options = require_dict(
        layout.get("controlOptions", {}), "Layout controlOptions", GenerationError
    )

    categories: list[JsonObject] = []
    configured_paths: set[str] = set()
    missing_paths: list[str] = []

    for section in sections:
        section = require_dict(section, "Layout section", GenerationError)
        section_id = require_str(section.get("id"), "Section id", GenerationError)
        label = require_str(section.get("label"), "Section label", GenerationError)
        paths = str_list(section.get("paths"), "Section paths", GenerationError)
        controls = []

        for path in paths:
            configured_paths.add(path)

            if path in hidden_paths:
                continue

            control = make_control(authoring_schema, path, control_options)

            if control is None:
                missing_paths.append(path)
            else:
                controls.append(control)

        if controls:
            categories.append(category(section_id, label, controls))

    additional = additional_controls(
        authoring_schema, editor_config, configured_paths | hidden_paths, control_options
    )
    if additional:
        categories.append(category("additional", "Additional fields", additional))

    return {"type": "Categorization", "elements": categories}, missing_paths


def additional_controls(
    authoring_schema: JsonObject,
    editor_config: JsonObject,
    known_paths: set[str],
    control_options: JsonObject,
) -> list[JsonObject]:
    """Controls for the properties below ``autoAdditionalPropertiesFrom`` that
    the layout neither shows nor hides, so no field is unreachable."""
    root = editor_config.get("autoAdditionalPropertiesFrom")

    if root is None:
        return []

    root = require_str(root, "editor.autoAdditionalPropertiesFrom", GenerationError)
    properties = as_dict(as_dict(schema_for_data_path(authoring_schema, root)).get("properties"))
    controls = []

    for name in sorted(properties):
        path = f"{root}.{name}"

        if path in known_paths:
            continue

        control = make_control(authoring_schema, path, control_options)
        if control is not None:
            controls.append(control)

    return controls
