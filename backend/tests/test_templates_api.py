from __future__ import annotations

from flask.testing import FlaskClient


def create_template(
    client: FlaskClient,
    name: str = "Acme Widget",
    fields: list[dict] | None = None,
):
    return client.post(
        "/api/v1/templates",
        json={
            "name": name,
            "fields": fields if fields is not None else [
                {"path": "containers.cna.affected.0.vendor", "value": "Acme"},
                {"path": "containers.cna.affected.0.product", "value": "Widget"},
            ],
        },
    )


def test_create_template_returns_201_with_id(client: FlaskClient) -> None:
    response = create_template(client)

    assert response.status_code == 201

    body = response.get_json()

    assert body["name"] == "Acme Widget"
    assert body["fields"] == [
        {"path": "containers.cna.affected.0.vendor", "value": "Acme"},
        {"path": "containers.cna.affected.0.product", "value": "Widget"},
    ]
    assert isinstance(body["id"], int)


def test_create_template_requires_non_empty_name(client: FlaskClient) -> None:
    response = create_template(client, name="   ")

    assert response.status_code == 400


def test_create_template_requires_a_json_object(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        data="not json",
        content_type="text/plain",
    )

    assert response.status_code == 400


def test_create_template_rejects_non_list_fields(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={"name": "Bad", "fields": "not a list"},
    )

    assert response.status_code == 400


def test_create_template_rejects_field_without_path(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={"name": "Bad", "fields": [{"value": "Acme"}]},
    )

    assert response.status_code == 400


def test_create_template_rejects_field_without_value(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={"name": "Bad", "fields": [{"path": "vendor"}]},
    )

    assert response.status_code == 400


def test_create_template_allows_falsy_values(client: FlaskClient) -> None:
    response = create_template(
        client,
        fields=[
            {"path": "containers.cna.affected.0.defaultStatus", "value": ""},
            {"path": "someBoolean", "value": False},
            {"path": "someNumber", "value": 0},
        ],
    )

    assert response.status_code == 201


def test_list_templates_orders_by_name(client: FlaskClient) -> None:
    create_template(client, name="Zebra Tool")
    create_template(client, name="Acme Widget")

    response = client.get("/api/v1/templates")
    names = [template["name"] for template in response.get_json()["templates"]]

    assert names == ["Acme Widget", "Zebra Tool"]


def test_update_template_changes_name_and_fields(client: FlaskClient) -> None:
    created = create_template(client).get_json()

    response = client.put(
        f"/api/v1/templates/{created['id']}",
        json={
            "name": "Renamed Tool",
            "fields": [{"path": "containers.cna.affected.0.vendor", "value": "NewCo"}],
        },
    )

    assert response.status_code == 200

    body = response.get_json()

    assert body["id"] == created["id"]
    assert body["name"] == "Renamed Tool"
    assert body["fields"] == [
        {"path": "containers.cna.affected.0.vendor", "value": "NewCo"},
    ]

    listed = client.get("/api/v1/templates").get_json()["templates"]

    assert len(listed) == 1
    assert listed[0]["name"] == "Renamed Tool"


def test_update_unknown_template_returns_404(client: FlaskClient) -> None:
    response = client.put(
        "/api/v1/templates/99999",
        json={"name": "Whatever", "fields": []},
    )

    assert response.status_code == 404


def test_update_template_requires_non_empty_name(client: FlaskClient) -> None:
    created = create_template(client).get_json()

    response = client.put(
        f"/api/v1/templates/{created['id']}",
        json={"name": "  ", "fields": []},
    )

    assert response.status_code == 400


def test_update_template_rejects_invalid_fields(client: FlaskClient) -> None:
    created = create_template(client).get_json()

    response = client.put(
        f"/api/v1/templates/{created['id']}",
        json={"name": "Still Acme", "fields": [{"path": "vendor"}]},
    )

    assert response.status_code == 400


def test_delete_template_removes_it(client: FlaskClient) -> None:
    created = create_template(client).get_json()

    response = client.delete(f"/api/v1/templates/{created['id']}")

    assert response.status_code == 200

    remaining = client.get("/api/v1/templates").get_json()["templates"]

    assert remaining == []


def test_delete_unknown_template_returns_404(client: FlaskClient) -> None:
    response = client.delete("/api/v1/templates/99999")

    assert response.status_code == 404
