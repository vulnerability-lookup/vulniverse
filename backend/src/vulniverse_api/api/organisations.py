"""Organisations, their members and invitations.

- Instance admins create organisations (/admin/organisations) and may
  add any existing account to one.
- An organisation's own admins (and instance admins) manage its name,
  members and invitation links (/organisations/<id>/...).
- Anyone with a valid invitation link joins with its role
  (/invitations/<token>); an organisation always keeps one admin.

Instance admins can move an organisation's records to another one, and
delete an organisation: an empty one, or one whose records are all
drafts never sent to CVE or VL (published ones must be moved).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from flask import request, session
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..auth.organisations import SESSION_KEY, can_manage_organisation, is_member
from ..auth.permissions import admin_required, multiuser_only
from ..extensions import db
from ..models import (
    MEMBERSHIP_ROLES,
    CnaPublication,
    Invitation,
    Membership,
    Organisation,
    User,
    VulnerabilityRecord,
)
from ..services.invitations import (
    accept_invitation,
    create_invitation,
    find_invitation,
    invitation_state,
)
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
    records = VulnerabilityRecord.query.filter_by(
        organisation_id=organisation.id
    ).count()

    return {
        "id": organisation.id,
        "name": organisation.name,
        "slug": organisation.slug,
        "createdAt": organisation.created_at.isoformat(),
        "memberCount": members,
        # Only an organisation without records can be deleted.
        "recordCount": records,
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


@api_bp.delete("/admin/organisations/<int:organisation_id>")
@multiuser_only
@admin_required
def delete_organisation(organisation_id: int) -> ApiResponse:
    """Delete an organisation; its memberships and invitations go with it,
    the accounts stay, and whoever had it as their current organisation
    falls back to their next one.

    With records it needs {"force": true, "confirmName": <its name>}, and
    even then only drafts that never went to CVE or VL are deleted with it:
    published records live on elsewhere (CVE.org, Vulnerability-Lookup),
    so losing the copy here would leave them without anyone able to update
    or reject them. Those must be moved instead (move-records).
    """
    organisation = db.session.get(Organisation, organisation_id)
    if organisation is None:
        return {"message": "Organisation not found."}, 404

    payload = request.get_json(silent=True)
    payload = payload if isinstance(payload, dict) else {}
    records = VulnerabilityRecord.query.filter_by(organisation_id=organisation_id)
    count = records.count()

    if count and payload.get("force") is not True:
        return {
            "message": f"{organisation.name} still has {count} record(s);"
            " move them, or delete it with its records.",
        }, 409

    if count:
        if payload.get("confirmName") != organisation.name:
            return {"message": "Type the organisation's name to confirm."}, 400

        kept = records.filter(
            (VulnerabilityRecord.is_draft.is_(False))
            | VulnerabilityRecord.id.in_(db.session.query(CnaPublication.record_id)),
        ).count()
        if kept:
            return {
                "message": f"{kept} of its {count} records"
                f" {'is' if kept == 1 else 'are'} published or went to CVE or"
                " Vulnerability-Lookup; move the records to another"
                " organisation instead of deleting them.",
            }, 409

        records.delete(synchronize_session=False)

    Invitation.query.filter_by(organisation_id=organisation_id).delete()
    Membership.query.filter_by(organisation_id=organisation_id).delete()
    db.session.delete(organisation)
    db.session.commit()

    return {"id": organisation_id, "deletedRecords": count}, 200


@api_bp.post("/admin/organisations/<int:organisation_id>/move-records")
@multiuser_only
@admin_required
def move_records(organisation_id: int) -> ApiResponse:
    """Move all of an organisation's records to another one, e.g. to merge
    two organisations or before deleting one. All or nothing: if the
    target already has a record with one of the IDs (unique per
    organisation), nothing moves and the clashing IDs are listed."""
    source = db.session.get(Organisation, organisation_id)
    if source is None:
        return {"message": "Organisation not found."}, 404

    payload = request.get_json(silent=True)
    target_id = (
        payload.get("targetOrganisationId") if isinstance(payload, dict) else None
    )
    if not isinstance(target_id, int) or isinstance(target_id, bool):
        return {"message": "An integer 'targetOrganisationId' is required."}, 400
    if target_id == organisation_id:
        return {
            "message": "Choose a different organisation to move the records to."
        }, 400
    target = db.session.get(Organisation, target_id)
    if target is None:
        return {"message": "Target organisation not found."}, 404

    target_ids = (
        db.session.query(func.lower(VulnerabilityRecord.identifier))
        .filter(
            VulnerabilityRecord.organisation_id == target_id,
            VulnerabilityRecord.identifier.is_not(None),
        )
        .scalar_subquery()
    )
    clashes = sorted(
        identifier
        for (identifier,) in db.session.query(VulnerabilityRecord.identifier).filter(
            VulnerabilityRecord.organisation_id == organisation_id,
            func.lower(VulnerabilityRecord.identifier).in_(target_ids),
        )
    )
    if clashes:
        return {
            "message": f"{target.name} already has records with these IDs, so"
            f" nothing was moved: {', '.join(clashes)}.",
            "clashes": clashes,
        }, 409

    moved = VulnerabilityRecord.query.filter_by(organisation_id=organisation_id).update(
        {"organisation_id": target_id},
        synchronize_session=False,
    )
    try:
        db.session.commit()
    except IntegrityError:
        # A clashing record was created in the target meanwhile.
        db.session.rollback()
        return {"message": "An ID now exists in both; try again."}, 409

    return {"moved": moved, "targetOrganisationId": target_id}, 200


def managed_organisation(organisation_id: int) -> Organisation | ApiResponse:
    """The organisation if the current user may manage it, else the error:
    404 if it doesn't exist, 403 if they may not."""
    organisation = db.session.get(Organisation, organisation_id)
    if organisation is None:
        return {"message": "Organisation not found."}, 404
    if not can_manage_organisation(current_user, organisation_id):
        return {"message": "Only the organisation's admins can do this."}, 403

    return organisation


def admin_count(organisation_id: int) -> int:
    return Membership.query.filter_by(
        organisation_id=organisation_id, role="admin"
    ).count()


LAST_ADMIN: ApiResponse = (
    {
        "message": "An organisation needs at least one admin."
        " Make someone else an admin first.",
    },
    409,
)


@api_bp.get("/organisations/<int:organisation_id>")
@multiuser_only
def get_organisation(organisation_id: int) -> ApiResponse:
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    return organisation_response(organisation), 200


@api_bp.patch("/organisations/<int:organisation_id>")
@multiuser_only
def update_organisation(organisation_id: int) -> ApiResponse:
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

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


@api_bp.get("/organisations/<int:organisation_id>/members")
@multiuser_only
def list_members(organisation_id: int) -> ApiResponse:
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    members = (
        Membership.query.filter_by(organisation_id=organisation_id)
        .join(User)
        .order_by(User.email)
        .all()
    )

    return {"members": [member_response(m) for m in members]}, 200


@api_bp.put("/organisations/<int:organisation_id>/members/<int:user_id>")
@multiuser_only
def set_member(organisation_id: int, user_id: int) -> ApiResponse:
    """Change a member's role. Instance admins may also add any existing
    account this way; organisation admins invite with a link instead,
    so they never see the instance's list of accounts."""
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation
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
        if not current_user.is_admin:
            return {"message": "Invite new members with an invitation link."}, 403
        membership = Membership(organisation_id=organisation_id, user_id=user_id)
        db.session.add(membership)
    elif (
        membership.role == "admin"
        and role != "admin"
        and admin_count(organisation_id) == 1
    ):
        return LAST_ADMIN

    membership.role = role

    try:
        db.session.commit()
    except IntegrityError:
        # Added at the same moment by another request.
        db.session.rollback()
        return {"message": "The user was just added; try again."}, 409

    return member_response(membership), 201 if created else 200


@api_bp.delete("/organisations/<int:organisation_id>/members/<int:user_id>")
@multiuser_only
def remove_member(organisation_id: int, user_id: int) -> ApiResponse:
    """The user loses access to the organisation's drafts; the records
    they created stay with the organisation."""
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    membership = Membership.query.filter_by(
        organisation_id=organisation_id,
        user_id=user_id,
    ).first()
    if membership is None:
        return {"message": "Membership not found."}, 404
    if membership.role == "admin" and admin_count(organisation_id) == 1:
        return LAST_ADMIN

    db.session.delete(membership)
    db.session.commit()

    return {"organisationId": organisation_id, "userId": user_id}, 200


# --- Invitations -----------------------------------------------------------


def invitation_response(invitation: Invitation) -> dict[str, Any]:
    return {
        "id": invitation.id,
        "role": invitation.role,
        "state": invitation_state(invitation),
        "createdAt": invitation.created_at.isoformat(),
        "expiresAt": invitation.expires_at.isoformat(),
        "createdBy": invitation.created_by.email if invitation.created_by else None,
        "acceptedBy": invitation.accepted_by.email if invitation.accepted_by else None,
    }


@api_bp.get("/organisations/<int:organisation_id>/invitations")
@multiuser_only
def list_invitations(organisation_id: int) -> ApiResponse:
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    invitations = (
        Invitation.query.filter_by(organisation_id=organisation_id)
        .order_by(Invitation.created_at.desc(), Invitation.id.desc())
        .all()
    )

    return {"invitations": [invitation_response(i) for i in invitations]}, 200


@api_bp.post("/organisations/<int:organisation_id>/invitations")
@multiuser_only
def create_organisation_invitation(organisation_id: int) -> ApiResponse:
    """A new invitation link's token is in this response only."""
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    payload = request.get_json(silent=True)
    role = payload.get("role") if isinstance(payload, dict) else None
    if role not in MEMBERSHIP_ROLES:
        return {
            "message": f"'role' must be one of: {', '.join(MEMBERSHIP_ROLES)}."
        }, 400

    invitation, token = create_invitation(organisation, role, current_user)

    return {**invitation_response(invitation), "token": token}, 201


@api_bp.delete("/organisations/<int:organisation_id>/invitations/<int:invitation_id>")
@multiuser_only
def revoke_invitation(organisation_id: int, invitation_id: int) -> ApiResponse:
    organisation = managed_organisation(organisation_id)
    if isinstance(organisation, tuple):
        return organisation

    invitation = db.session.get(Invitation, invitation_id)
    if invitation is None or invitation.organisation_id != organisation_id:
        return {"message": "Invitation not found."}, 404

    if invitation_state(invitation) == "valid":
        invitation.revoked_at = datetime.now(UTC)
        db.session.commit()

    return invitation_response(invitation), 200


@api_bp.get("/invitations/<token>")
@multiuser_only
def invitation_info(token: str) -> ApiResponse:
    """What an invitation link offers, for its landing page; needs no
    login, the token itself is the secret."""
    invitation = find_invitation(token)
    if invitation is None:
        return {"message": "This invitation link isn't valid."}, 404

    return {
        "organisation": invitation.organisation.name,
        "role": invitation.role,
        "state": invitation_state(invitation),
    }, 200


@api_bp.post("/invitations/<token>/accept")
@multiuser_only
def accept_organisation_invitation(token: str) -> ApiResponse:
    """Join the invitation's organisation, which becomes the current one."""
    invitation = find_invitation(token)
    error = invitation_error(invitation)
    if error is not None:
        return error
    assert invitation is not None

    if is_member(current_user, invitation.organisation_id):
        return {"message": "You're already a member of this organisation."}, 409

    membership = accept_invitation(invitation, current_user)
    session[SESSION_KEY] = membership.organisation_id

    return {"organisationId": membership.organisation_id, "role": membership.role}, 200


def invitation_error(invitation: Invitation | None) -> ApiResponse | None:
    """Why the invitation can't be used, or None if it can."""
    if invitation is None:
        return {"message": "This invitation link isn't valid."}, 404

    state = invitation_state(invitation)
    if state != "valid":
        return {"message": f"This invitation has been {state}; ask for a new one."}, 410

    return None
