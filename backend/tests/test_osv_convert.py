"""Drafting an OSV 1.9.2 record from a CVE/GCVE record."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from vulniverse_api.services.osv_convert import osv_from_cve, package_from_purl
from vulniverse_api.services.record_validation import validate_record

FIXTURE = Path(__file__).parent / "fixtures" / "convert" / "gcve-record.json"
NOW = datetime(2026, 11, 13, 10, 0, 0, 123456, tzinfo=UTC)


@pytest.fixture
def record() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(FIXTURE.read_text())
    return document


def errors(document: dict[str, Any]) -> list[str]:
    return [
        f"{'/'.join(map(str, e['path']))}: {e['message']}"
        for e in validate_record(document, "osv-1.9.2")
        if e["severity"] == "error"
    ]


def test_the_draft_is_valid_once_it_has_an_id(record: dict[str, Any]) -> None:
    osv = osv_from_cve(record, "PyPI", NOW)

    # Left empty: Vulniverse IDs are unique across formats, and GCVE is no
    # registered OSV database (x_ marks an unregistered one).
    assert osv["id"] == ""
    osv["id"] = "x_GCVE-1-2026-00042"

    assert errors(osv) == []


def test_fields(record: dict[str, Any]) -> None:
    osv = osv_from_cve(record, "PyPI", NOW)

    assert osv["schema_version"] == "1.9.2"
    assert osv["modified"] == "2026-11-13T10:00:00Z"
    assert osv["published"] == "2026-11-10T08:00:00.000Z"
    assert osv["aliases"] == ["GCVE-1-2026-00042", "CVE-2026-12345"]
    assert osv["summary"] == "Stored XSS in Example Widget comment form"
    assert osv["details"].startswith("The comment form in Example Widget")
    assert osv["severity"] == [
        {"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N"},
        {
            "type": "CVSS_V4",
            "score": "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:P/VC:N/VI:N/VA:N/SC:L/SI:L/SA:N",
        },
    ]
    assert osv["credits"] == [{"name": "Jane Doe", "type": "FINDER"}]
    assert osv["database_specific"] == {
        "cwe_ids": ["CWE-79"],
        "x_gcve": [{"vulnId": "GCVE-1-2026-00042", "recordType": "advisory"}],
    }


def test_affected_versions_become_ranges_and_versions(record: dict[str, Any]) -> None:
    affected = osv_from_cve(record, "PyPI", NOW)["affected"]

    assert affected == [
        {
            "package": {"ecosystem": "PyPI", "name": "Widget"},
            # 1.0.0 <= v < 1.3.0; the unaffected 1.3.0 is left out.
            "ranges": [
                {
                    "type": "SEMVER",
                    "events": [{"introduced": "1.0.0"}, {"fixed": "1.3.0"}],
                }
            ],
            "versions": ["0.9.5"],
        },
        {
            # No versions, defaultStatus affected: every version.
            "package": {"ecosystem": "PyPI", "name": "Widget Cloud"},
            "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}]}],
        },
    ]


def test_a_package_url_gives_ecosystem_and_name(record: dict[str, Any]) -> None:
    record["containers"]["cna"]["affected"][0]["packageURL"] = (
        "pkg:maven/org.example/widget@1.2.0"
    )

    affected = osv_from_cve(record, "", NOW)["affected"]

    # Without an ecosystem, only the product with a package URL is kept.
    assert [entry["package"] for entry in affected] == [
        {
            "ecosystem": "Maven",
            "name": "org.example:widget",
            "purl": "pkg:maven/org.example/widget",
        }
    ]


@pytest.mark.parametrize(
    ("purl", "package"),
    [
        (
            "pkg:pypi/django@4.2",
            {"ecosystem": "PyPI", "name": "django", "purl": "pkg:pypi/django"},
        ),
        (
            "pkg:npm/%40angular/core",
            {
                "ecosystem": "npm",
                "name": "@angular/core",
                "purl": "pkg:npm/%40angular/core",
            },
        ),
        (
            "pkg:golang/github.com/gin-gonic/gin?x=1",
            {
                "ecosystem": "Go",
                "name": "github.com/gin-gonic/gin",
                "purl": "pkg:golang/github.com/gin-gonic/gin",
            },
        ),
        ("pkg:deb/debian/openssl", None),
        ("not a purl", None),
    ],
)
def test_package_from_purl(purl: str, package: dict[str, str] | None) -> None:
    assert package_from_purl(purl) == package


def test_git_ranges_need_the_repository(record: dict[str, Any]) -> None:
    version = record["containers"]["cna"]["affected"][0]["versions"][0]
    version["versionType"] = "git"

    assert (
        osv_from_cve(record, "PyPI", NOW)["affected"][0]["ranges"][0]["type"]
        == "ECOSYSTEM"
    )

    record["containers"]["cna"]["affected"][0]["repo"] = (
        "https://github.com/example/widget"
    )
    ranges = osv_from_cve(record, "PyPI", NOW)["affected"][0]["ranges"]

    assert ranges[0]["type"] == "GIT"
    assert ranges[0]["repo"] == "https://github.com/example/widget"


def test_the_endpoint_converts_to_osv_without_saving(
    client, record: dict[str, Any]
) -> None:
    response = client.post(
        "/api/v1/convert/osv",
        json={"record": record, "profile": "cve-5.2.0", "ecosystem": "PyPI"},
    )

    assert response.status_code == 200
    assert response.get_json()["profile"] == "osv-1.9.2"
    assert (
        response.get_json()["record"]["affected"][0]["package"]["ecosystem"] == "PyPI"
    )

    assert client.post("/api/v1/convert/sbom", json={}).status_code == 404
