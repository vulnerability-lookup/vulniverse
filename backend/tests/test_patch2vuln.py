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


# --- submit_job ---------------------------------------------------------


def test_submit_job_raises_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln,
        "get_patch2vuln_config",
        lambda: enabled_config(enabled=False),
    )

    with pytest.raises(RuntimeError, match="disabled"):
        patch2vuln.submit_job([], [], {})


def test_submit_job_requires_at_least_one_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    with pytest.raises(ValueError, match="No patch inputs"):
        patch2vuln.submit_job([], [], {})


def test_submit_job_builds_request_and_returns_job_id(
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

        return FakeResponse(202, {"id": "job-123", "status": "queued"})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    result = patch2vuln.submit_job(
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

    assert result == {"jobId": "job-123", "status": "queued"}

    assert captured["url"] == "https://patch2vuln.example.org/api/v1/jobs"
    assert captured["timeout"] == patch2vuln.REQUEST_TIMEOUT_SECONDS
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


def test_submit_job_sends_bearer_token_when_configured(
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
        return FakeResponse(202, {"id": "job-123", "status": "queued"})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})

    assert captured["headers"] == {"Authorization": "Bearer secret-token"}


def test_submit_job_raises_on_non_202_with_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(
            429, {"error": {"code": "busy", "message": "Queue is full"}},
        )

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Queue is full"):
        patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_submit_job_raises_on_non_202_without_error_envelope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(500, "not json")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="status 500"):
        patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_submit_job_raises_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> None:
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="did not respond"):
        patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_submit_job_raises_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Could not reach"):
        patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})


def test_submit_job_raises_when_no_job_id_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_post(url: str, *, json: Any, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(202, {"status": "queued"})

    monkeypatch.setattr(patch2vuln.httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="did not return a job id"):
        patch2vuln.submit_job(["https://github.com/o/r/commit/abc.patch"], [], {})


# --- get_job_status ------------------------------------------------------


@pytest.mark.parametrize(
    ("remote_status", "expected"),
    [
        ("queued", "queued"),
        ("running", "running"),
        ("succeeded", "completed"),
        ("failed", "failed"),
        ("canceled", "failed"),
        ("something-unknown", "failed"),
    ],
)
def test_get_job_status_maps_remote_status(
    monkeypatch: pytest.MonkeyPatch,
    remote_status: str,
    expected: str,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        assert url == "https://patch2vuln.example.org/api/v1/jobs/job-123"
        return FakeResponse(200, {"status": remote_status})

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    assert patch2vuln.get_job_status("job-123") == {"status": expected}


def test_get_job_status_raises_lookup_error_on_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(404, {"error": {"message": "unknown job"}})

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    with pytest.raises(LookupError):
        patch2vuln.get_job_status("job-123")


def test_get_job_status_raises_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> None:
        raise httpx.ConnectError("boom")

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Could not reach"):
        patch2vuln.get_job_status("job-123")


# --- get_job_result --------------------------------------------------------


def test_get_job_result_reshapes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        assert url == "https://patch2vuln.example.org/api/v1/jobs/job-123/result"
        assert timeout == 300
        return FakeResponse(
            200,
            {
                "draft": True,
                "records": {"cve": VALID_CVE_RECORD, "analysis": {"summary": "ok"}},
            },
        )

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    assert patch2vuln.get_job_result("job-123") == {
        "record": VALID_CVE_RECORD,
        "analysis": {"summary": "ok"},
    }


def test_get_job_result_raises_lookup_error_on_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(404, {})

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    with pytest.raises(LookupError):
        patch2vuln.get_job_result("job-123")


def test_get_job_result_rejects_missing_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(200, {"draft": True})

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    with pytest.raises(TypeError, match="did not include any records"):
        patch2vuln.get_job_result("job-123")


def test_get_job_result_rejects_invalid_record_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_patch2vuln_config", enabled_config,
    )

    def fake_get(url: str, *, headers: Any, timeout: Any) -> FakeResponse:
        return FakeResponse(200, {"records": {"cve": {"dataType": "wrong"}}})

    monkeypatch.setattr(patch2vuln.httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="Invalid Patch2Vuln record"):
        patch2vuln.get_job_result("job-123")


# --- stream_job_status -----------------------------------------------------


def test_stream_job_status_stops_immediately_on_terminal_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln, "get_job_status", lambda job_id: {"status": "completed"},
    )

    events = list(patch2vuln.stream_job_status("token-abc", "job-123"))

    assert events[0] == "retry: 3000\n\n"
    assert events[1] == 'event: status\ndata: {"jobId": "token-abc", "status": "completed"}\n\n'
    assert len(events) == 2


def test_stream_job_status_polls_until_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    statuses = iter(["queued", "running", "running", "completed"])

    monkeypatch.setattr(
        patch2vuln,
        "get_job_status",
        lambda job_id: {"status": next(statuses)},
    )
    monkeypatch.setattr(patch2vuln.time, "sleep", lambda _seconds: None)

    events = list(patch2vuln.stream_job_status("token-abc", "job-123"))

    # One event per distinct status (duplicate "running" is suppressed).
    assert events == [
        "retry: 3000\n\n",
        'event: status\ndata: {"jobId": "token-abc", "status": "queued"}\n\n',
        'event: status\ndata: {"jobId": "token-abc", "status": "running"}\n\n',
        'event: status\ndata: {"jobId": "token-abc", "status": "completed"}\n\n',
    ]


def test_stream_job_status_treats_job_not_found_as_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_lookup(job_id: str) -> dict[str, Any]:
        raise LookupError("gone")

    monkeypatch.setattr(patch2vuln, "get_job_status", raise_lookup)

    events = list(patch2vuln.stream_job_status("token-abc", "job-123"))

    assert events[-1] == 'event: status\ndata: {"jobId": "token-abc", "status": "failed"}\n\n'


# --- get_patch2vuln_config (unaffected by the job-queue rewrite) -----------


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

    # Trailing slash stripped so f"{api_url}/api/v1/jobs" never ends up
    # with a doubled slash.
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
