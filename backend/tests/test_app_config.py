from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient

from vulniverse_api.services import app_config


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    app_config.load_app_config.cache_clear()
    yield
    app_config.load_app_config.cache_clear()


def test_falls_back_to_sample_file_when_real_config_absent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    sample_path = tmp_path / "vulniverse.toml.sample"
    sample_path.write_text(
        '[panels]\n"stats" = true\n\n[modules]\n"download-json" = false\n',
    )

    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", sample_path)

    result = app_config.load_app_config()

    assert result == {
        "panels": {"stats": True},
        "modules": {"download-json": False},
    }


def test_prefers_real_config_over_sample(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text('[panels]\n"vl" = false\n')
    sample_path = tmp_path / "vulniverse.toml.sample"
    sample_path.write_text('[panels]\n"vl" = true\n')

    monkeypatch.setattr(app_config, "CONFIG_PATH", real_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", sample_path)

    result = app_config.load_app_config()

    assert result["panels"] == {"vl": False}


def test_empty_tables_when_neither_file_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")

    result = app_config.load_app_config()

    assert result == {"panels": {}, "modules": {}}


def test_capabilities_endpoint_includes_panels_and_modules(client: FlaskClient) -> None:
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    body = response.get_json()
    assert "panels" in body
    assert "modules" in body
    assert isinstance(body["panels"], dict)
    assert isinstance(body["modules"], dict)
