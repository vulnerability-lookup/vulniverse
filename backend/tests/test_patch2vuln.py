from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from vulniverse_api.services import patch2vuln

VALID_CVE_RECORD = {
    "dataType": "CVE_RECORD",
    "dataVersion": "5.2",
    "containers": {"cna": {}},
}


class FakeResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload


def enabled_config(
    **overrides: Any,
) -> patch2vuln.Patch2VulnConfig:
    defaults: dict[str, Any] = {
        "enabled": True,
        "api_url": "https://patch2vuln.example.org",
        "api_token": None,
        "timeout_seconds": 300,
        "models": (),
    }
    defaults.update(overrides)
    return patch2vuln.Patch2VulnConfig(**defaults)


def test_run_patch2vuln_raises_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln,
        "get_patch2vuln_config",
        lambda: enabled_config(enabled=False),
    )

    with pytest.raises(RuntimeError, match="disabled"):
        patch2vuln.run_patch2vuln([], [], {})


def test_run_patch2vuln_requires_at_least_one_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    with pytest.raises(ValueError, match="No patch inputs"):
        patch2vuln.run_patch2vuln([], [], {})


def test_run_patch2vuln_builds_request_and_reshapes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln,
        "get_patch2vuln_config",
        lambda: enabled_config(models=("qwen3.8:27b",)),
    )

    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        captured["timeout"] = timeout

        return FakeResponse(
            200,
            {
                "draft": True,
                "records": {"cve": VALID_CVE_RECORD, "analysis": {"summary": "ok"}},
            },
        )

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    result = patch2vuln.run_patch2vuln(
        ["https://github.com/owner/repo/commit/abc123.patch"],
        [b"diff --git a/x b/x"],
        {
            "vendor": "Acme",
            "product": "Widget",
            "affectedVersion": "1.0",
            "fixedVersion": "1.1",
            "versionType": "semver",
        },
    )

    assert result == {"record": VALID_CVE_RECORD, "analysis": {"summary": "ok"}}

    assert captured["url"] == "https://patch2vuln.example.org/api/v1/advisories"
    assert captured["timeout"] == 300
    assert captured["headers"] == {}
    assert captured["json"] == {
        "patches": ["diff --git a/x b/x"],
        "urls": ["https://github.com/owner/repo/commit/abc123.patch"],
        "vendor": "Acme",
        "product": "Widget",
        "affected_version": "1.0",
        "fixed_version": "1.1",
        "models": ["qwen3.8:27b"],
    }
    # versionType has no equivalent on the web service — must not leak through.
    assert "version_type" not in captured["json"]
    assert "versionType" not in captured["json"]


def test_run_patch2vuln_sends_bearer_token_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln,
        "get_patch2vuln_config",
        lambda: enabled_config(api_token="secret-token"),
    )

    captured: dict[str, Any] = {}

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        captured["headers"] = headers
        return FakeResponse(200, {"records": {"cve": VALID_CVE_RECORD}})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})

    assert captured["headers"] == {"Authorization": "Bearer secret-token"}


def test_run_patch2vuln_raises_on_non_200_with_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(
            429, {"error": {"code": "busy", "message": "Analysis slot occupied"}},
        )

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Analysis slot occupied"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_run_patch2vuln_raises_on_non_200_without_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(500, "not json")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="status 500"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_run_patch2vuln_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> None:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="timed out"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_run_patch2vuln_raises_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Could not reach"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_run_patch2vuln_rejects_missing_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(200, {"draft": True})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(TypeError, match="did not include any records"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_run_patch2vuln_rejects_invalid_record_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(200, {"records": {"cve": {"dataType": "wrong"}}})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Invalid Patch2Vuln record"):
        patch2vuln.run_patch2vuln(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_get_patch2vuln_config_reads_toml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text(
        "[panels.patch2vuln]\n"
        "enabled = true\n"
        'api_url = "https://patch2vuln.internal/"\n'
        'api_token = "from-toml"\n'
        "timeout_seconds = 120\n"
        'models = ["model-a", "model-b"]\n',
    )

    monkeypatch.setattr(patch2vuln, "CONFIG_PATH", real_path)
    monkeypatch.delenv("PATCH2VULN_API_TOKEN", raising=False)
    patch2vuln.get_patch2vuln_config.cache_clear()

    config = patch2vuln.get_patch2vuln_config()

    # Trailing slash stripped so f"{api_url}/api/v1/advisories" never
    # ends up with a doubled slash.
    assert config.api_url == "https://patch2vuln.internal"
    assert config.api_token == "from-toml"
    assert config.timeout_seconds == 120
    assert config.models == ("model-a", "model-b")

    patch2vuln.get_patch2vuln_config.cache_clear()


def test_get_patch2vuln_config_env_token_overrides_toml(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    real_path = tmp_path / "vulniverse.toml"
    real_path.write_text(
        '[panels.patch2vuln]\napi_token = "from-toml"\n',
    )

    monkeypatch.setattr(patch2vuln, "CONFIG_PATH", real_path)
    monkeypatch.setenv("PATCH2VULN_API_TOKEN", "from-env")
    patch2vuln.get_patch2vuln_config.cache_clear()

    config = patch2vuln.get_patch2vuln_config()

    assert config.api_token == "from-env"

    patch2vuln.get_patch2vuln_config.cache_clear()
