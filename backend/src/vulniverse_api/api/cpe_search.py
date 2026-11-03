from __future__ import annotations

from typing import Any

from flask import request

from ..app_config import load_app_config
from ..services.cpe_search import (
    search_products,
    search_vendors,
)
from . import api_bp

MIN_QUERY_LENGTH = 2

DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 25


def _integer_arg(
    name: str,
    default: int,
) -> int:
    value = request.args.get(
        name,
        type=int,
    )

    if value is None:
        return default

    return max(
        1,
        value,
    )


def _page() -> int:
    return _integer_arg(
        "page",
        DEFAULT_PAGE,
    )


def _per_page() -> int:
    return min(
        MAX_PER_PAGE,
        _integer_arg(
            "per_page",
            DEFAULT_PER_PAGE,
        ),
    )


def _text_arg(
    name: str,
) -> str | None:
    value = request.args.get(
        name,
        type=str,
    )

    if value is None:
        return None

    value = value.strip()

    return value if value else None


def _is_search_term(
    value: str | None,
) -> bool:
    return bool(value and len(value) >= MIN_QUERY_LENGTH)


@api_bp.get("/cpe/vendors")
def cpe_vendors() -> tuple[
    dict[str, Any] | list[Any],
    int,
]:
    if not load_app_config()["features"]["cpeVendors"]:
        return {"message": "Vendor suggestions are disabled."}, 404

    q = _text_arg("q")

    if not _is_search_term(q):
        return [], 200

    assert q is not None  # narrowed by _is_search_term above

    try:
        result = search_vendors(
            q,
            page=_page(),
            per_page=_per_page(),
        )

    except (FileNotFoundError, OSError, ValueError):
        return {"message": "Local CPE catalog unavailable."}, 503

    return result, 200


@api_bp.get("/cpe/products")
def cpe_products() -> tuple[
    dict[str, Any] | list[Any],
    int,
]:
    if not load_app_config()["features"]["cpeProducts"]:
        return {"message": "Product suggestions are disabled."}, 404

    q = _text_arg("q")

    if not _is_search_term(q):
        return [], 200

    assert q is not None  # narrowed by _is_search_term above

    vendor_q = _text_arg("vendor_q")

    try:
        result = search_products(
            q,
            page=_page(),
            per_page=_per_page(),
            vendor_q=vendor_q,
        )

    except (FileNotFoundError, OSError, ValueError):
        return {"message": "Local CPE catalog unavailable."}, 503

    return result, 200


@api_bp.get("/cpe/cpes")
def cpe_entries() -> tuple[
    dict[str, Any] | list[Any],
    int,
]:
    # Full CPE-identifier suggestions are temporarily disabled: unlike
    # vendor/product search, mirroring this catalog locally would mean
    # syncing the much larger /cpes/export dataset, which is out of
    # scope for now. 
    return {
        "message": "CPE identifier recommendations are temporarily disabled.",
    }, 503
