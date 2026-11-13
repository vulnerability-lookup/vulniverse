"""Drafting a CSAF 2.1 advisory from a CVE/GCVE record."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from vulniverse_api.services.csaf_convert import csaf_from_cve
from vulniverse_api.services.record_validation import validate_record

FIXTURE = Path(__file__).parent / "fixtures" / "convert" / "gcve-record.json"
NOW = datetime(2026, 11, 13, 10, 0, 0, 123456, tzinfo=UTC)


@pytest.fixture
def record() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(FIXTURE.read_text())
    return document


@pytest.fixture
def advisory(record: dict[str, Any]) -> dict[str, Any]:
    return csaf_from_cve(record, NOW)


def products(advisory: dict[str, Any]) -> dict[str, str]:
    """{product_id: name} of every product in the tree."""
    found: dict[str, str] = {}

    def walk(branches: list[dict[str, Any]]) -> None:
        for branch in branches:
            if "product" in branch:
                found[branch["product"]["product_id"]] = branch["product"]["name"]
            walk(branch.get("branches", []))

    walk(advisory["product_tree"]["branches"])
    return found


def test_the_draft_is_valid_once_the_author_fills_in_the_advisory_fields(
    advisory: dict[str, Any],
) -> None:
    # Left empty on purpose: the advisory ID and the publisher's URI.
    advisory["document"]["tracking"]["id"] = "EXAMPLE-2026-0001"
    advisory["document"]["publisher"]["namespace"] = "https://example.com"

    errors = [
        f"{'/'.join(map(str, e['path']))}: {e['message']}"
        for e in validate_record(advisory, "csaf-2.1")
        if e["severity"] == "error"
    ]

    assert errors == []


def test_the_draft_is_a_fresh_unreleased_advisory(advisory: dict[str, Any]) -> None:
    tracking = advisory["document"]["tracking"]

    assert tracking == {
        "id": "",
        "status": "draft",
        "version": "0.1.0",
        "initial_release_date": "2026-11-13T10:00:00Z",
        "current_release_date": "2026-11-13T10:00:00Z",
        "revision_history": [
            {
                "date": "2026-11-13T10:00:00Z",
                "number": "0.1.0",
                "summary": "Initial draft from GCVE-1-2026-00042.",
            }
        ],
    }
    assert advisory["document"]["title"] == "Stored XSS in Example Widget comment form"
    assert advisory["document"]["publisher"]["name"] == "Example CERT"


def test_versions_keep_their_status_and_ranges(advisory: dict[str, Any]) -> None:
    names = products(advisory)
    status = advisory["vulnerabilities"][0]["product_status"]

    assert [names[i] for i in status["known_affected"]] == [
        "Example Widget vers:semver/>=1.0.0|<1.3.0",
        "Example Widget 0.9.5",
        "Example Widget Cloud",
    ]
    assert [names[i] for i in status["known_not_affected"]] == ["Example Widget 1.3.0"]


def test_vulnerability_details(advisory: dict[str, Any]) -> None:
    vulnerability = advisory["vulnerabilities"][0]
    affected = vulnerability["product_status"]["known_affected"]

    assert vulnerability["cve"] == "CVE-2026-12345"
    assert vulnerability["ids"] == [
        {"system_name": "GCVE", "text": "GCVE-1-2026-00042"}
    ]
    assert vulnerability["disclosure_date"] == "2026-11-10T08:00:00.000Z"
    # "CWE-79 <name>" in CVE; CSAF wants the bare name and its CWE release.
    assert vulnerability["cwes"] == [
        {
            "id": "CWE-79",
            "name": "Improper Neutralization of Input During Web Page Generation",
            "version": "5.0",
        }
    ]
    assert [list(metric["content"]) for metric in vulnerability["metrics"]] == [
        ["cvss_v3"],
        ["cvss_v4"],
    ]
    assert all(metric["products"] == affected for metric in vulnerability["metrics"])
    assert [r["category"] for r in vulnerability["remediations"]] == [
        "vendor_fix",
        "workaround",
    ]
    assert vulnerability["references"][1] == {
        "category": "external",
        "url": "https://example.com/advisory",
        "summary": "https://example.com/advisory",
    }
    assert vulnerability["acknowledgments"] == [
        {"names": ["Jane Doe"], "summary": "finder"}
    ]


def test_an_empty_record_gives_a_bare_draft() -> None:
    advisory = csaf_from_cve({}, NOW)

    assert "vulnerabilities" not in advisory
    assert "product_tree" not in advisory
    assert advisory["document"]["tracking"]["revision_history"][0]["summary"] == (
        "Initial draft from the record."
    )


def test_the_endpoint_converts_without_saving(client, record: dict[str, Any]) -> None:
    response = client.post(
        "/api/v1/convert/csaf", json={"record": record, "profile": "gcve-bcp-05-1.7"}
    )

    assert response.status_code == 200
    assert response.get_json()["profile"] == "csaf-2.1"
    assert (
        response.get_json()["record"]["vulnerabilities"][0]["cve"] == "CVE-2026-12345"
    )

    response = client.post(
        "/api/v1/convert/csaf", json={"record": record, "profile": "osv-1.9.2"}
    )

    assert response.status_code == 400
