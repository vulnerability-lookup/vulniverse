import httpx

from ..services.reference_data import get_reference_list, known_reference_kinds
from . import api_bp


@api_bp.get("/references/<kind>")
def reference_list(kind: str) -> tuple[dict, int]:
    if kind not in known_reference_kinds():
        return {"message": f"Unknown reference list: {kind!r}"}, 404

    try:
        items = get_reference_list(kind)
    except httpx.HTTPError as error:
        return {
            "message": f"Could not fetch the {kind.upper()} reference list.",
            "detail": str(error),
        }, 502

    return {"items": items}, 200
