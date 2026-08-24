from __future__ import annotations

from flask import request

from ..extensions import db
from ..models import Template
from . import api_bp


def _validate_fields(
    fields: object,
) -> str | None:
    if not isinstance(fields, list):
        return "'fields' must be a list."

    for entry in fields:
        if not isinstance(entry, dict):
            return "Each field entry must be an object."

        path = entry.get("path")

        if not isinstance(path, str) or not path.strip():
            return "Each field entry needs a non-empty 'path' string."

        if "value" not in entry:
            return "Each field entry needs a 'value'."

    return None


def _serialize(
    template: Template,
) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "fields": template.fields,
    }


@api_bp.get("/templates")
def list_templates() -> tuple[dict, int]:
    templates = Template.query.order_by(
        Template.name.asc(),
    ).all()

    return {
        "templates": [_serialize(template) for template in templates],
    }, 200


@api_bp.post("/templates")
def create_template() -> tuple[dict, int]:
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    name = payload.get("name")

    if not isinstance(name, str) or not name.strip():
        return {"message": "A non-empty 'name' is required."}, 400

    fields = payload.get("fields")
    error = _validate_fields(fields)

    if error:
        return {"message": error}, 400

    template = Template(
        name=name.strip(),
        fields=fields,
    )

    db.session.add(template)
    db.session.commit()

    return _serialize(template), 201


@api_bp.put("/templates/<int:template_id>")
def update_template(
    template_id: int,
) -> tuple[dict, int]:
    template = db.session.get(Template, template_id)

    if template is None:
        return {"message": "Template not found."}, 404

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    name = payload.get("name")

    if not isinstance(name, str) or not name.strip():
        return {"message": "A non-empty 'name' is required."}, 400

    fields = payload.get("fields")
    error = _validate_fields(fields)

    if error:
        return {"message": error}, 400

    assert isinstance(fields, list)

    template.name = name.strip()
    template.fields = fields

    db.session.commit()

    return _serialize(template), 200


@api_bp.delete("/templates/<int:template_id>")
def delete_template(
    template_id: int,
) -> tuple[dict, int]:
    template = db.session.get(Template, template_id)

    if template is None:
        return {"message": "Template not found."}, 404

    db.session.delete(template)
    db.session.commit()

    return {"id": template_id}, 200
