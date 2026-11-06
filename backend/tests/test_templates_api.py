from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from vulniverse_api import api as api_module
from vulniverse_api.extensions import db
from vulniverse_api.models import Template


def insert_template(
    app,
    owner_id: int,
    name: str = "Acme Widget",
    profile: str = "cve-5.2.0",
) -> int:
    """Inserts a template directly via the ORM rather than through an
    authenticated HTTP request — see insert_record's docstring in
    test_records_api.py for why cross-user visibility tests need this
    instead of two different logged-in test_client()s each making a
    real request within one test.
    """
    with app.app_context():
        template = Template(
            profile=profile,
            name=name,
            fields=[
                {"path": "containers.cna.affected.0.vendor", "value": "Acme"},
            ],
            created_by_id=owner_id,
        )
        db.session.add(template)
        db.session.commit()
        db.session.refresh(template)
        return template.id


def create_template(
    client: FlaskClient,
    name: str = "Acme Widget",
    fields: list[dict] | None = None,
    profile: str = "cve-5.2.0",
):
    return client.post(
        "/api/v1/templates",
        json={
            "profile": profile,
            "name": name,
            "fields": fields if fields is not None else [
                {"path": "containers.cna.affected.0.vendor", "value": "Acme"},
                {"path": "containers.cna.affected.0.product", "value": "Widget"},
            ],
        },
    )


def list_templates(
    client: FlaskClient,
    profile: str = "cve-5.2.0",
):
    return client.get(f"/api/v1/templates?profile={profile}")


def test_create_template_returns_201_with_id(client: FlaskClient) -> None:
    response = create_template(client)

    assert response.status_code == 201

    body = response.get_json()

    assert body["profile"] == "cve-5.2.0"
    assert body["name"] == "Acme Widget"
    assert body["fields"] == [
        {"path": "containers.cna.affected.0.vendor", "value": "Acme"},
        {"path": "containers.cna.affected.0.product", "value": "Widget"},
    ]
    assert isinstance(body["id"], int)


def test_create_template_requires_profile(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={
            "name": "Acme Widget",
            "fields": [{"path": "vendor", "value": "Acme"}],
        },
    )

    assert response.status_code == 400


def test_create_template_rejects_unknown_profile(client: FlaskClient) -> None:
    response = create_template(client, profile="not-a-real-profile")

    assert response.status_code == 400


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
        json={"profile": "cve-5.2.0", "name": "Bad", "fields": "not a list"},
    )

    assert response.status_code == 400


def test_create_template_rejects_field_without_path(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={"profile": "cve-5.2.0", "name": "Bad", "fields": [{"value": "Acme"}]},
    )

    assert response.status_code == 400


def test_create_template_rejects_field_without_value(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/templates",
        json={"profile": "cve-5.2.0", "name": "Bad", "fields": [{"path": "vendor"}]},
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


def test_list_templates_requires_profile(client: FlaskClient) -> None:
    response = client.get("/api/v1/templates")

    assert response.status_code == 400


def test_list_templates_orders_by_name(client: FlaskClient) -> None:
    create_template(client, name="Zebra Tool")
    create_template(client, name="Acme Widget")

    response = list_templates(client)
    names = [template["name"] for template in response.get_json()["templates"]]

    assert names == ["Acme Widget", "Zebra Tool"]


def test_list_templates_filters_by_profile(client: FlaskClient) -> None:
    create_template(client, name="CVE Template", profile="cve-5.2.0")
    create_template(client, name="GCVE Template", profile="gcve-bcp-05-1.7")

    cve_names = [
        template["name"]
        for template in list_templates(client, profile="cve-5.2.0").get_json()["templates"]
    ]
    gcve_names = [
        template["name"]
        for template in list_templates(client, profile="gcve-bcp-05-1.7").get_json()["templates"]
    ]

    assert cve_names == ["CVE Template"]
    assert gcve_names == ["GCVE Template"]


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

    listed = list_templates(client).get_json()["templates"]

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

    remaining = list_templates(client).get_json()["templates"]

    assert remaining == []


def test_delete_unknown_template_returns_404(client: FlaskClient) -> None:
    response = client.delete("/api/v1/templates/99999")

    assert response.status_code == 404


def test_other_users_templates_are_hidden_from_list(
    app,
    test_user,
    other_client: FlaskClient,
) -> None:
    insert_template(app, test_user.id)

    assert list_templates(other_client).get_json()["templates"] == []


def test_other_user_cannot_update_someones_template(
    app,
    test_user,
    other_client: FlaskClient,
) -> None:
    template_id = insert_template(app, test_user.id)

    response = other_client.put(
        f"/api/v1/templates/{template_id}",
        json={"name": "Hijacked", "fields": []},
    )

    assert response.status_code == 404


def test_other_user_cannot_delete_someones_template(
    app,
    test_user,
    other_client: FlaskClient,
) -> None:
    template_id = insert_template(app, test_user.id)

    response = other_client.delete(f"/api/v1/templates/{template_id}")

    assert response.status_code == 404


def test_admin_does_not_see_other_users_templates_in_list(
    app,
    test_user,
    admin_client: FlaskClient,
) -> None:
    insert_template(app, test_user.id)

    assert list_templates(admin_client).get_json()["templates"] == []


def test_admin_cannot_update_someone_elses_template(
    app,
    test_user,
    admin_client: FlaskClient,
) -> None:
    template_id = insert_template(app, test_user.id)

    response = admin_client.put(
        f"/api/v1/templates/{template_id}",
        json={"name": "Renamed by admin", "fields": []},
    )

    assert response.status_code == 404


def test_disabled_panel_404s_every_route(
    client: FlaskClient,
    app,
    test_user,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_load_app_config = api_module.load_app_config

    def patched() -> dict:
        config = dict(real_load_app_config())
        config["panels"] = {**config["panels"], "templates": False}
        return config

    monkeypatch.setattr(api_module, "load_app_config", patched)

    template_id = insert_template(app, test_user.id)

    assert client.get("/api/v1/templates?profile=cve-5.2.0").status_code == 404
    assert create_template(client).status_code == 404
    assert client.put(
        f"/api/v1/templates/{template_id}",
        json={"name": "x", "fields": []},
    ).status_code == 404
    assert client.delete(f"/api/v1/templates/{template_id}").status_code == 404
