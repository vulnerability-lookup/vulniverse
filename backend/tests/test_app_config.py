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
        '[panels]\n"stats" = true\n\n[actions]\n"download-json" = false\n',
    )

    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", sample_path)

    result = app_config.load_app_config()

    assert result == {
        "panels": {"stats": True},
        "actions": {"download-json": False},
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


def test_panel_table_with_enabled_key_is_flattened_to_bool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text(
        "[panels.stats]\nenabled = false\n\n"
        '[panels.patch2vuln]\nenabled = true\nexecutable = "/opt/patch2vuln.py"\n',
    )

    monkeypatch.setattr(app_config, "CONFIG_PATH", real_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")

    result = app_config.load_app_config()

    # Only `enabled` is a capability; patch2vuln's own config (executable,
    # ollama_host, ...) never reaches this result.
    assert result["panels"] == {"stats": False, "patch2vuln": True}


def test_panel_table_without_enabled_key_defaults_to_true(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text('[panels.stats]\nnote = "no enabled key here"\n')

    monkeypatch.setattr(app_config, "CONFIG_PATH", real_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")

    result = app_config.load_app_config()

    assert result["panels"] == {"stats": True}


def test_legacy_flat_bool_panels_still_supported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text('[panels]\n"vl" = false\n"stats" = true\n')

    monkeypatch.setattr(app_config, "CONFIG_PATH", real_path)
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")

    result = app_config.load_app_config()

    assert result["panels"] == {"vl": False, "stats": True}


def test_empty_tables_when_neither_file_exists(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_config, "CONFIG_PATH", tmp_path / "vulniverse.toml")
    monkeypatch.setattr(app_config, "SAMPLE_CONFIG_PATH", tmp_path / "vulniverse.toml.sample")

    result = app_config.load_app_config()

    assert result == {"panels": {}, "actions": {}}


def test_capabilities_endpoint_includes_panels_and_actions(client: FlaskClient) -> None:
    response = client.get("/api/v1/capabilities")

    assert response.status_code == 200
    body = response.get_json()
    assert "panels" in body
    assert "actions" in body
    assert isinstance(body["panels"], dict)
    assert isinstance(body["actions"], dict)
