"""Invitation links: an organisation's admins create, list and revoke
them (/organisations/<id>/invitations); anyone with a valid link sees
what it offers and joins with its role (/invitations/<token>). Accounts
registering with one go through api/auth.py's register(), which uses
invitation_error() from here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import request, session
from flask_login import current_user

from ..auth.organisations import SESSION_KEY, is_member
from ..auth.permissions import multiuser_only
from ..extensions import db
from ..models import MEMBERSHIP_ROLES, Invitation
from ..services.invitations import (
    accept_invitation,
    create_invitation,
    find_invitation,
    invitation_state,
)
from . import api_bp
from .organisations import ApiResponse, managed_organisation


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
