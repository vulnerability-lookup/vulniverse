from __future__ import annotations

from typing import Any, Self

import httpx
import pytest
from flask.testing import FlaskClient

from vulniverse_api.api import reference_data as reference_data_api
from vulniverse_api.services import reference_data as reference_data_service


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=httpx.Request("GET", "http://test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> Any:
        return self._payload


class FakeCweClient:
    """Stands in for httpx.Client(base_url=...) used for batched name lookups."""

    def __init__(self, weakness_names: dict[str, str], **_: Any) -> None:
        self._weakness_names = weakness_names

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, path: str) -> FakeResponse:
        ids = path.rsplit("/", 1)[-1].split(",")
        weaknesses = [
            {"ID": cwe_id, "Name": self._weakness_names[cwe_id]}
            for cwe_id in ids
            if cwe_id in self._weakness_names
        ]

        return FakeResponse({"Weaknesses": weaknesses})


DESCENDANTS_TREE = [
    {
        "Data": {"Type": "view", "ID": "1000"},
        "Children": [
            {
                "Data": {"Type": "pillar_weakness", "ID": "1"},
                "Children": [
                    {"Data": {"Type": "base_weakness", "ID": "2"}, "Children": None},
                ],
            },
            {"Data": {"Type": "category", "ID": "999"}, "Children": None},
        ],
    },
]

WEAKNESS_NAMES = {
    "1": "Fake Weakness One",
    "2": "Fake Weakness Two",
}

CAPEC_BUNDLE = {
    "objects": [
        {
            "type": "attack-pattern",
            "name": "Fake Pattern One",
            "external_references": [
                {"source_name": "capec", "external_id": "CAPEC-1"},
                {"source_name": "cwe", "external_id": "CWE-1"},
            ],
        },
        {
            "type": "course-of-action",
            "name": "Not a pattern",
        },
    ],
}


@pytest.fixture(autouse=True)
def clear_reference_cache() -> None:
    reference_data_service._cache.clear()


def mock_cwe_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, params: dict | None = None, timeout: float | None = None) -> FakeResponse:
        assert "descendants" in url
        return FakeResponse(DESCENDANTS_TREE)

    monkeypatch.setattr(reference_data_service.httpx, "get", fake_get)
    monkeypatch.setattr(
        reference_data_service.httpx,
        "Client",
        lambda **kwargs: FakeCweClient(WEAKNESS_NAMES, **kwargs),
    )


def mock_capec_endpoint(monkeypatch: pytest.MonkeyPatch, payload: Any = CAPEC_BUNDLE) -> None:
    def fake_get(url: str, timeout: float | None = None) -> FakeResponse:
        return FakeResponse(payload)

    monkeypatch.setattr(reference_data_service.httpx, "get", fake_get)


def test_fetch_cwe_list_excludes_non_weakness_nodes(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_cwe_endpoints(monkeypatch)

    items = reference_data_service.get_reference_list("cwe")

    assert items == [
        {"id": "CWE-1", "name": "Fake Weakness One"},
        {"id": "CWE-2", "name": "Fake Weakness Two"},
    ]


def test_fetch_capec_list_excludes_non_attack_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_capec_endpoint(monkeypatch)

    items = reference_data_service.get_reference_list("capec")

    assert items == [{"id": "CAPEC-1", "name": "Fake Pattern One"}]


def test_cache_avoids_refetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def fake_get(url: str, timeout: float | None = None) -> FakeResponse:
        calls["count"] += 1
        return FakeResponse(CAPEC_BUNDLE)

    monkeypatch.setattr(reference_data_service.httpx, "get", fake_get)

    reference_data_service.get_reference_list("capec")
    reference_data_service.get_reference_list("capec")

    assert calls["count"] == 1


def test_stale_cache_used_when_refetch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_capec_endpoint(monkeypatch)
    first = reference_data_service.get_reference_list("capec")

    # Force the cache entry to look expired without waiting a day.
    reference_data_service._cache["capec"] = (0.0, first)

    def fake_get_fail(url: str, timeout: float | None = None) -> FakeResponse:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(reference_data_service.httpx, "get", fake_get_fail)

    second = reference_data_service.get_reference_list("capec")

    assert second == first


def test_raises_when_never_cached_and_fetch_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_fail(url: str, timeout: float | None = None) -> FakeResponse:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(reference_data_service.httpx, "get", fake_get_fail)

    with pytest.raises(httpx.HTTPError):
        reference_data_service.get_reference_list("capec")


def test_reference_list_route_success(client: FlaskClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reference_data_api,
        "get_reference_list",
        lambda kind: [{"id": "CWE-1", "name": "X"}],
    )

    response = client.get("/api/v1/references/cwe")

    assert response.status_code == 200
    assert response.get_json() == {"items": [{"id": "CWE-1", "name": "X"}]}


def test_reference_list_route_unknown_kind(client: FlaskClient) -> None:
    response = client.get("/api/v1/references/bogus")

    assert response.status_code == 404


def test_reference_list_route_upstream_failure(client: FlaskClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(kind: str) -> list[dict[str, str]]:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(reference_data_api, "get_reference_list", raise_error)

    response = client.get("/api/v1/references/capec")

    assert response.status_code == 502
