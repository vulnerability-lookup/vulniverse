"""field-paths.json: every scalar field of a profile, for path autocomplete
in the Templates panel."""

from .jsontypes import JsonObject

CONTAINER_TYPES = ("object", "array", "unknown")


def field_type(schema: JsonObject) -> str:
    """The declared type, or a guess from the schema's shape."""
    declared = schema.get("type")

    if isinstance(declared, str):
        return declared
    if "enum" in schema:
        return "string"
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return "unknown"


def collect_field_catalog(schema: JsonObject, path: str = "") -> list[JsonObject]:
    """Path, title and type of every field below ``schema``; fields inside
    array items get a ``[]`` path suffix (``affected[].package``)."""
    properties = schema.get("properties")

    if not isinstance(properties, dict):
        return []

    fields: list[JsonObject] = []

    for name, child in properties.items():
        if not isinstance(child, dict):
            continue

        child_path = f"{path}.{name}" if path else name
        kind = field_type(child)
        fields.append({"path": child_path, "title": child.get("title"), "type": kind})

        if kind == "object":
            fields.extend(collect_field_catalog(child, child_path))
        elif kind == "array":
            items = child.get("items")
            if isinstance(items, dict) and (items.get("type") == "object" or "properties" in items):
                fields.extend(collect_field_catalog(items, child_path + "[]"))

    return fields


def frontend_path_catalog(schema: JsonObject) -> list[JsonObject]:
    """The scalar fields: the ones a template can set."""
    return [
        field for field in collect_field_catalog(schema) if field["type"] not in CONTAINER_TYPES
    ]
