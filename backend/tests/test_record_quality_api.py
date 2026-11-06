from __future__ import annotations

import pytest
from flask.testing import FlaskClient

from vulniverse_api import api as api_module

VALID_PAYLOAD = {
    "profile": "cve-5.2.0",
    "record": {
        "containers": {"cna": {"descriptions": [{"lang": "en", "value": "bug"}]}},
    },
}


def test_record_quality_scores_a_record(client: FlaskClient) -> None:
    response = client.post("/api/v1/record-quality", json=VALID_PAYLOAD)

    assert response.status_code == 200
    assert "score" in response.get_json()


def test_disabled_panel_is_404(
    client: FlaskClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_load_app_config = api_module.load_app_config

    def patched() -> dict:
        config = dict(real_load_app_config())
        config["panels"] = {**config["panels"], "record-quality": False}
        return config

    monkeypatch.setattr(api_module, "load_app_config", patched)

    response = client.post("/api/v1/record-quality", json=VALID_PAYLOAD)

    assert response.status_code == 404
