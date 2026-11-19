from __future__ import annotations

import copy
from typing import Any

import pytest

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
    record["containers"]["cna"]["x_gcve"] = [extension]
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
    assert not any("do not match any of the regexes" in message for message in messages)


def test_valid_cve_record_passes() -> None:
    errors = validate_record(minimal_cve_record(), "cve-5.2.0")

    assert errors == []


def test_valid_gcve_record_passes() -> None:
    record = minimal_gcve_record(
        relationships=[
            {"destId": "CVE-2026-00002", "type": "related"},
        ]
    )

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert errors == []


def test_bad_vuln_id_pattern_fails_at_x_gcve_path() -> None:
    record = minimal_gcve_record(vulnId="not-a-valid-id")

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert errors
    assert ["containers", "cna", "x_gcve", 0, "vulnId"] in error_paths(errors)
    assert all(error["severity"] == "error" for error in errors)


def test_mandatory_relationships_by_record_type() -> None:
    record = minimal_gcve_record(recordType="update")

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["containers", "cna", "x_gcve", 0, "relationships"] in error_paths(errors)


def test_translation_requires_language() -> None:
    record = minimal_gcve_record(
        recordType="translation",
        relationships=[{"destId": "CVE-2026-00002", "type": "related"}],
    )

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["containers", "cna", "x_gcve", 0, "language"] in error_paths(errors)


def test_unknown_relationship_type_is_a_warning_not_an_error() -> None:
    record = minimal_gcve_record(
        relationships=[
            {"destId": "CVE-2026-00002", "type": "unheard-of-type"},
        ]
    )

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


def test_legalizing_nested_x_gcve_does_not_clobber_sibling_cna_properties() -> None:
    """
    The overlay that legalizes containers.cna.x_gcve merges into the
    compiled base-schema validator's containers.properties.cna
    dict — a naive shallow update() there (rather than a recursive
    merge) would silently replace the *entire* real cna.properties
    definition with just {x_gcve: ...}, meaning every other cna field
    (affected, descriptions, etc.) would lose its real type
    constraint and stop being checked at all. Guards against that
    regression directly, independent of test_valid_gcve_record_passes
    happening to still pass for other reasons.
    """
    record = minimal_cve_record()
    record["containers"]["cna"]["x_gcve"] = [
        {"vulnId": "GCVE-0-2026-00001", "recordType": "creation"},
    ]
    record["containers"]["cna"]["affected"] = "not-an-array"

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["containers", "cna", "affected"] in error_paths(errors)


def test_validate_is_exempt_from_the_login_gate(anon_client) -> None:
    response = anon_client.post(
        "/api/v1/validate",
        json={"record": minimal_cve_record(), "profile": "cve-5.2.0"},
    )

    assert response.status_code == 200
    assert response.get_json()["valid"] is True


def test_unknown_profile_is_rejected_by_the_api(client) -> None:
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


def test_missing_required_field_is_reported_at_the_field() -> None:
    record = minimal_cve_record()
    del record["cveMetadata"]["cveId"]
    del record["containers"]["cna"]["references"][0]["url"]

    paths = [
        error["path"]
        for error in validate_record(record, "cve-5.2.0")
        if error["validator"] == "required"
    ]

    assert ["cveMetadata", "cveId"] in paths
    assert ["containers", "cna", "references", 0, "url"] in paths


# --- GCVE records don't need the CVE Program's IDs (validation.notRequired) ---


def gcve_only_record() -> dict[str, Any]:
    """A GCVE record as a GNA writes it: no CVE ID, no CVE Program org."""
    record = minimal_gcve_record(vulnId="GCVE-1-2026-0007", recordType="advisory")
    del record["cveMetadata"]["cveId"]
    del record["cveMetadata"]["assignerOrgId"]
    del record["containers"]["cna"]["providerMetadata"]
    return record


def test_a_gcve_record_needs_no_cve_id_assigner_or_provider() -> None:
    errors = validate_record(gcve_only_record(), "gcve-bcp-05-1.7")

    assert [e for e in errors if e.get("severity", "error") == "error"] == []


def test_a_gcve_record_still_needs_its_content() -> None:
    record = gcve_only_record()
    del record["containers"]["cna"]["affected"]

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["containers", "cna", "affected"] in error_paths(errors)


def test_a_cve_id_that_is_there_is_still_checked() -> None:
    record = gcve_only_record()
    record["cveMetadata"]["cveId"] = "not-a-cve-id"

    errors = validate_record(record, "gcve-bcp-05-1.7")

    assert ["cveMetadata", "cveId"] in error_paths(errors)


def test_cve_records_still_need_a_cve_id() -> None:
    record = minimal_cve_record()
    del record["cveMetadata"]["cveId"]

    errors = validate_record(record, "cve-5.2.0")

    assert ["cveMetadata", "cveId"] in error_paths(errors)
