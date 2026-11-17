from __future__ import annotations

from typing import Any

from flask import request
from flask_login import current_user

from ..auth.permissions import admin_required, multiuser_only
from ..extensions import db
from ..models import User
from ..services.accounts import (
    delete_account,
    deletion_problem,
    generate_password,
    set_password,
)
from . import api_bp


def _serialize(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "isAdmin": user.is_admin,
        "isActive": user.is_active,
        "createdAt": user.created_at.isoformat(),
    }


@api_bp.get("/admin/users")
@multiuser_only
@admin_required
def list_users() -> tuple[dict, int]:
    users = User.query.order_by(User.created_at.asc()).all()

    return {"users": [_serialize(user) for user in users]}, 200


@api_bp.put("/admin/users/<int:user_id>")
@multiuser_only
@admin_required
def update_user(user_id: int) -> tuple[dict, int]:
    user = db.session.get(User, user_id)

    if user is None:
        return {"message": "User not found."}, 404

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"message": "A JSON object is required."}, 400

    if user.id == current_user.id and (
        payload.get("isAdmin") is False or payload.get("isActive") is False
    ):
        return {
            "message": "You cannot remove your own admin access or deactivate yourself.",
        }, 400

    if "isAdmin" in payload:
        if not isinstance(payload["isAdmin"], bool):
            return {"message": "'isAdmin' must be a boolean."}, 400

        user.is_admin = payload["isAdmin"]

    if "isActive" in payload:
        if not isinstance(payload["isActive"], bool):
            return {"message": "'isActive' must be a boolean."}, 400

        user.is_active = payload["isActive"]

    db.session.commit()

    return _serialize(user), 200


@api_bp.post("/admin/users/<int:user_id>/reset-password")
@multiuser_only
@admin_required
def reset_password(user_id: int) -> tuple[dict, int]:
    """Give the user a new random password, shown only in this response,
    for the admin to pass on."""
    user = db.session.get(User, user_id)

    if user is None:
        return {"message": "User not found."}, 404

    password = generate_password()
    set_password(user, password)

    return {"password": password}, 200


@api_bp.delete("/admin/users/<int:user_id>")
@multiuser_only
@admin_required
def delete_user(user_id: int) -> tuple[dict, int]:
    """Delete an account (see services/accounts.py for what goes with it).
    Your own is deleted from your account page, with your password."""
    user = db.session.get(User, user_id)

    if user is None:
        return {"message": "User not found."}, 404

    if user.id == current_user.id:
        return {"message": "Delete your own account from your account page."}, 400

    problem = deletion_problem(user)
    if problem:
        return {"message": problem}, 409

    delete_account(user)

    return {"id": user_id}, 200
