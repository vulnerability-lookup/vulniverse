from flask import Blueprint

from ..services.app_config import load_app_config

api_bp = Blueprint("api_v1", __name__)


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


from . import publish, records, reference_data, templates, validation  # noqa: F401
