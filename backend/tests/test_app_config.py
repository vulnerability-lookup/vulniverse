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
        "integrations": {},
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

    assert result == {"panels": {}, "modules": {}, "integrations": {}}


def test_get_integration_returns_none_when_keys_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "vulniverse.toml"
    config_path.write_text(
        '[integrations.vl]\ncve_url = "https://example.test/api/cna"\n',
    )

    monkeypatch.setattr(app_config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "missing.sample")

    assert app_config.get_integration("vl") is None
    assert app_config.is_integration_configured("vl") is False


def test_get_integration_returns_credentials_when_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "vulniverse.toml"
    config_path.write_text(
        "[integrations.vl]\n"
        'cve_url = "https://example.test/api/cna"\n'
        'short_name = "acme"\n'
        'cve_api_org = "ACME"\n'
        'cve_api_user = "user@example.test"\n'
        'cve_api_key = "secret"\n',
    )

    monkeypatch.setattr(app_config, "CONFIG_PATH", config_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "missing.sample")

    credentials = app_config.get_integration("vl")

    assert credentials == {
        "cve_url": "https://example.test/api/cna",
        "short_name": "acme",
        "cve_api_org": "ACME",
        "cve_api_user": "user@example.test",
        "cve_api_key": "secret",
    }
    assert app_config.is_integration_configured("vl") is True
    assert app_config.get_integration("cve-program") is None


def test_capabilities_endpoint_includes_panels_and_modules(client: FlaskClient) -> None:
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    body = response.get_json()
    assert "panels" in body
    assert "modules" in body
    assert isinstance(body["panels"], dict)
    assert isinstance(body["modules"], dict)
