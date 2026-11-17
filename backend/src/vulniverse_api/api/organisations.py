"""Organisations and their members, managed by instance admins.

Organisation admins managing their own members is phase 2; until then
the "admin" role is stored but grants nothing beyond "editor". Deleting
an organisation isn't offered: its records would need a new home first.
"""

from __future__ import annotations

import re
from typing import Any

from flask import request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..auth.permissions import admin_required, multiuser_only
from ..extensions import db
from ..models import MEMBERSHIP_ROLES, Membership, Organisation, User
from . import api_bp

type ApiResponse = tuple[dict[str, Any], int]

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_NAME = 128
MAX_SLUG = 64


def slug_from(name: str) -> str:
    """'Acme Security, Inc.' -> 'acme-security-inc'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:MAX_SLUG].strip("-")


def organisation_response(organisation: Organisation) -> dict[str, Any]:
    members = Membership.query.filter_by(organisation_id=organisation.id).count()

    return {
        "id": organisation.id,
        "name": organisation.name,
        "slug": organisation.slug,
        "createdAt": organisation.created_at.isoformat(),
        "memberCount": members,
    }


def member_response(membership: Membership) -> dict[str, Any]:
    return {
        "userId": membership.user.id,
        "email": membership.user.email,
        "isActive": membership.user.is_active,
        "role": membership.role,
    }


def read_name_and_slug(
    payload: dict[str, Any],
    *,
    required: bool,
) -> tuple[str | None, str | None, ApiResponse | None]:
    """The cleaned name and slug from a create or rename request (None
    when absent), and an error response if they're invalid."""
    name = payload.get("name")
    slug = payload.get("slug")

    if name is not None or required:
        if not isinstance(name, str) or not name.strip():
            return None, None, ({"message": "A non-empty 'name' is required."}, 400)
        name = name.strip()
        if len(name) > MAX_NAME:
            return (
                None,
                None,
                ({"message": f"'name' can be at most {MAX_NAME} characters."}, 400),
            )

    if slug is not None and (
        not isinstance(slug, str) or not SLUG.match(slug) or len(slug) > MAX_SLUG
    ):
        return (
            None,
            None,
            (
                {
                    "message": "'slug' must be lowercase letters, digits and single hyphens,"
                    f" at most {MAX_SLUG} characters.",
                },
                400,
            ),
        )

    return name, slug, None


def name_taken(name: str, *, exclude_id: int | None = None) -> bool:
    """Names tell organisations apart in the switcher, so they're unique
    too, ignoring case.

    shortcut: checked here, not by a database index, so two requests at
    the same moment could both pass; add an index on lower(name) if
    organisations are ever created by self-service.
    """
    query = Organisation.query.filter(func.lower(Organisation.name) == name.lower())
    if exclude_id is not None:
        query = query.filter(Organisation.id != exclude_id)

    return query.first() is not None


NAME_TAKEN: ApiResponse = (
    {"message": "An organisation with this name already exists."},
    409,
)


def commit_or_slug_conflict() -> ApiResponse | None:
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"message": "An organisation with this slug already exists."}, 409

    return None


@api_bp.get("/admin/organisations")
@multiuser_only
@admin_required
def list_organisations() -> ApiResponse:
    organisations = Organisation.query.order_by(func.lower(Organisation.name)).all()

    return {"organisations": [organisation_response(o) for o in organisations]}, 200


@api_bp.post("/admin/organisations")
@multiuser_only
@admin_required
def create_organisation() -> ApiResponse:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    name, slug, error = read_name_and_slug(payload, required=True)
    if error is not None:
        return error
    assert name is not None  # required=True

    if name_taken(name):
        return NAME_TAKEN

    slug = slug or slug_from(name)
    if not slug:
        return {"message": "Give a 'slug': none can be derived from this name."}, 400

    organisation = Organisation(name=name, slug=slug)
    db.session.add(organisation)

    error = commit_or_slug_conflict()
    if error is not None:
        return error

    return organisation_response(organisation), 201


@api_bp.patch("/admin/organisations/<int:organisation_id>")
@multiuser_only
@admin_required
def update_organisation(organisation_id: int) -> ApiResponse:
    organisation = db.session.get(Organisation, organisation_id)
    if organisation is None:
        return {"message": "Organisation not found."}, 404

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    name, slug, error = read_name_and_slug(payload, required=False)
    if error is not None:
        return error

    if name is not None:
        if name_taken(name, exclude_id=organisation.id):
            return NAME_TAKEN
        organisation.name = name
    if slug is not None:
        organisation.slug = slug

    error = commit_or_slug_conflict()
    if error is not None:
        return error

    return organisation_response(organisation), 200


@api_bp.get("/admin/organisations/<int:organisation_id>/members")
@multiuser_only
@admin_required
def list_members(organisation_id: int) -> ApiResponse:
    if db.session.get(Organisation, organisation_id) is None:
        return {"message": "Organisation not found."}, 404

    members = (
        Membership.query.filter_by(organisation_id=organisation_id)
        .join(User)
        .order_by(User.email)
        .all()
    )

    return {"members": [member_response(m) for m in members]}, 200


@api_bp.put("/admin/organisations/<int:organisation_id>/members/<int:user_id>")
@multiuser_only
@admin_required
def set_member(organisation_id: int, user_id: int) -> ApiResponse:
    """Add the user to the organisation, or change their role there."""
    if db.session.get(Organisation, organisation_id) is None:
        return {"message": "Organisation not found."}, 404
    if db.session.get(User, user_id) is None:
        return {"message": "User not found."}, 404

    payload = request.get_json(silent=True)
    role = payload.get("role") if isinstance(payload, dict) else None
    if role not in MEMBERSHIP_ROLES:
        return {
            "message": f"'role' must be one of: {', '.join(MEMBERSHIP_ROLES)}."
        }, 400

    membership = Membership.query.filter_by(
        organisation_id=organisation_id,
        user_id=user_id,
    ).first()
    created = membership is None

    if membership is None:
        membership = Membership(organisation_id=organisation_id, user_id=user_id)
        db.session.add(membership)
    membership.role = role

    try:
        db.session.commit()
    except IntegrityError:
        # Added at the same moment by another request.
        db.session.rollback()
        return {"message": "The user was just added; try again."}, 409

    return member_response(membership), 201 if created else 200


@api_bp.delete("/admin/organisations/<int:organisation_id>/members/<int:user_id>")
@multiuser_only
@admin_required
def remove_member(organisation_id: int, user_id: int) -> ApiResponse:
    """The user loses access to the organisation's drafts; the records
    they created stay with the organisation."""
    membership = Membership.query.filter_by(
        organisation_id=organisation_id,
        user_id=user_id,
    ).first()
    if membership is None:
        return {"message": "Membership not found."}, 404

    db.session.delete(membership)
    db.session.commit()

    return {"organisationId": organisation_id, "userId": user_id}, 200
