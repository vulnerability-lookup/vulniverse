"""Reading CVE/GCVE records tolerantly, for the conversions to CSAF and OSV:
wrong types read as empty, as drafts may be incomplete."""

from __future__ import annotations

import re
from typing import Any

# "CWE-79 Improper Neutralization …", "CWE-79: …", "CWE-79 - …"
CWE_IN_TEXT = re.compile(r"^\s*CWE-(\d+)\b\s*[:\-–]?\s*")


def obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def dicts(value: Any) -> list[dict[str, Any]]:
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def english(entries: Any) -> str:
    """The English ``value`` of a CVE descriptions/solutions list, else the first."""
    items = [entry for entry in dicts(entries) if text(entry.get("value"))]
    english_items = [
        entry for entry in items if text(entry.get("lang")).startswith("en")
    ]
    return text((english_items or items or [{}])[0].get("value"))


def cna(record: dict[str, Any]) -> dict[str, Any]:
    return obj(obj(record.get("containers")).get("cna"))


def vulnerability_ids(record: dict[str, Any]) -> tuple[str, list[str]]:
    """(CVE ID or "", [GCVE IDs]) of a CVE/GCVE record."""
    metadata = obj(record.get("cveMetadata"))
    gcve_ids = [
        vuln_id
        for vuln_id in dict.fromkeys(
            [text(entry.get("vulnId")) for entry in dicts(cna(record).get("x_gcve"))]
            + [text(metadata.get("vulnId"))]
        )
        if vuln_id
    ]
    return text(metadata.get("cveId")), gcve_ids


def is_range(version: dict[str, Any]) -> bool:
    """Whether a CVE version entry is a range (it has an upper bound)."""
    return bool(text(version.get("lessThan")) or text(version.get("lessThanOrEqual")))


def stretches(version: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    """A CVE version range as (status, start, less_than, less_or_equal)
    stretches, following its ``changes`` (e.g. Log4Shell: affected from
    2.0-beta9, unaffected at 2.3.1, affected again at 2.4, …). A wildcard
    bound ("*", "log4j-core*") is open-ended, and a start that isn't a
    version (it has spaces) is no lower bound: ""."""

    def bound(value: str) -> str:
        return "" if "*" in value else value

    status = text(version.get("status"))
    start = text(version.get("version"))
    # Some records put a product name in "version" (CVE-2021-45046:
    # "Apache Log4j2"); a version never has spaces, so: no lower bound.
    if re.search(r"\s", start):
        start = ""
    result = []

    for change in dicts(version.get("changes")):
        at = text(change.get("at"))
        if at:
            result.append((status, start, at, ""))
            start, status = at, text(change.get("status")) or status

    result.append(
        (
            status,
            start,
            bound(text(version.get("lessThan"))),
            bound(text(version.get("lessThanOrEqual"))),
        )
    )
    return result


def cwes(cna: dict[str, Any]) -> list[tuple[str, str]]:
    """(number, name) of every CWE in a record's problem types. The number
    comes from ``cweId``, or, in older records without one, from a leading
    "CWE-79" in the description; the name is the rest of that text
    (possibly empty)."""
    found: dict[str, str] = {}

    for problem in dicts(cna.get("problemTypes")):
        for entry in dicts(problem.get("descriptions")):
            description = text(entry.get("description"))
            match = CWE_IN_TEXT.match(description)
            cwe_id = text(entry.get("cweId")).removeprefix("CWE-")
            number = cwe_id if cwe_id.isdigit() else match[1] if match else ""
            if number and number not in found:
                found[number] = CWE_IN_TEXT.sub("", description, count=1).strip()

    return list(found.items())
