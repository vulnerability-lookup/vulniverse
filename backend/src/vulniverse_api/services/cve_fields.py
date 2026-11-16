"""Reading CVE/GCVE records tolerantly, for the conversions to CSAF and OSV:
wrong types read as empty, as drafts may be incomplete."""

from __future__ import annotations

from typing import Any


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
    bound ("*", "log4j-core*") is open-ended: ""."""

    def bound(value: str) -> str:
        return "" if "*" in value else value

    status = text(version.get("status"))
    start = text(version.get("version"))
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
