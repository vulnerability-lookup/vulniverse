from flask import Blueprint, request
from flask_login import current_user

from ..services.app_config import load_app_config

api_bp = Blueprint("api_v1", __name__)

# Every other route under /api/v1 requires a logged-in session (see
# require_login below) — health is exempt for uptime monitoring, the auth
# endpoints themselves obviously can't require already being logged in.
EXEMPT_ENDPOINTS = frozenset({
    "api_v1.health",
    "api_v1.register",
    "api_v1.login",
    "api_v1.csrf_token",
})


@api_bp.before_request
def require_login() -> tuple[dict, int] | None:
    if request.endpoint in EXEMPT_ENDPOINTS or current_user.is_authenticated:
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
    auth,
    cna_credentials,
    publish,
    records,
    reference_data,
    templates,
    validation,
)
