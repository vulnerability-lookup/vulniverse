from schematools.layout import build_ui_schema, humanize, make_control, scope_for_data_path

SCHEMA = {
    "properties": {
        "containers": {
            "properties": {
                "cna": {
                    "properties": {
                        "title": {"type": "string", "title": "Title"},
                        "affected": {"type": "array"},
                        "assignerShortName": {"type": "string"},
                        "x_extra": {"type": "string"},
                    }
                }
            }
        },
        "a/b~c": {"type": "string"},
    }
}


def test_scope_escapes_json_pointer_characters() -> None:
    assert scope_for_data_path("a/b~c") == "#/properties/a~1b~0c"
    assert scope_for_data_path("containers.cna") == "#/properties/containers/properties/cna"


def test_humanize() -> None:
    assert humanize("assignerShortName") == "Assigner short name"
    assert humanize("database_specific") == "Database specific"


def test_control_label_comes_from_layout_then_title_then_name() -> None:
    options = {"containers.cna.title": {"label": "Headline", "wrap": True}}

    assert make_control(SCHEMA, "containers.cna.title", options) == {
        "type": "Control",
        "scope": "#/properties/containers/properties/cna/properties/title",
        "label": "Headline",
        "options": {"wrap": True},
    }
    assert make_control(SCHEMA, "containers.cna.title", {})["label"] == "Title"  # type: ignore[index]
    control = make_control(SCHEMA, "containers.cna.assignerShortName", {})
    assert control is not None and control["label"] == "Assigner short name"


def test_array_controls_get_detail_options() -> None:
    control = make_control(SCHEMA, "containers.cna.affected", {})

    assert control is not None
    assert control["options"] == {"detail": "GENERATED", "showSortButtons": True}


def test_missing_path_has_no_control() -> None:
    assert make_control(SCHEMA, "containers.cna.nope", {}) is None


def test_ui_schema_sections_hidden_missing_and_additional_fields() -> None:
    layout = {
        "sections": [
            {"id": "basics", "label": "Basics", "paths": ["containers.cna.title", "nope"]},
            {"id": "empty", "label": "Empty", "paths": ["containers.cna.affected"]},
        ],
        "hiddenPaths": ["containers.cna.affected"],
    }
    editor = {"autoAdditionalPropertiesFrom": "containers.cna"}

    ui_schema, missing = build_ui_schema(SCHEMA, layout, editor)

    assert missing == ["nope"]
    categories = ui_schema["elements"]
    # The "empty" section only had a hidden path, so it is left out.
    assert [category["id"] for category in categories] == ["basics", "additional"]
    assert [control["label"] for control in categories[1]["elements"]] == [
        "Assigner short name",
        "X extra",
    ]
