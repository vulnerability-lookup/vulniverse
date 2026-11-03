from __future__ import annotations

from typing import Any

import pytest
from flask.testing import FlaskClient

from vulniverse_api.api import cpe_search as cpe_search_api

SEARCH_RESULT: dict[str, Any] = {
    "items": [{"uuid": "v-1", "name": "acme", "title": "Acme"}],
    "page": 1,
    "per_page": 25,
    "total": 1,
    "total_pages": 1,
}


def test_cpe_vendors_short_query_returns_empty_without_searching(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_: Any, **__: Any) -> None:
        raise AssertionError("search_vendors should not be called for a short query")

    monkeypatch.setattr(cpe_search_api, "search_vendors", fail)

    response = client.get("/api/v1/cpe/vendors?q=a")

    assert response.status_code == 200
    assert response.get_json() == []


def test_cpe_vendors_returns_catalog_results(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cpe_search_api,
        "search_vendors",
        lambda q, *, page, per_page: SEARCH_RESULT,
    )

    response = client.get("/api/v1/cpe/vendors?q=acme")

    assert response.status_code == 200
    assert response.get_json() == SEARCH_RESULT


def test_cpe_vendors_returns_503_when_catalog_unavailable(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing(q: str, *, page: int, per_page: int) -> None:
        raise FileNotFoundError("no catalog")

    monkeypatch.setattr(cpe_search_api, "search_vendors", raise_missing)

    response = client.get("/api/v1/cpe/vendors?q=acme")

    assert response.status_code == 503
    assert response.get_json() == {"message": "Local CPE catalog unavailable."}


def test_cpe_products_returns_catalog_results(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cpe_search_api,
        "search_products",
        lambda q, *, page, per_page, vendor_q: SEARCH_RESULT,
    )

    response = client.get("/api/v1/cpe/products?q=widget")

    assert response.status_code == 200
    assert response.get_json() == SEARCH_RESULT


def test_cpe_products_forwards_vendor_q(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_search_products(q: str, *, page: int, per_page: int, vendor_q: str | None) -> dict:
        captured["q"] = q
        captured["vendor_q"] = vendor_q
        return SEARCH_RESULT

    monkeypatch.setattr(cpe_search_api, "search_products", fake_search_products)

    response = client.get("/api/v1/cpe/products?q=widget&vendor_q=acme")

    assert response.status_code == 200
    assert captured == {"q": "widget", "vendor_q": "acme"}


def test_cpe_products_returns_503_when_catalog_unavailable(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_corrupt(q: str, *, page: int, per_page: int, vendor_q: str | None) -> None:
        raise ValueError("malformed catalog")

    monkeypatch.setattr(cpe_search_api, "search_products", raise_corrupt)

    response = client.get("/api/v1/cpe/products?q=widget")

    assert response.status_code == 503


def test_cpe_entries_route_is_disabled(client: FlaskClient) -> None:
    response = client.get("/api/v1/cpe/cpes?q=windows")

    assert response.status_code == 503
    assert "disabled" in response.get_json()["message"]
