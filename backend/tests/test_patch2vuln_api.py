from __future__ import annotations

from typing import Any

import pytest
from flask import Flask
from flask.testing import FlaskClient

from vulniverse_api import api as api_module
from vulniverse_api.api import patch2vuln as patch2vuln_api
from vulniverse_api.models import User
from vulniverse_api.services import patch2vuln as patch2vuln_service
from vulniverse_api.services.patch2vuln import Patch2VulnConfig


def enabled_config(**overrides: Any) -> Patch2VulnConfig:
    defaults: dict[str, Any] = {
        "enabled": True,
        "api_url": "https://patch2vuln.example.org",
        "api_token": None,
        "timeout_seconds": 300,
        "models": (),
    }
    defaults.update(overrides)
    return Patch2VulnConfig(**defaults)


@pytest.fixture(autouse=True)
def _enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        patch2vuln_api, "get_patch2vuln_config", enabled_config,
    )


def _token_for(app: Flask, job_id: str, user: User) -> str:
    with app.app_context():
        return patch2vuln_api._encode_job_token(job_id, str(user.id))


# --- POST /patch2vuln/jobs -------------------------------------------------


def test_create_job_requires_login(anon_client: FlaskClient) -> None:
    response = anon_client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": "[]"},
    )

    assert response.status_code == 401


def test_create_job_returns_403_when_disabled(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln_api, "get_patch2vuln_config", lambda: enabled_config(enabled=False),
    )

    response = client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": '["https://github.com/o/r/commit/abcdef1.patch"]'},
    )

    assert response.status_code == 403


def test_create_job_requires_at_least_one_input(client: FlaskClient) -> None:
    response = client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": "[]"},
    )

    assert response.status_code == 400


def test_create_job_submits_and_returns_opaque_token(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        patch2vuln_api,
        "submit_job",
        lambda sources, patches, context: {"jobId": "real-job-id", "status": "queued"},
    )

    response = client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": '["https://github.com/o/r/commit/abcdef1.patch"]'},
    )

    assert response.status_code == 202
    body = response.get_json()
    assert body["status"] == "queued"
    # The frontend-facing id is a signed token, never patch2vuln's raw id.
    assert body["jobId"] != "real-job-id"


def test_create_job_forwards_package_url_and_osv_ecosystem(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_submit(sources, patches, context):
        captured.update(context)
        return {"jobId": "real-job-id", "status": "queued"}

    monkeypatch.setattr(patch2vuln_api, "submit_job", fake_submit)

    response = client.post(
        "/api/v1/patch2vuln/jobs",
        data={
            "commitUrls": '["https://github.com/o/r/commit/abcdef1.patch"]',
            "packageUrl": " pkg:pypi/widget ",
            "osvEcosystem": "PyPI",
            "fixedVersion": "",
        },
    )

    assert response.status_code == 202
    assert captured == {"packageUrl": "pkg:pypi/widget", "osvEcosystem": "PyPI"}


def test_create_job_maps_submit_failure_to_502(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(sources: Any, patches: Any, context: Any) -> dict[str, Any]:
        raise RuntimeError("Could not reach the Patch2Vuln service")

    monkeypatch.setattr(patch2vuln_api, "submit_job", fail)

    response = client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": '["https://github.com/o/r/commit/abcdef1.patch"]'},
    )

    assert response.status_code == 502


# --- GET /patch2vuln/jobs/<token> ------------------------------------------


def test_get_job_rejects_garbage_token(client: FlaskClient) -> None:
    response = client.get("/api/v1/patch2vuln/jobs/not-a-real-token")

    assert response.status_code == 404


def test_get_job_rejects_another_users_token(
    app: Flask,
    client: FlaskClient,
    other_client: FlaskClient,
    other_user: User,
) -> None:
    token = _token_for(app, "job-123", other_user)

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 404


def test_cancel_job_returns_the_new_status(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)
    cancelled: list[str] = []

    def fake_cancel(job_id: str) -> dict:
        cancelled.append(job_id)
        return {"status": "canceled"}

    monkeypatch.setattr(patch2vuln_api, "cancel_job", fake_cancel)

    response = client.delete(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 200
    assert response.get_json() == {"jobId": token, "status": "canceled"}
    assert cancelled == ["job-123"]


def test_cancel_job_rejects_another_users_token(
    app: Flask,
    client: FlaskClient,
    other_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", other_user)
    monkeypatch.setattr(
        patch2vuln_api, "cancel_job", lambda job_id: pytest.fail("must not cancel"),
    )

    response = client.delete(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 404


def test_get_job_reports_running_status(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)

    monkeypatch.setattr(
        patch2vuln_api, "get_job_status", lambda job_id: {"status": "running"},
    )

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 200
    assert response.get_json() == {"jobId": token, "status": "running"}


def test_get_job_includes_result_once_completed(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)

    monkeypatch.setattr(
        patch2vuln_api, "get_job_status", lambda job_id: {"status": "completed"},
    )
    monkeypatch.setattr(
        patch2vuln_api,
        "get_job_result",
        lambda job_id: {"record": {"dataType": "CVE_RECORD"}, "analysis": None},
    )

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "completed"
    assert body["result"] == {"record": {"dataType": "CVE_RECORD"}, "analysis": None}


def test_get_job_surfaces_result_fetch_failure_as_failed(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)

    monkeypatch.setattr(
        patch2vuln_api, "get_job_status", lambda job_id: {"status": "completed"},
    )

    def fail(job_id: str) -> dict[str, Any]:
        raise RuntimeError("boom")

    monkeypatch.setattr(patch2vuln_api, "get_job_result", fail)

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "failed"


def test_get_job_reports_failed_status(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)

    monkeypatch.setattr(
        patch2vuln_api, "get_job_status", lambda job_id: {"status": "failed"},
    )

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}")

    assert response.status_code == 200
    assert response.get_json() == {
        "jobId": token,
        "status": "failed",
        "error": "Patch analysis failed",
    }


# --- GET /patch2vuln/jobs/<token>/events -----------------------------------


def test_events_rejects_garbage_token(client: FlaskClient) -> None:
    response = client.get("/api/v1/patch2vuln/jobs/not-a-real-token/events")

    assert response.status_code == 404


def test_events_rejects_another_users_token(
    app: Flask,
    client: FlaskClient,
    other_user: User,
) -> None:
    token = _token_for(app, "job-123", other_user)

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}/events")

    assert response.status_code == 404


def test_events_streams_status_updates(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = _token_for(app, "job-123", test_user)

    # stream_job_status() lives in the service module and calls its own
    # get_job_status directly, not the route module's imported reference.
    monkeypatch.setattr(
        patch2vuln_service, "get_job_status", lambda job_id: {"status": "completed"},
    )

    response = client.get(f"/api/v1/patch2vuln/jobs/{token}/events")

    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    body = response.get_data(as_text=True)
    assert f'"jobId": "{token}", "status": "completed"' in body


# --- [panels.patch2vuln] gating ---------------------------------------------


def test_disabled_panel_404s_every_route(
    app: Flask,
    client: FlaskClient,
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_load_app_config = api_module.load_app_config

    def patched() -> dict:
        config = dict(real_load_app_config())
        config["panels"] = {**config["panels"], "patch2vuln": False}
        return config

    monkeypatch.setattr(api_module, "load_app_config", patched)

    token = _token_for(app, "job-123", test_user)

    assert client.post(
        "/api/v1/patch2vuln/jobs",
        data={"commitUrls": '["https://github.com/o/r/commit/abcdef1.patch"]'},
    ).status_code == 404
    assert client.get(f"/api/v1/patch2vuln/jobs/{token}").status_code == 404
    assert client.get(f"/api/v1/patch2vuln/jobs/{token}/events").status_code == 404
