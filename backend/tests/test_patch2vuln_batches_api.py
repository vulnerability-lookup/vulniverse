from __future__ import annotations

from typing import Any

import pytest
from flask import Flask, g
from flask.testing import FlaskClient

from vulniverse_api.api import patch2vuln_batches as batches_api
from vulniverse_api.services.patch2vuln import Patch2VulnConfig

COMMIT = "https://github.com/acme/widget/commit/abcdef1"
OTHER_COMMIT = "https://github.com/acme/widget/commit/1234567"

GENERATED = {
    "record": {"containers": {"cna": {"title": "Buffer overflow in widget"}}},
    "osv": None,
    "analysis": None,
}


class FakePatch2Vuln:
    """Patch2Vuln's jobs, as the batch API sees them through the service."""

    def __init__(self) -> None:
        self.statuses: dict[str, str] = {}
        self.submitted: list[list[list[str]]] = []
        self.canceled: list[str] = []
        self.contexts: list[dict[str, str] | None] = []
        self.unreachable = False

    def submit_bulk_jobs(
        self, groups: list[list[str]], context: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        self.submitted.append(groups)
        self.contexts.append(context)
        jobs = []
        for _group in groups:
            job_id = f"job-{len(self.statuses) + 1}"
            self.statuses[job_id] = "queued"
            jobs.append({"jobId": job_id, "status": "queued"})
        return jobs

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        if self.unreachable:
            raise RuntimeError("Could not reach the Patch2Vuln service")
        if job_id not in self.statuses:
            raise LookupError("Patch2Vuln job not found")
        return {"status": self.statuses[job_id]}

    def get_job_result(self, job_id: str) -> dict[str, Any]:
        return GENERATED

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        self.canceled.append(job_id)
        return {"status": "canceled"}


@pytest.fixture(autouse=True)
def _user_per_request(app: Flask) -> None:
    """The app fixture keeps one app context open, so Flask-Login would
    keep the first request's user for every client of a test; these tests
    use several clients to check what each organisation sees."""

    @app.before_request
    def forget_user() -> None:
        g.pop("_login_user", None)


@pytest.fixture
def patch2vuln(monkeypatch: pytest.MonkeyPatch) -> FakePatch2Vuln:
    fake = FakePatch2Vuln()
    for name in ("submit_bulk_jobs", "get_job_status", "get_job_result", "cancel_job"):
        monkeypatch.setattr(batches_api, name, getattr(fake, name))
    monkeypatch.setattr(
        batches_api,
        "get_patch2vuln_config",
        lambda: Patch2VulnConfig(
            enabled=True,
            api_url="https://patch2vuln.example.org",
            api_token=None,
            timeout_seconds=300,
        ),
    )
    return fake


def create_batch(client: FlaskClient, *urls: str | list[str]) -> dict[str, Any]:
    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={"name": "Widget fixes", "profile": "cve-5.2.0", "commitUrls": list(urls)},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def test_a_batch_queues_one_job_per_commit(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch = create_batch(client, COMMIT, OTHER_COMMIT, COMMIT, "  ")

    assert patch2vuln.submitted == [[[f"{COMMIT}.patch"], [f"{OTHER_COMMIT}.patch"]]]
    assert batch["total"] == 2
    assert batch["open"] == 2


def test_commits_of_one_vulnerability_are_analysed_together(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch = create_batch(
        client,
        COMMIT,
        [OTHER_COMMIT, COMMIT, OTHER_COMMIT, " "],
        [OTHER_COMMIT, COMMIT],
    )

    # Repeats within a group are dropped, and so is a repeated group.
    assert patch2vuln.submitted == [
        [[f"{COMMIT}.patch"], [f"{OTHER_COMMIT}.patch", f"{COMMIT}.patch"]]
    ]
    assert batch["total"] == 2
    detail = client.get(f"/api/v1/patch2vuln/batches/{batch['id']}").get_json()
    assert detail["candidates"][1]["commitUrls"] == [
        f"{OTHER_COMMIT}.patch",
        f"{COMMIT}.patch",
    ]


def test_the_analysis_context_applies_to_the_whole_batch(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={
            "name": "Widget fixes",
            "profile": "cve-5.2.0",
            "commitUrls": [COMMIT, OTHER_COMMIT],
            "context": {
                "vendor": " Acme ",
                "product": "Widget",
                "versionType": "semver",
                "fixedVersion": "",
                "prompt": "Focus on authentication.",
            },
        },
    )

    assert response.status_code == 201
    assert patch2vuln.contexts == [
        {
            "vendor": "Acme",
            "product": "Widget",
            "versionType": "semver",
            "prompt": "Focus on authentication.",
        }
    ]


@pytest.mark.parametrize(
    "context",
    [{"vendor": "x" * 201}, {"vendor": 5}, {"prompt": "a\x00b"}, ["vendor"]],
    ids=["too long", "not a string", "null character", "not an object"],
)
def test_an_invalid_analysis_context_queues_nothing(
    client: FlaskClient, patch2vuln: FakePatch2Vuln, context: Any
) -> None:
    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={
            "name": "Bad",
            "profile": "cve-5.2.0",
            "commitUrls": [COMMIT],
            "context": context,
        },
    )

    assert response.status_code == 400
    assert patch2vuln.submitted == []


@pytest.mark.parametrize(
    "commit_urls",
    [
        [[f"https://github.com/acme/widget/commit/{index:07x}" for index in range(6)]],
        [[COMMIT, 7]],
        [{"url": COMMIT}],
        COMMIT,
    ],
    ids=[
        "too many commits for one vulnerability",
        "not a URL",
        "an object",
        "not a list",
    ],
)
def test_invalid_commit_groups_queue_nothing(
    client: FlaskClient, patch2vuln: FakePatch2Vuln, commit_urls: Any
) -> None:
    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={"name": "Bad", "profile": "cve-5.2.0", "commitUrls": commit_urls},
    )

    assert response.status_code == 400
    assert patch2vuln.submitted == []


def test_invalid_commit_urls_queue_nothing(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={
            "name": "Mixed",
            "profile": "cve-5.2.0",
            "commitUrls": [COMMIT, "https://example.com/not-a-commit"],
        },
    )

    assert response.status_code == 400
    assert patch2vuln.submitted == []


def test_a_batch_has_a_maximum_size(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    urls = [f"https://github.com/acme/widget/commit/{index:07x}" for index in range(51)]

    response = client.post(
        "/api/v1/patch2vuln/batches",
        json={"name": "Too many", "profile": "cve-5.2.0", "commitUrls": urls},
    )

    assert response.status_code == 400
    assert patch2vuln.submitted == []


def test_opening_a_batch_keeps_finished_results(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT, OTHER_COMMIT)["id"]
    patch2vuln.statuses["job-1"] = "completed"
    patch2vuln.statuses["job-2"] = "running"

    batch = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()

    first, second = batch["candidates"]
    assert first["status"] == "completed"
    assert first["title"] == "Buffer overflow in widget"
    assert second["status"] == "running"

    # Patch2Vuln forgets the job; the stored result stays.
    patch2vuln.statuses.clear()
    candidate = client.get(f"/api/v1/patch2vuln/candidates/{first['id']}").get_json()
    assert candidate["result"] == GENERATED
    assert candidate["profile"] == "cve-5.2.0"


def test_a_job_patch2vuln_forgot_is_expired(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]
    patch2vuln.statuses.clear()

    batch = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()

    assert batch["candidates"][0]["status"] == "expired"


def test_an_unreachable_patch2vuln_keeps_the_last_status(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]
    patch2vuln.unreachable = True

    batch = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()

    assert batch["candidates"][0]["status"] == "queued"
    assert batch["refreshError"] == "Could not reach the Patch2Vuln service"


def test_batches_belong_to_the_organisation(
    client: FlaskClient,
    colleague_client: FlaskClient,
    other_client: FlaskClient,
    patch2vuln: FakePatch2Vuln,
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]

    assert (
        len(colleague_client.get("/api/v1/patch2vuln/batches").get_json()["batches"])
        == 1
    )
    assert other_client.get("/api/v1/patch2vuln/batches").get_json()["batches"] == []
    assert other_client.get(f"/api/v1/patch2vuln/batches/{batch_id}").status_code == 404
    assert (
        other_client.delete(f"/api/v1/patch2vuln/batches/{batch_id}").status_code == 404
    )


def test_a_candidate_becomes_one_record(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]
    patch2vuln.statuses["job-1"] = "completed"
    candidate_id = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()[
        "candidates"
    ][0]["id"]
    body = {
        "record": {"containers": {"cna": {"title": "Reviewed"}}},
        "profile": "cve-5.2.0",
        "isDraft": True,
        "candidateId": candidate_id,
    }

    created = client.post("/api/v1/records", json=body)
    again = client.post("/api/v1/records", json=body)

    assert created.status_code == 201
    assert again.status_code == 409
    assert again.get_json()["recordId"] == created.get_json()["id"]
    batch = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()
    assert batch["candidates"][0]["recordId"] == created.get_json()["id"]
    assert batch["reviewed"] == 1

    # Deleting the record makes the candidate reviewable again.
    client.delete(f"/api/v1/records/{created.get_json()['id']}")
    batch = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()
    assert batch["candidates"][0]["recordId"] is None


def test_another_organisations_candidate_is_refused(
    client: FlaskClient, other_client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]
    candidate_id = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()[
        "candidates"
    ][0]["id"]

    response = other_client.post(
        "/api/v1/records",
        json={
            "record": {"containers": {"cna": {}}},
            "profile": "cve-5.2.0",
            "isDraft": True,
            "candidateId": candidate_id,
        },
    )

    assert response.status_code == 404
    assert (
        other_client.get(f"/api/v1/patch2vuln/candidates/{candidate_id}").status_code
        == 404
    )


def test_dismissing_and_restoring_a_candidate(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT)["id"]
    candidate_id = client.get(f"/api/v1/patch2vuln/batches/{batch_id}").get_json()[
        "candidates"
    ][0]["id"]
    url = f"/api/v1/patch2vuln/candidates/{candidate_id}/dismiss"

    assert client.post(url, json={"dismissed": True}).get_json()["dismissed"] is True
    assert client.post(url, json={"dismissed": False}).get_json()["dismissed"] is False


def test_deleting_a_batch_cancels_its_open_jobs(
    client: FlaskClient, patch2vuln: FakePatch2Vuln
) -> None:
    batch_id = create_batch(client, COMMIT, OTHER_COMMIT)["id"]
    patch2vuln.statuses["job-1"] = "completed"
    client.get(f"/api/v1/patch2vuln/batches/{batch_id}")

    response = client.delete(f"/api/v1/patch2vuln/batches/{batch_id}")

    assert response.status_code == 200
    assert patch2vuln.canceled == ["job-2"]
    assert client.get(f"/api/v1/patch2vuln/batches/{batch_id}").status_code == 404
