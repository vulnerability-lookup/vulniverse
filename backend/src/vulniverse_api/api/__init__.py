from flask import Blueprint

api_bp = Blueprint("api_v1", __name__)


@api_bp.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api_bp.get("/capabilities")
def capabilities() -> dict:
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
            "publication": False,
        },
    }


from . import records, reference_data, validation  # noqa: F401
