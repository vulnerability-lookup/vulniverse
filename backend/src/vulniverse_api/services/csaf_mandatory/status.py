"""Mandatory tests: Product status, flags, remediations and per-product consistency in vulnerabilities."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .core import Issue, get, group_members, mandatory, select, strings

# Product status groups (spec 3.2.4.13); `recommended` contradicts nothing.
_STATUS_GROUPS = {
    "first_affected": "affected",
    "known_affected": "affected",
    "last_affected": "affected",
    "known_not_affected": "not affected",
    "first_fixed": "fixed",
    "fixed": "fixed",
    "under_investigation": "under investigation",
    "unknown": "unknown",
}

_VEX_JUSTIFICATION_CODES = {
    "component_not_present",
    "inline_mitigations_already_exist",
    "vulnerable_code_cannot_be_controlled_by_adversary",
    "vulnerable_code_not_in_execute_path",
    "vulnerable_code_not_present",
}

# The "prohibited" cells of the remediation combination table.
_CONTRADICTING_REMEDIATIONS = {
    frozenset(pair)
    for pair in [
        *(
            ("optional_patch", other)
            for other in (
                "workaround",
                "mitigation",
                "vendor_fix",
                "none_available",
                "fix_planned",
                "no_fix_planned",
            )
        ),
        *(
            ("none_available", other)
            for other in (
                "workaround",
                "mitigation",
                "vendor_fix",
                "fix_planned",
                "no_fix_planned",
            )
        ),
        ("vendor_fix", "fix_planned"),
        ("vendor_fix", "no_fix_planned"),
        ("fix_planned", "no_fix_planned"),
    ]
}

# The "prohibited" cells of the product status remediation combination table.
_CONTRADICTING_STATUS = {
    "workaround": {"not affected", "fixed"},
    "mitigation": {"not affected", "fixed"},
    "vendor_fix": {"not affected", "fixed"},
    "optional_patch": {"affected"},
    "none_available": {"not affected", "fixed"},
    "fix_planned": {"fixed"},
    "no_fix_planned": {"fixed"},
}


def _products(item: Any, members: dict[str, list[str]]) -> set[str]:
    """The product IDs ``item`` refers to, directly or through its groups."""
    products = {p for _, p in strings(select(item, "$.product_ids[*]"))}
    for _, group_id in strings(select(item, "$.group_ids[*]")):
        products.update(members.get(group_id, ()))
    return products


@mandatory("6.1.6", "Contradicting Product Status")
def contradicting_product_status(document: dict[str, Any]) -> Iterator[Issue]:
    for base, status in select(document, "$.vulnerabilities[*].product_status"):
        seen: dict[str, str] = {}

        for key, group in _STATUS_GROUPS.items():
            for path, product_id in strings(select(status, f"$.{key}[*]")):
                other = seen.setdefault(product_id, group)
                if other != group:
                    yield Issue(
                        (*base, *path),
                        f"product id `{product_id}` is both {other} and {group}",
                    )


@mandatory("6.1.7", "Multiple Scores with Same Version per Product")
def multiple_scores_same_version(document: dict[str, Any]) -> Iterator[Issue]:
    for base, metrics in select(document, "$.vulnerabilities[*].metrics"):
        seen: set[tuple[str, str, Any, str]] = set()

        for path, metric in select(metrics, "$[*]"):
            content = get(metric, "content")
            if not isinstance(content, dict):
                continue
            source = get(metric, "source")
            # Any cvss_v* key, also for versions CSAF doesn't define.
            versions = [
                (key, version)
                for key, score in content.items()
                if key.startswith("cvss_v")
                and isinstance(version := get(score, "version"), str)
            ]
            for product_path, product_id in strings(select(metric, "$.products[*]")):
                for key, version in versions:
                    found = (key, version, source, product_id)
                    if found in seen:
                        yield Issue(
                            (*base, *path, *product_path),
                            f"product id `{product_id}` has more than one cvss "
                            f"{version} score from the same source",
                        )
                    seen.add(found)


@mandatory("6.1.23", "Multiple Use of Same CVE")
def multiple_use_of_cve(document: dict[str, Any]) -> Iterator[Issue]:
    seen: set[str] = set()

    for path, cve in strings(select(document, "$.vulnerabilities[*].cve")):
        if cve in seen:
            yield Issue(path, f"cve `{cve}` is used in more than one vulnerability")
        seen.add(cve)


@mandatory("6.1.29", "Remediation without Product Reference")
def remediation_without_product(document: dict[str, Any]) -> Iterator[Issue]:
    for path, remediation in select(document, "$.vulnerabilities[*].remediations[*]"):
        if isinstance(remediation, dict) and not (
            "group_ids" in remediation or "product_ids" in remediation
        ):
            yield Issue(path, "remediation has neither group_ids nor product_ids")


@mandatory("6.1.32", "Flag without Product Reference")
def flag_without_product(document: dict[str, Any]) -> Iterator[Issue]:
    for path, flag in select(document, "$.vulnerabilities[*].flags[*]"):
        if isinstance(flag, dict) and not (
            "group_ids" in flag or "product_ids" in flag
        ):
            yield Issue(path, "flag has neither group_ids nor product_ids")


@mandatory("6.1.33", "Multiple Flags with VEX Justification Codes per Product")
def multiple_vex_flags(document: dict[str, Any]) -> Iterator[Issue]:
    members = group_members(document)

    for base, vulnerability in select(document, "$.vulnerabilities[*]"):
        flagged: set[str] = set()

        for path, flag in select(vulnerability, "$.flags[*]"):
            if get(flag, "label") not in _VEX_JUSTIFICATION_CODES:
                continue
            products = _products(flag, members)
            for product_id in sorted(products & flagged):
                yield Issue(
                    (*base, *path),
                    f"product id `{product_id}` has more than one vex justification "
                    "flag",
                )
            flagged |= products


@mandatory("6.1.35", "Contradicting Remediations")
def contradicting_remediations(document: dict[str, Any]) -> Iterator[Issue]:
    members = group_members(document)

    for base, vulnerability in select(document, "$.vulnerabilities[*]"):
        categories: dict[str, set[str]] = {}

        for path, remediation in select(vulnerability, "$.remediations[*]"):
            category = get(remediation, "category")
            if not isinstance(category, str):
                continue
            for product_id in sorted(_products(remediation, members)):
                earlier = categories.setdefault(product_id, set())
                for other in sorted(earlier):
                    if frozenset((category, other)) in _CONTRADICTING_REMEDIATIONS:
                        yield Issue(
                            (*base, *path),
                            f"product id `{product_id}` has contradicting "
                            f"remediations {other} and {category}",
                        )
                earlier.add(category)


# Some official examples (converted from CSAF 2.0) fail this; see
# KNOWN_EXAMPLE_DEFECTS in tests/test_csaf_mandatory.py.
@mandatory("6.1.36", "Contradicting Product Status Remediation Combination")
def contradicting_status_remediation(document: dict[str, Any]) -> Iterator[Issue]:
    members = group_members(document)

    for base, vulnerability in select(document, "$.vulnerabilities[*]"):
        groups: dict[str, set[str]] = {}
        for key, group in _STATUS_GROUPS.items():
            for _, product_id in strings(
                select(vulnerability, f"$.product_status.{key}[*]")
            ):
                groups.setdefault(product_id, set()).add(group)

        for path, remediation in select(vulnerability, "$.remediations[*]"):
            prohibited = _CONTRADICTING_STATUS.get(get(remediation, "category"), set())
            for product_id in sorted(_products(remediation, members)):
                for group in sorted(groups.get(product_id, set()) & prohibited):
                    yield Issue(
                        (*base, *path),
                        f"remediation {get(remediation, 'category')} contradicts "
                        f"product status {group} of product id `{product_id}`",
                    )
