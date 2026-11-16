from flask import current_app

from ..services.gcve_lookup import LookupUnavailable, lookup_public_record
from . import api_bp, require_panel


@api_bp.get("/compare-vulnerabilities/<string:identifier>")
@require_panel("compare-vulnerabilities")
def get_public_record(identifier: str) -> tuple[dict, int]:
    """A GCVE or CVE record from its public source (see gcve_lookup.py)."""
    try:
        result = lookup_public_record(identifier)
    except LookupUnavailable:
        return {
            "message": "Looking up public records needs the backend's gcve extra "
            "(pip install 'vulniverse-api[gcve]')."
        }, 501
    except ValueError as error:
        return {"message": str(error)}, 400
    except LookupError as error:
        return {"message": str(error)}, 404
    # requests' errors are OSErrors; requests itself comes with the extra.
    except (OSError, RuntimeError) as error:
        current_app.logger.warning(
            "Public record lookup of %s failed: %s", identifier, error
        )
        return {"message": "The public source could not be reached."}, 502

    if result is None:
        return {"message": f"No public record found for {identifier}."}, 404

    return result, 200
