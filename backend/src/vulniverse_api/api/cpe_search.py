from __future__ import annotations

from typing import Any

import httpx
from flask import request

from ..services.cpe_search import (
    search_cpes,
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

    except httpx.HTTPError as error:
        return {
            "message": "Could not search CPE vendors.",
            "detail": str(error),
        }, 502

    return result, 200


@api_bp.get("/cpe/cpes")
def cpe_entries() -> tuple[
    dict[str, Any] | list[Any],
    int,
]:
    q = _text_arg("q")

    vendor_q = _text_arg("vendor_q")

    product_q = _text_arg("product_q")

    part = _text_arg("part")

    # Avoid expensive broad requests while the user is merely
    # typing. q itself is optional because vendor_q/product_q
    # are valid CPE search inputs.
    if not any(
        (
            _is_search_term(q),
            _is_search_term(vendor_q),
            _is_search_term(product_q),
        )
    ):
        return [], 200

    try:
        result = search_cpes(
            q=q,
            vendor_q=vendor_q,
            product_q=product_q,
            part=part,
            page=_page(),
            per_page=_per_page(),
        )

    except httpx.HTTPError as error:
        return {
            "message": "Could not search CPEs.",
            "detail": str(error),
        }, 502

    return result, 200
