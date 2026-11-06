from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from flask import Blueprint, request
from flask_login import current_user

from ..app_config import load_app_config

F = TypeVar("F", bound=Callable[..., Any])

api_bp = Blueprint("api_v1", __name__)

# Every other route under /api/v1 requires a logged-in session (see
# require_login below) — health is exempt for uptime monitoring, the auth
# endpoints themselves obviously can't require already being logged in,
# and validate is a stateless, read-only check of whatever document is
# posted to it (nothing stored, nothing user-specific) — exempt so the
# anonymous sandbox editor (frontend/src/pages/TryEditorPage.vue) can
# use real schema validation without requiring an account.
EXEMPT_ENDPOINTS = frozenset({
    "api_v1.health",
    "api_v1.register",
    "api_v1.login",
    "api_v1.csrf_token",
    "api_v1.validate",
})


@api_bp.before_request
def require_login() -> tuple[dict, int] | None:
    if request.endpoint in EXEMPT_ENDPOINTS:
        return None

    # A deactivated account's existing session loses access immediately,
    # not just on its next login attempt (see api/auth.py's login()).
    if current_user.is_authenticated and current_user.is_active:
        return None

    return {"message": "Authentication required."}, 401


def require_panel(panel_id: str) -> Callable[[F], F]:
    """Gate a route behind config/vulniverse.toml's [panels.<panel_id>].

    Panels used to be UI-only: hiding a panel's button never stopped its
    routes from working, so disabling one in config didn't actually
    restrict anything — any authenticated user could still reach it
    directly. This closes that gap the same way [features] is already
    enforced in reference_data.py/cpe_search.py. A panel id absent from
    config defaults to enabled, matching the frontend's own default (see
    frontend/src/editor/enabled-extensions.ts) and capabilities' own
    "no config = everything on" behavior.
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not load_app_config()["panels"].get(panel_id, True):
                return {"message": f"The {panel_id!r} panel is disabled."}, 404

            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


@api_bp.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_bp.get("/capabilities")
def capabilities() -> dict:
    app_config = load_app_config()

    return {
        "apiVersion": "1.0",
        "recordProfiles": [
            "cve-5.2.0",
            "gcve-bcp-05",
        ],
        "features": {
            "recordStorage": True,
            "validation": True,
            "publication": True,
            # Deprecated: kept for any existing consumer, derived from
            # the granular flags below rather than hardcoded. Nothing
            # in this codebase reads it anymore.
            "cpeSearch": (
                app_config["features"]["cpeVendors"]
                or app_config["features"]["cpeProducts"]
            ),
            "cpeProposals": False,
            **app_config["features"],
        },
        "panels": app_config["panels"],
        "actions": app_config["actions"],
    }


from . import (  # noqa: F401
    admin,
    auth,
    cna_credentials,
    cpe_search,
    patch2vuln,
    publish,
    record_quality,
    records,
    reference_data,
    templates,
    validation,
)
