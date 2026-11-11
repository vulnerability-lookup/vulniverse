"""The CSAF 2.1 profile: validation, identifier and records."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from vulniverse_api.services.identifiers import extract_identifier
from vulniverse_api.services.record_validation import validate_record

PROFILE = "csaf-2.1"

# Official example of the CSAF 2.1 tag the schemas are vendored from.
FIXTURE = Path(__file__).parent / "fixtures" / "csaf" / "bsi-2022-0001.json"


@pytest.fixture
def advisory() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(FIXTURE.read_text())
    return document


def errors(document: dict[str, Any]) -> list[tuple[str, str]]:
    return [
        ("/".join(map(str, error["path"])), error["message"])
        for error in validate_record(document, PROFILE)
        if error.get("severity", "error") == "error"
    ]


def test_the_official_example_is_valid(advisory: dict[str, Any]) -> None:
    assert errors(advisory) == []


def test_the_identifier_is_the_tracking_id(advisory: dict[str, Any]) -> None:
    assert extract_identifier(advisory, PROFILE) == "BSI-2022-0001"


def test_the_schema_url_is_fixed(advisory: dict[str, Any]) -> None:
    # What patch2vuln currently writes; CSAF 2.1 requires schema/csaf.json.
    advisory["$schema"] = "https://docs.oasis-open.org/csaf/csaf/v2.1/csaf_json_schema.json"

    assert [path for path, _ in errors(advisory)] == ["$schema"]


def test_cvss_v3_is_checked_against_firsts_schema(advisory: dict[str, Any]) -> None:
    advisory["vulnerabilities"][0]["metrics"][0]["content"]["cvss_v3"]["baseSeverity"] = "BOGUS"

    assert "vulnerabilities/0/metrics/0/content/cvss_v3/baseSeverity" in [path for path, _ in errors(advisory)]


def test_cvss_v4_is_checked_against_firsts_schema(advisory: dict[str, Any]) -> None:
    metric = copy.deepcopy(advisory["vulnerabilities"][0]["metrics"][0])
    metric["content"] = {"cvss_v4": {
        "version": "4.0",
        "vectorString": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H/SC:N/SI:N/SA:N",
        "baseScore": 9.3,
        "baseSeverity": "CRITICAL",
    }}
    advisory["vulnerabilities"][0]["metrics"].append(metric)

    assert errors(advisory) == []

    metric["content"]["cvss_v4"]["vectorString"] = "not a vector"

    assert any("cvss_v4/vectorString" in path for path, _ in errors(advisory))


def test_distribution_is_required(advisory: dict[str, Any]) -> None:
    del advisory["document"]["distribution"]

    assert errors(advisory) == [("document", "'distribution' is a required property")]


def test_a_csaf_advisory_is_published_under_its_tracking_id(client, advisory: dict[str, Any]) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": advisory, "profile": PROFILE, "isDraft": False},
    )

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["identifier"] == "BSI-2022-0001"


def test_an_incomplete_csaf_draft_can_be_saved(client) -> None:
    response = client.post(
        "/api/v1/records",
        json={"record": {"document": {"title": ""}}, "profile": PROFILE, "isDraft": True},
    )

    assert response.status_code == 201
    assert response.get_json()["identifier"] is None


def test_an_invalid_csaf_advisory_is_not_published(client, advisory: dict[str, Any]) -> None:
    del advisory["document"]["distribution"]

    response = client.post(
        "/api/v1/records",
        json={"record": advisory, "profile": PROFILE, "isDraft": False},
    )

    assert response.status_code == 422
