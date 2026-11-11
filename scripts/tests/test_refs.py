import pytest

from schematools.errors import GenerationError
from schematools.refs import dereference, drop_unused_definitions, strip_nested_ids

CVSS_URL = "https://www.first.org/cvss/cvss-v3.0.json"


def test_local_reference_is_inlined_and_sibling_keywords_win() -> None:
    root = {"definitions": {"id": {"type": "string", "title": "Upstream"}}}
    node = {"$ref": "#/definitions/id", "title": "Local"}

    assert dereference(node, root) == {"type": "string", "title": "Local"}


def test_resource_is_inlined_without_its_own_declarations() -> None:
    cvss = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "id": CVSS_URL,
        "type": "object",
        "properties": {"version": {"$ref": "#/definitions/version"}},
        "definitions": {"version": {"const": "3.0"}},
    }
    root = {"properties": {"cvss": {"$ref": CVSS_URL}}}

    expanded = dereference(root, root, resources={CVSS_URL: cvss})

    # Local refs inside the resource resolve against the resource.
    assert expanded["properties"]["cvss"] == {
        "type": "object",
        "properties": {"version": {"const": "3.0"}},
        "definitions": {"version": {"const": "3.0"}},
    }


def test_unknown_external_reference_is_left_alone() -> None:
    node = {"$ref": "https://example.invalid/schema.json"}

    assert dereference(node, {}) == node


def test_recursive_reference_stays_a_reference() -> None:
    root = {
        "definitions": {
            "branch": {
                "type": "object",
                "properties": {"branches": {"items": {"$ref": "#/definitions/branch"}}},
            }
        }
    }

    expanded = dereference({"$ref": "#/definitions/branch"}, root)

    assert expanded["properties"]["branches"]["items"] == {"$ref": "#/definitions/branch"}


def test_recursion_inside_a_resource_is_an_error() -> None:
    url = "https://example.invalid/tree.json"
    tree = {
        "definitions": {"node": {"items": {"$ref": "#/definitions/node"}}},
        "$ref": "#/definitions/node",
    }

    with pytest.raises(GenerationError, match="inside a schema resource"):
        dereference({"$ref": url}, {}, resources={url: tree})


def test_definitions_are_dropped_only_when_unused() -> None:
    used = {"$defs": {"a": {}}, "definitions": {"b": {}}, "items": {"$ref": "#/$defs/a"}}

    drop_unused_definitions(used)

    assert "$defs" in used
    assert "definitions" not in used


def test_nested_ids_are_stripped_but_the_root_id_stays() -> None:
    schema = {"$id": "root", "properties": {"a": {"$id": "nested", "type": "string"}}}

    strip_nested_ids(schema)

    assert schema == {"$id": "root", "properties": {"a": {"type": "string"}}}


def test_marked_definitions_survive_inlining_and_sibling_titles() -> None:
    from schematools.authoring import DEFINITION_MARKER, mark_definitions

    schema = {
        "$defs": {"id_t": {"type": "string"}},
        "properties": {"ref": {"title": "Own title", "$ref": "#/$defs/id_t"}},
    }

    marked = mark_definitions(schema, ["id_t"])
    expanded = dereference(marked, marked)

    assert expanded["properties"]["ref"] == {
        "type": "string",
        DEFINITION_MARKER: "id_t",
        "title": "Own title",
    }
    # The upstream schema itself is left alone.
    assert DEFINITION_MARKER not in schema["$defs"]["id_t"]

    with pytest.raises(GenerationError, match="no definition named 'missing'"):
        mark_definitions(schema, ["missing"])
