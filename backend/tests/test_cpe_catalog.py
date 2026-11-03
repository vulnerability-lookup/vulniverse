from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Self

import httpx
import pytest

from vulniverse_api.services import cpe_catalog

VENDORS_EXPORT: dict[str, Any] = {
    "entity": "vendors",
    "total": 2,
    "items": [
        {"uuid": "v-1", "name": "acme", "title": "Acme", "product_count": 9},
        {"uuid": "v-2", "name": "zeta", "title": "Zeta Corp", "product_count": 1},
    ],
}

PRODUCTS_EXPORT: dict[str, Any] = {
    "entity": "products",
    "total": 2,
    "items": [
        {"uuid": "p-1", "name": "widget", "title": "Widget", "vendor_uuid": "v-1"},
        {"uuid": "p-2", "name": "gadget", "title": "Gadget", "vendor_uuid": "v-2"},
    ],
}


class FakeResponse:
    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


class FakeClient:
    def __init__(self, exports: dict[str, Any], **_: Any) -> None:
        self._exports = exports

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, url: str) -> FakeResponse:
        kind = "vendors" if "vendors" in url else "products"
        return FakeResponse(self._exports[kind])


def mock_exports(
    monkeypatch: pytest.MonkeyPatch,
    *,
    vendors: dict[str, Any] = VENDORS_EXPORT,
    products: dict[str, Any] = PRODUCTS_EXPORT,
) -> None:
    exports = {"vendors": vendors, "products": products}
    monkeypatch.setattr(
        cpe_catalog.httpx,
        "Client",
        lambda **kwargs: FakeClient(exports, **kwargs),
    )


def test_sync_catalog_writes_trimmed_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"

    result = cpe_catalog.sync_catalog(path=destination)

    assert result == {"vendors": 2, "products": 2}

    data = json.loads(destination.read_text())

    assert data["vendors"][0] == {"uuid": "v-1", "name": "acme", "title": "Acme"}
    assert "product_count" not in data["vendors"][0]
    assert data["products"][0] == {
        "uuid": "p-1",
        "name": "widget",
        "title": "Widget",
        "vendor_uuid": "v-1",
    }


def test_sync_catalog_writes_a_world_readable_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mkstemp defaults to 0600 (owner-only) — the Flask process
    serving search requests need not be the same user/process that
    ran the sync (e.g. a container's app user vs. an operator's
    shell), so the final file must not stay owner-only.
    """
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"

    cpe_catalog.sync_catalog(path=destination)

    mode = destination.stat().st_mode & 0o777
    assert mode & 0o044 == 0o044


def test_sync_catalog_drops_records_missing_uuid_or_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sparse_vendors = {
        "entity": "vendors",
        "total": 2,
        "items": [
            {"uuid": "v-1", "name": "acme", "title": "Acme"},
            {"uuid": "", "name": "no-uuid"},
        ],
    }
    mock_exports(monkeypatch, vendors=sparse_vendors)
    destination = tmp_path / "cpe-catalog.json"

    result = cpe_catalog.sync_catalog(path=destination)

    assert result["vendors"] == 1


def test_sync_catalog_rejects_count_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad_export = {**VENDORS_EXPORT, "total": 5}
    mock_exports(monkeypatch, vendors=bad_export)
    destination = tmp_path / "cpe-catalog.json"

    with pytest.raises(ValueError):
        cpe_catalog.sync_catalog(path=destination)

    assert not destination.exists()


def test_sync_catalog_rejects_wrong_entity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wrong_entity = {**VENDORS_EXPORT, "entity": "products"}
    mock_exports(monkeypatch, vendors=wrong_entity)
    destination = tmp_path / "cpe-catalog.json"

    with pytest.raises(ValueError):
        cpe_catalog.sync_catalog(path=destination)


def test_sync_catalog_preserves_previous_catalog_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "cpe-catalog.json"
    mock_exports(monkeypatch)
    cpe_catalog.sync_catalog(path=destination)
    previous = destination.read_text()

    def fail(**_: Any) -> FakeClient:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(cpe_catalog.httpx, "Client", fail)

    with pytest.raises(httpx.ConnectError):
        cpe_catalog.sync_catalog(path=destination)

    assert destination.read_text() == previous


def test_search_catalog_raises_when_not_synced(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        cpe_catalog.search_catalog("vendors", "a", path=tmp_path / "missing.json")


def test_search_catalog_rejects_unknown_kind(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        cpe_catalog.search_catalog("bogus", "a", path=tmp_path / "missing.json")


def test_search_catalog_matches_name_or_title(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    result = cpe_catalog.search_catalog("vendors", "zeta", path=destination)

    assert [item["uuid"] for item in result["items"]] == ["v-2"]
    assert result["total"] == 1


def test_search_catalog_products_scoped_by_vendor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vendors = {
        "entity": "vendors",
        "total": 2,
        "items": [
            {"uuid": "v-1", "name": "acme", "title": "Acme"},
            {"uuid": "v-2", "name": "zorp", "title": "Zorp Inc"},
        ],
    }
    products = {
        "entity": "products",
        "total": 2,
        "items": [
            {"uuid": "p-1", "name": "widget", "title": "Widget", "vendor_uuid": "v-1"},
            {"uuid": "p-2", "name": "widget", "title": "Widget", "vendor_uuid": "v-2"},
        ],
    }
    mock_exports(monkeypatch, vendors=vendors, products=products)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    result = cpe_catalog.search_catalog(
        "products", "widget", vendor_q="acme", path=destination,
    )

    assert [item["uuid"] for item in result["items"]] == ["p-1"]
    assert result["total"] == 1


def test_search_catalog_products_vendor_q_matching_no_vendor_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    result = cpe_catalog.search_catalog(
        "products", "widget", vendor_q="no-such-vendor", path=destination,
    )

    assert result["items"] == []
    assert result["total"] == 0


def test_search_catalog_blank_vendor_q_is_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    with_blank = cpe_catalog.search_catalog(
        "products", "widget", vendor_q="   ", path=destination,
    )
    without = cpe_catalog.search_catalog("products", "widget", path=destination)

    assert with_blank == without


def test_search_catalog_paginates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    many_vendors = {
        "entity": "vendors",
        "total": 3,
        "items": [
            {"uuid": f"v-{i}", "name": f"vendor{i}", "title": ""} for i in range(3)
        ],
    }
    mock_exports(monkeypatch, vendors=many_vendors)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    page1 = cpe_catalog.search_catalog(
        "vendors", "vendor", page=1, per_page=2, path=destination,
    )
    page2 = cpe_catalog.search_catalog(
        "vendors", "vendor", page=2, per_page=2, path=destination,
    )

    assert [item["uuid"] for item in page1["items"]] == ["v-0", "v-1"]
    assert [item["uuid"] for item in page2["items"]] == ["v-2"]
    assert page1["total"] == 3
    assert page1["total_pages"] == 2


def test_search_catalog_reflects_resync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_exports(monkeypatch)
    destination = tmp_path / "cpe-catalog.json"
    cpe_catalog.sync_catalog(path=destination)

    before = cpe_catalog.search_catalog("vendors", "acme", path=destination)
    assert before["total"] == 1

    updated_vendors = {
        "entity": "vendors",
        "total": 1,
        "items": [{"uuid": "v-3", "name": "acme-two", "title": "Acme Two"}],
    }
    mock_exports(monkeypatch, vendors=updated_vendors)
    cpe_catalog.sync_catalog(path=destination)

    after = cpe_catalog.search_catalog("vendors", "acme", path=destination)
    assert [item["uuid"] for item in after["items"]] == ["v-3"]
