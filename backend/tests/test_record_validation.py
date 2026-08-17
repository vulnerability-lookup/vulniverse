from __future__ import annotations

import copy
from typing import Any

import pytest

from vulniverse_api import create_app
from vulniverse_api.services.record_validation import validate_record


def minimal_cve_record() -> dict[str, Any]:
    return {
        "dataType": "CVE_RECORD",
        "dataVersion": "5.2.0",
        "cveMetadata": {
            "cveId": "CVE-2026-00001",
            "assignerOrgId": "11111111-1111-4111-9111-111111111111",
            "state": "PUBLISHED",
        },
        "containers": {
            "cna": {
                "providerMetadata": {
                    "orgId": "11111111-1111-4111-9111-111111111111",
                },
                "descriptions": [
                    {"lang": "en", "value": "A test vulnerability description."},
                ],
                "affected": [
                    {
                        "vendor": "Acme",
                        "product": "Widget",
                        "defaultStatus": "affected",
                    },
                ],
                "references": [{"url": "https://example.com/advisory"}],
            },
        },
    }


def minimal_gcve_record(**extension_overrides: Any) -> dict[str, Any]:
    record = minimal_cve_record()
    extension: dict[str, Any] = {
        "vulnId": "GCVE-0-2026-00001",
        "recordType": "creation",
    }
    extension.update(extension_overrides)
    record["x_gcve"] = [extension]
    return record


def error_paths(errors: list[dict[str, Any]]) -> list[list[Any]]:
    return [error["path"] for error in errors]


def test_fresh_draft_without_state_gets_published_branch_errors() -> None:
    """
    A freshly created record has no cveMetadata.state yet (the user
    hasn't set it). Both the Published and Rejected root schema
    branches fail identically on that missing discriminator, so raw
    error-count alone would favor Rejected (a structurally smaller,
    less demanding schema for an incomplete document) and report
    confusing, wrong-branch feedback like "rejectedReasons is
    required" on a record nobody intends to reject.
    """
    record = {
        "dataType": "CVE_RECORD",
        "dataVersion": "5.2.0",
        "cveMetadata": {},
        "containers": {
            "cna": {"descriptions": [], "affected": [], "references": []},
        },
    }

    errors = validate_record(record, "cve-5.2.0")
    messages = [error["message"] for error in errors]

    assert any("providerMetadata" in message for message in messages)
    assert not any("rejectedReasons" in message for message in messages)
    assert not any(
        "do not match any of the regexes" in message
        for message in messages
    )


def test_valid_cve_record_passes() -> None:
    errors = validate_record(minimal_cve_record(), "cve-5.2.0")

    assert errors == []


def test_valid_gcve_record_passes() -> None:
    record = minimal_gcve_record(relationships=[
        {"destId": "CVE-2026-00002", "type": "related"},
    ])

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert errors == []


def test_bad_vuln_id_pattern_fails_at_x_gcve_path() -> None:
    record = minimal_gcve_record(vulnId="not-a-valid-id")

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert errors
    assert ["x_gcve", 0, "vulnId"] in error_paths(errors)
    assert all(error["severity"] == "error" for error in errors)


def test_mandatory_relationships_by_record_type() -> None:
    record = minimal_gcve_record(recordType="update")

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["x_gcve", 0, "relationships"] in error_paths(errors)


def test_translation_requires_language() -> None:
    record = minimal_gcve_record(
        recordType="translation",
        relationships=[{"destId": "CVE-2026-00002", "type": "related"}],
    )

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["x_gcve", 0, "language"] in error_paths(errors)


def test_unknown_relationship_type_is_a_warning_not_an_error() -> None:
    record = minimal_gcve_record(relationships=[
        {"destId": "CVE-2026-00002", "type": "unheard-of-type"},
    ])

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert errors
    assert all(error["severity"] == "warning" for error in errors)


def test_x_gcve_is_validated_at_nested_locations_too() -> None:
    record = minimal_cve_record()
    record["containers"]["cna"]["x_gcve"] = [
        {"vulnId": "not-valid", "recordType": "creation"},
    ]

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["containers", "cna", "x_gcve", 0, "vulnId"] in error_paths(errors)


def test_unknown_profile_is_rejected_by_the_api() -> None:
    app = create_app({"TESTING": True})

    with app.test_client() as client:
        response = client.post(
            "/api/v1/validate",
            json={
                "record": minimal_cve_record(),
                "profile": "not-a-real-profile",
            },
        )

    assert response.status_code == 400


def test_valid_record_is_not_mutated_by_validation() -> None:
    record = minimal_cve_record()
    original = copy.deepcopy(record)

    validate_record(record, "cve-5.2.0")

    assert record == original


def test_unknown_profile_raises_for_direct_callers() -> None:
    with pytest.raises(ValueError):
        validate_record(minimal_cve_record(), "not-a-real-profile")
