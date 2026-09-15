from flask import Blueprint, request
from flask_login import current_user

from ..services.app_config import load_app_config

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
            "cpeSearch": False,
            "cpeProposals": False,
            "publication": True,
        },
        "panels": app_config["panels"],
        "modules": app_config["modules"],
    }


from . import (  # noqa: F401
    admin,
    auth,
    cna_credentials,
    publish,
    records,
    reference_data,
    templates,
    validation,
)
