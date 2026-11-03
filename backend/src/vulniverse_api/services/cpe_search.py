from __future__ import annotations

from typing import Any

from .cpe_catalog import search_catalog


def search_vendors(
    q: str,
    *,
    page: int = 1,
    per_page: int = 25,
) -> dict[str, Any]:
    return search_catalog("vendors", q, page=page, per_page=per_page)


def search_products(
    q: str,
    *,
    page: int = 1,
    per_page: int = 25,
    vendor_q: str | None = None,
) -> dict[str, Any]:
    return search_catalog(
        "products", q, page=page, per_page=per_page, vendor_q=vendor_q,
    )
