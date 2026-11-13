"""patch2vuln's CSAF output, converted to valid CSAF 2.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from vulniverse_api.services import patch2vuln
from vulniverse_api.services.csaf_mandatory.scores import cwe_release
from vulniverse_api.services.patch2vuln import CSAF_SCHEMA_URL, csaf_from_patch2vuln
from vulniverse_api.services.record_validation import validate_record

# What patch2vuln's build_csaf_record produces (gcve-lab-patch2vuln
# ef328ff): CSAF 2.0's $schema URL, cwe and scores in a 2.1 document.
FIXTURE = Path(__file__).parent / "fixtures" / "patch2vuln" / "csaf-record.json"

XSS = "Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')"


@pytest.fixture
def generated() -> dict[str, Any]:
    record: dict[str, Any] = json.loads(FIXTURE.read_text())
    return record


def errors(document: dict[str, Any]) -> list[str]:
    return [
        f"{'/'.join(map(str, error['path']))}: {error['message']}"
        for error in validate_record(document, "csaf-2.1")
        if error["severity"] == "error"
    ]


def test_the_raw_output_is_not_csaf_2_1(generated: dict[str, Any]) -> None:
    assert errors(generated)


def test_the_converted_output_passes_schema_and_mandatory_tests(
    generated: dict[str, Any],
) -> None:
    assert errors(csaf_from_patch2vuln(generated)) == []


def test_conversion_moves_2_0_fields(generated: dict[str, Any]) -> None:
    vulnerability = csaf_from_patch2vuln(generated)["vulnerabilities"][0]
    original = generated["vulnerabilities"][0]

    assert "scores" not in vulnerability
    assert "cwe" not in vulnerability
    assert vulnerability["metrics"] == [
        {
            "content": {"cvss_v4": original["scores"][0]["cvss_v4"]},
            "products": ["CSAFPID-0001", "CSAFPID-0002"],
        }
    ]
    # The newest release with patch2vuln's name; 4.21 renamed CWE-79.
    assert vulnerability["cwes"] == [{"id": "CWE-79", "name": XSS, "version": "4.20"}]


def test_conversion_fixes_the_schema_url_and_drops_nulls(
    generated: dict[str, Any],
) -> None:
    generated["document"]["notes"][0]["title"] = None

    converted = csaf_from_patch2vuln(generated)

    assert converted["$schema"] == CSAF_SCHEMA_URL
    assert "title" not in converted["document"]["notes"][0]


def test_conversion_keeps_2_1_fields() -> None:
    document = {
        "vulnerabilities": [
            {"metrics": [{"content": {}}], "scores": [{"products": []}], "cwes": []}
        ]
    }

    vulnerability = csaf_from_patch2vuln(document)["vulnerabilities"][0]

    assert vulnerability == {"metrics": [{"content": {}}], "cwes": []}


def test_cwe_release_prefers_a_release_with_the_same_name() -> None:
    # CWE-79 was renamed in 4.21: the old name belongs to 4.20.
    assert cwe_release("79", XSS) == "4.20"
    assert cwe_release("79", "Improper Neutralization of Input During Web Page Generation") == "5.0"
    # No release has this name: the newest one, so 6.1.11 shows the real name.
    assert cwe_release("79", "Some other name") == "5.0"
    assert cwe_release("999999", "Unknown") is None


def test_cvss_scores_are_checked_exactly() -> None:
    # 5.3 / 0.1 is 52.999… in floating point; FIRST's CVSS 4.0 schema
    # says multipleOf 0.1, so a third of all valid scores used to fail.
    from vulniverse_api.services.record_validation import validator_class_for

    validator = validator_class_for({"type": "number", "multipleOf": 0.1})({"type": "number", "multipleOf": 0.1})

    assert [score / 10 for score in range(101) if not validator.is_valid(score / 10)] == []
    assert not validator.is_valid(5.35)


def test_get_job_result_passes_the_converted_csaf_record(
    monkeypatch: pytest.MonkeyPatch, generated: dict[str, Any]
) -> None:
    from test_patch2vuln import VALID_CVE_RECORD, FakeResponse, enabled_config

    monkeypatch.setattr(patch2vuln, "get_patch2vuln_config", enabled_config)
    monkeypatch.setattr(
        patch2vuln.httpx,
        "get",
        lambda url, *, headers, timeout: FakeResponse(
            200,
            {"records": {"cve": copy.deepcopy(VALID_CVE_RECORD), "csaf": generated}},
        ),
    )

    result = patch2vuln.get_job_result("job-123")

    assert result["csaf"]["$schema"] == CSAF_SCHEMA_URL
    assert "metrics" in result["csaf"]["vulnerabilities"][0]
