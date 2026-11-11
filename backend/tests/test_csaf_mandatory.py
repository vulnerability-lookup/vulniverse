"""The CSAF 2.1 mandatory tests against OASIS's official test documents.

tests/fixtures/csaf/mandatory holds the mandatory part of the CSAF TC's
validator test suite (oasis-tcs/csaf, csaf_2.1/test/validator/data, commit
897bac6), testcases.json listing per test the documents that must fail it
and those that must pass. Where the suite gives an expected result
(*.result.json), the reported paths must match it exactly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from vulniverse_api.services.csaf_mandatory import REGISTRY, validate_csaf_mandatory
from vulniverse_api.services.csaf_mandatory.core import pointer, select

FIXTURES = Path(__file__).parent / "fixtures" / "csaf"
SUITE = FIXTURES / "mandatory"
TESTCASES = json.loads((SUITE / "testcases.json").read_text())["tests"]
SUITE_IDS = [case["id"] for case in TESTCASES]


def load(name: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads((SUITE.parent / name).read_text())
    return document


# Official test documents that contradict the spec text. Expected to fail
# (strict: once fixed upstream, the xfail turns into an error to remove it).
# - 6.1.64.12-13, listed as valid: EID-0003 confirms actions ACN-1..3 that
#   only EID-0004 received, and ACN-3 is defined twice (failing 6.1.64.10).
KNOWN_SUITE_DEFECTS = {
    "mandatory/oasis_csaf_tc-csaf_2_1-2024-6-1-64-12-13.json",
}


def _marks(test_id: str, name: str) -> list[Any]:
    if test_id not in REGISTRY:
        return [pytest.mark.skip(reason=f"{test_id} not implemented")]
    if name in KNOWN_SUITE_DEFECTS:
        return [pytest.mark.xfail(strict=True, reason="contradicts the spec")]
    return []


def cases() -> list[Any]:
    params = []

    for case in TESTCASES:
        for expected_valid, entries in (
            (False, case["failures"]),
            (True, case.get("valid", [])),
        ):
            for entry in entries:
                params.append(
                    pytest.param(
                        case["id"],
                        entry["name"],
                        entry.get("result"),
                        expected_valid,
                        id=f"{case['id']}:{Path(entry['name']).stem.rsplit('-', 2)[-2:]}",
                        marks=_marks(case["id"], entry["name"]),
                    )
                )

    return params


@pytest.mark.parametrize(("test_id", "name", "result", "expected_valid"), cases())
def test_official_suite(
    test_id: str, name: str, result: str | None, expected_valid: bool
) -> None:
    document = load(f"mandatory/{Path(name).name}")
    # Warnings (unsupported algorithms, VERS types) don't fail a test.
    issues = [
        issue for issue in REGISTRY[test_id].run(document) if issue.severity == "error"
    ]

    if expected_valid:
        assert issues == [], f"{name} should pass {test_id}"
    else:
        assert issues, f"{name} should fail {test_id}"

    if result:
        expected = json.loads((SUITE / Path(result).name).read_text())["primary_result"]
        paths = sorted(error["instance_path"] for error in expected.get("errors", []))
        assert sorted(pointer(issue.path) for issue in issues) == paths


# Official examples that break a mandatory test, checked against the spec
# text and its official test documents (which agree with the test):
# - 6.1.36: the Red Hat examples, converted from CSAF 2.0, give vendor_fix
#   to products that are fixed or not affected; CSAF 2.1's remediation
#   table prohibits both.
# - 6.1.62: their discovery_date is after the disclosure_date.
# - 6.1.66: Cisco's initial_release_date (16:00:00Z) differs from the date
#   of revision 1.0.0 (15:17:05Z).
KNOWN_EXAMPLE_DEFECTS = {
    "rhsa-2021_5186.json": {"6.1.36", "6.1.62"},
    "rhsa-2021_5217.json": {"6.1.36", "6.1.62"},
    "rhsa-2022_0011.json": {"6.1.36", "6.1.62"},
    "cisco-sa-20180328-smi2.json": {"6.1.66"},
}


@pytest.mark.parametrize(
    "name", sorted(p.name for p in (FIXTURES / "examples").glob("*.json"))
)
def test_official_examples_pass_every_test(name: str) -> None:
    document = json.loads((FIXTURES / "examples" / name).read_text())
    failed = {
        error["test"]
        for error in validate_csaf_mandatory(document, "csaf-2.1")
        if error["severity"] == "error"
    }

    # Exactly the known defects: a new failure, or a fixed one, shows up.
    assert failed == KNOWN_EXAMPLE_DEFECTS.get(name, set())


def test_every_registered_test_is_in_the_suite() -> None:
    assert sorted(set(REGISTRY) - set(SUITE_IDS)) == []


def test_select_supports_the_spec_paths() -> None:
    document = {
        "product_tree": {
            "branches": [
                {"branches": [{"product": {"product_id": "A"}}]},
                {"product": {"product_id": "B"}},
            ]
        },
        "a/b": {"~": [1, 2]},
    }

    # Depth first: the outer branch's product before the nested one's.
    assert [
        value
        for _, value in select(
            document, "$.product_tree..branches[*].product.product_id"
        )
    ] == ["B", "A"]
    assert select(document, "$['a/b']['~'][1]") == [(("a/b", "~", 1), 2)]
    assert pointer(("a/b", "~", 1)) == "/a~1b/~0/1"
    assert select(document, "$.missing[*].x") == []
    assert select([1], "$.key") == []
