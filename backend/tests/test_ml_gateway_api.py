from __future__ import annotations

from typing import Any

import httpx
import pytest
from flask.testing import FlaskClient

from vulniverse_api import api as api_module
from vulniverse_api.services import ml_gateway
from vulniverse_api.services.ml_gateway import MlGatewayConfig

SEVERITY_URL = "/api/v1/ml-gateway/severity"
ATTACK_URL = "/api/v1/ml-gateway/attack-techniques"


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        if isinstance(self._payload, str):
            raise ValueError("not json")  # noqa: TRY004
        return self._payload


def _config(enabled: bool = True) -> MlGatewayConfig:
    return MlGatewayConfig(
        enabled=enabled, api_url="http://ml-gateway:8000", timeout_seconds=30
    )


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ml_gateway, "get_ml_gateway_config", _config)
    monkeypatch.setattr(api_module.ml_gateway, "get_ml_gateway_config", _config)
    monkeypatch.setattr(api_module, "get_ml_gateway_config", _config)


def _gateway(monkeypatch: pytest.MonkeyPatch, response: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def fake_post(url: str, *, json: Any, timeout: Any) -> Any:
        calls.append({"url": url, "json": json})
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(ml_gateway.httpx, "post", fake_post)
    return calls


def test_requires_login(anon_client: FlaskClient) -> None:
    assert anon_client.post(SEVERITY_URL, json={"description": "x"}).status_code == 401


def test_returns_403_when_not_configured(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        api_module.ml_gateway, "get_ml_gateway_config", lambda: _config(enabled=False)
    )

    assert client.post(SEVERITY_URL, json={"description": "x"}).status_code == 403


def test_capabilities_reports_the_panel_only_when_configured(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert client.get("/api/v1/capabilities").json["panels"]["ml-gateway"] is True

    monkeypatch.setattr(
        api_module, "get_ml_gateway_config", lambda: _config(enabled=False)
    )

    assert client.get("/api/v1/capabilities").json["panels"]["ml-gateway"] is False


@pytest.mark.parametrize("body", [{}, {"description": "  "}, {"description": 3}])
def test_rejects_a_missing_description(client: FlaskClient, body: Any) -> None:
    assert client.post(SEVERITY_URL, json=body).status_code == 400


def test_rejects_a_too_long_description(client: FlaskClient) -> None:
    response = client.post(SEVERITY_URL, json={"description": "x" * 20_001})

    assert response.status_code == 413


@pytest.mark.parametrize("top_k", [0, 21, "5", True])
def test_rejects_a_bad_top_k(client: FlaskClient, top_k: Any) -> None:
    response = client.post(ATTACK_URL, json={"description": "x", "topK": top_k})

    assert response.status_code == 400


def test_severity(client: FlaskClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _gateway(
        monkeypatch,
        FakeResponse(
            200,
            {
                "severity": "High",
                "confidence": 0.93,
                "model": "CIRCL/severity",
                "model_revision": "abc",
                "error": None,
            },
        ),
    )

    response = client.post(SEVERITY_URL, json={"description": "SQL injection"})

    assert response.status_code == 200
    assert response.json == {
        "severity": "High",
        "confidence": 0.93,
        "model": "CIRCL/severity",
    }
    assert calls == [
        {
            "url": "http://ml-gateway:8000/classify/severity",
            "json": {"description": "SQL injection"},
        }
    ]


def test_attack_techniques(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _gateway(
        monkeypatch,
        FakeResponse(
            200,
            {
                "techniques": [
                    {
                        "technique": "T1190",
                        "name": "Exploit Public-Facing Application",
                        "score": 0.71,
                        "predicted": True,
                    },
                    {
                        "technique": "T1059",
                        "name": "Command",
                        "score": 0.2,
                        "predicted": False,
                    },
                ],
                "model": "CIRCL/attack",
                "error": None,
            },
        ),
    )

    response = client.post(ATTACK_URL, json={"description": "RCE", "topK": 5})

    assert response.status_code == 200
    assert response.json["techniques"] == [
        {
            "id": "T1190",
            "name": "Exploit Public-Facing Application",
            "score": 0.71,
            "predicted": True,
        },
        {"id": "T1059", "name": "Command", "score": 0.2, "predicted": False},
    ]
    assert calls[0]["json"] == {"description": "RCE", "top_k": 5}


@pytest.mark.parametrize(
    ("gateway_response", "status"),
    [
        (
            FakeResponse(
                200, {"severity": "", "confidence": 0, "error": "model failed"}
            ),
            502,
        ),
        (FakeResponse(200, {"error": None}), 502),
        (FakeResponse(200, "not json"), 502),
        (FakeResponse(500, {}), 502),
        (FakeResponse(503, {}), 503),
        (httpx.ConnectError("refused"), 502),
        (httpx.ReadTimeout("slow"), 502),
    ],
)
def test_gateway_failures(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
    gateway_response: Any,
    status: int,
) -> None:
    _gateway(monkeypatch, gateway_response)

    response = client.post(SEVERITY_URL, json={"description": "x"})

    assert response.status_code == status
    assert response.json["message"]
