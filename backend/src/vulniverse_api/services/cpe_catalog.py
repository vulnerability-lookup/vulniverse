from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from flask import current_app

CPE_EXPORT_API_ROOT = "https://cpe.gcve.eu/api"

EXPORT_TIMEOUT_SECONDS = 120.0

CATALOG_KINDS = ("vendors", "products")

VENDOR_FIELDS = ("uuid", "name", "title")
PRODUCT_FIELDS = ("uuid", "name", "title", "vendor_uuid")


def catalog_path() -> Path:
    return Path(current_app.instance_path) / "cpe-catalog.json"


def _fetch_export(
    client: httpx.Client,
    kind: str,
) -> list[dict[str, Any]]:
    response = client.get(f"{CPE_EXPORT_API_ROOT}/{kind}/export")
    response.raise_for_status()

    payload = response.json()

    if not isinstance(payload, dict) or payload.get("entity") != kind:
        raise ValueError(f"Unexpected {kind} export response shape.")

    items = payload.get("items")
    total = payload.get("total")

    if not isinstance(items, list) or not isinstance(total, int) or len(items) != total:
        raise ValueError(f"{kind} export item count does not match its reported total.")

    fields = VENDOR_FIELDS if kind == "vendors" else PRODUCT_FIELDS

    return [
        {field: item.get(field) for field in fields}
        for item in items
        if isinstance(item, dict) and item.get("uuid") and item.get("name")
    ]


def sync_catalog(
    *,
    path: Path | None = None,
) -> dict[str, int]:
    """Fetches fresh vendor/product exports and atomically replaces the
    local catalog file. If anything fails (network error, malformed
    response), the previous catalog is left untouched — a failed sync
    should never take autocomplete offline.
    """
    destination = path if path is not None else catalog_path()
    destination.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=EXPORT_TIMEOUT_SECONDS) as client:
        vendors = _fetch_export(client, "vendors")
        products = _fetch_export(client, "products")

    catalog = {"vendors": vendors, "products": products}

    fd, tmp_name = tempfile.mkstemp(
        dir=destination.parent,
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(catalog, handle, ensure_ascii=False)

        os.chmod(tmp_name, 0o644)
        os.replace(tmp_name, destination)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    return {"vendors": len(vendors), "products": len(products)}


_IndexedRecord = tuple[dict[str, Any], str]


@lru_cache(maxsize=1)
def _load_catalog(
    path_str: str,
    mtime_ns: int,
) -> dict[str, list[_IndexedRecord]]:
    with open(path_str, encoding="utf-8") as handle:
        catalog = json.load(handle)

    indexed: dict[str, list[_IndexedRecord]] = {}

    for kind in CATALOG_KINDS:
        records = catalog.get(kind, [])
        records.sort(key=lambda record: (record["name"].casefold(), record["uuid"]))

        indexed[kind] = [
            (
                record,
                (record["name"] + " " + (record.get("title") or "")).casefold(),
            )
            for record in records
        ]

    return indexed


def search_catalog(
    kind: str,
    q: str,
    *,
    page: int = 1,
    per_page: int = 25,
    vendor_q: str | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    if kind not in CATALOG_KINDS:
        raise ValueError(f"Unsupported catalog type: {kind!r}")

    catalog_file = path if path is not None else catalog_path()

    if not catalog_file.is_file():
        raise FileNotFoundError("CPE catalog has not been synchronized yet.")

    indexed = _load_catalog(str(catalog_file), catalog_file.stat().st_mtime_ns)

    candidates = indexed[kind]

    if kind == "products" and vendor_q and vendor_q.strip():
        vendor_term = vendor_q.strip().casefold()
        matching_vendor_uuids = {
            vendor["uuid"]
            for vendor, searchable in indexed["vendors"]
            if vendor_term in searchable
        }
        candidates = [
            (record, searchable)
            for record, searchable in candidates
            if record.get("vendor_uuid") in matching_vendor_uuids
        ]

    term = q.strip().casefold()
    start = (page - 1) * per_page
    end = start + per_page

    matches = [record for record, searchable in candidates if term in searchable]
    total = len(matches)

    return {
        "items": matches[start:end],
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page if per_page else 0,
    }
