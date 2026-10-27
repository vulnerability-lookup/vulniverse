from __future__ import annotations

from flask import current_app

from ..extensions import db, login_manager
from ..models import User
from .local_user import get_local_user


def is_local_mode() -> bool:
    return (
        current_app.config["VULNIVERSE_MODE"]
        == "local"
    )


def init_auth() -> None:
    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        if is_local_mode():
            return get_local_user()

        try:
            return db.session.get(
                User,
                int(user_id),
                populate_existing=True,
            )
        except ValueError:
            return None

    @login_manager.request_loader
    def load_user_from_request(request) -> User | None:
        if is_local_mode():
            return get_local_user()

        return None
