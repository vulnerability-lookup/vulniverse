from __future__ import annotations

import hmac

from flask import current_app

from ..extensions import db, login_manager
from ..models import User
from .local_user import get_local_user


def is_local_mode() -> bool:
    return current_app.config["VULNIVERSE_MODE"] == "local"


def init_auth() -> None:
    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if is_local_mode():
            return get_local_user()

        # "<id>:<session_token>" (User.get_id); anything else, such as a
        # session from before session tokens, is logged out.
        user_part, _, token = user_id.partition(":")
        if not user_part.isdigit() or not token:
            return None

        # populate_existing=True: is_admin/is_active/session_token can
        # change between two requests of the same session; a stale
        # identity-mapped User would hide that.
        user = db.session.get(User, int(user_part), populate_existing=True)
        if user is None or not hmac.compare_digest(user.session_token, token):
            return None

        return user

    @login_manager.request_loader
    def load_user_from_request(request) -> User | None:
        if is_local_mode():
            return get_local_user()

        return None
