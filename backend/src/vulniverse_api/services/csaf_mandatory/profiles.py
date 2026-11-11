"""Mandatory tests: Profile tests (6.1.27.x): what each document category must contain.

Each test applies only to the `$.document.category` values the spec lists for it
(compared exactly; any other value falls back to the CSAF Base profile).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from .core import Issue, Path, get, group_members, mandatory, select, strings

_VEX_STATUSES = (
    "fixed",
    "known_affected",
    "known_not_affected",
    "under_investigation",
)


def _category(document: dict[str, Any], *categories: str) -> str | None:
    """The document category if it is one of ``categories``, else None."""
    category = get(document, "document", "category")
    return category if category in categories else None


def _english(document: dict[str, Any]) -> bool:
    """The document language is English or unspecified."""
    lang = get(document, "document", "lang")
    return not isinstance(lang, str) or lang.split("-")[0].lower() == "en"


def _vulnerabilities(document: dict[str, Any]) -> Iterator[tuple[Path, Any]]:
    return (
        (path, vulnerability)
        for path, vulnerability in select(document, "$.vulnerabilities[*]")
        if isinstance(vulnerability, dict)
    )


def _dicts(value: Any) -> list[tuple[int, dict[str, Any]]]:
    if not isinstance(value, list):
        return []
    return [(index, item) for index, item in enumerate(value) if isinstance(item, dict)]


def _products_of(document: dict[str, Any], items: Iterable[Any]) -> set[str]:
    """Product IDs the items name directly or through their product groups."""
    groups = group_members(document)
    products: set[str] = set()

    for item in items:
        products.update(p for _, p in strings(select(item, "$.product_ids[*]")))
        for _, group_id in strings(select(item, "$.group_ids[*]")):
            products.update(groups.get(group_id, ()))

    return products


def _has_note(document: dict[str, Any], categories: set[str]) -> bool:
    notes = get(document, "document", "notes")
    return any(
        isinstance(note.get("category"), str) and note["category"] in categories
        for _, note in _dicts(notes)
    )


@mandatory("6.1.27.1", "Document Notes")
def document_notes(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(
        document, "csaf_informational_advisory", "csaf_security_incident_response"
    )
    if category and not _has_note(
        document, {"description", "details", "general", "summary"}
    ):
        yield Issue(
            ("document", "notes"),
            f"`{category}` must have at least one document note with category "
            "`description`, `details`, `general` or `summary`",
        )


@mandatory("6.1.27.2", "Document References")
def document_references(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(
        document,
        "csaf_informational_advisory",
        "csaf_security_incident_response",
        "csaf_superseded",
    )
    references = get(document, "document", "references")
    if category and not any(
        reference.get("category") == "external" for _, reference in _dicts(references)
    ):
        yield Issue(
            ("document", "references"),
            f"`{category}` must have at least one document reference with "
            "category `external`",
        )


@mandatory("6.1.27.3", "Vulnerabilities")
def no_vulnerabilities(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(
        document, "csaf_informational_advisory", "csaf_withdrawn", "csaf_superseded"
    )
    if category and "vulnerabilities" in document:
        yield Issue(
            ("vulnerabilities",), f"`{category}` must not have `vulnerabilities`"
        )


@mandatory("6.1.27.4", "Product Tree")
def product_tree(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(
        document,
        "csaf_security_advisory",
        "csaf_vex",
        "csaf_deprecated_security_advisory",
        "csaf_vulnerability_report",
    )
    if category and "product_tree" not in document:
        yield Issue((), f"`{category}` must have a `product_tree`")


@mandatory("6.1.27.5", "Vulnerability Notes")
def vulnerability_notes(document: dict[str, Any]) -> Iterator[Issue]:
    if _category(
        document,
        "csaf_security_advisory",
        "csaf_vex",
        "csaf_deprecated_security_advisory",
    ):
        for path, vulnerability in _vulnerabilities(document):
            if "notes" not in vulnerability:
                yield Issue(path, "vulnerability must have `notes`")


@mandatory("6.1.27.6", "Product Status")
def product_status(document: dict[str, Any]) -> Iterator[Issue]:
    if _category(
        document, "csaf_security_advisory", "csaf_deprecated_security_advisory"
    ):
        for path, vulnerability in _vulnerabilities(document):
            if "product_status" not in vulnerability:
                yield Issue(path, "vulnerability must have a `product_status`")


@mandatory("6.1.27.7", "VEX Product Status")
def vex_product_status(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_vex"):
        return

    for path, vulnerability in _vulnerabilities(document):
        status = vulnerability.get("product_status")
        if not isinstance(status, dict) or not any(k in status for k in _VEX_STATUSES):
            yield Issue(
                (*path, "product_status") if isinstance(status, dict) else path,
                "product status needs at least one of `fixed`, `known_affected`, "
                "`known_not_affected`, `under_investigation`",
            )


@mandatory("6.1.27.8", "Vulnerability ID")
def vulnerability_id(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(
        document, "csaf_security_advisory", "csaf_vex", "csaf_vulnerability_report"
    ):
        return

    for path, vulnerability in _vulnerabilities(document):
        if "cve" not in vulnerability and "ids" not in vulnerability:
            yield Issue(
                path, "needs at least one of the following properties: `cve`, `ids`"
            )
            continue

        ids = vulnerability.get("ids")
        if "cve" in vulnerability or not isinstance(ids, list):
            continue
        # An id without product or group binding covers the whole vulnerability.
        if not all(
            isinstance(item, dict) and ("product_ids" in item or "group_ids" in item)
            for item in ids
        ):
            continue

        assigned = _products_of(document, ids)
        for product_path, product_id in strings(
            select(vulnerability, "$.product_status[*][*]")
        ):
            if product_id not in assigned:
                yield Issue(
                    (*path, *product_path),
                    f"product id `{product_id}` does not have a vulnerability id "
                    "assigned nor a CVE or general vulnerability id is given",
                )


def _unstated(
    document: dict[str, Any], status: str, statements: Any
) -> Iterator[tuple[Path, str]]:
    """Products in ``status`` of each vulnerability with no statement in
    ``statements(vulnerability)`` of that same vulnerability."""
    for path, vulnerability in _vulnerabilities(document):
        covered = _products_of(document, statements(vulnerability))
        for product_path, product_id in strings(
            select(vulnerability, f"$.product_status.{status}[*]")
        ):
            if product_id not in covered:
                yield (*path, *product_path), product_id


@mandatory("6.1.27.9", "Impact Statement")
def impact_statement(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_vex"):
        return

    def statements(vulnerability: dict[str, Any]) -> list[Any]:
        flags = [flag for _, flag in _dicts(vulnerability.get("flags"))]
        threats = [
            threat
            for _, threat in _dicts(vulnerability.get("threats"))
            if threat.get("category") == "impact"
        ]
        return flags + threats

    for path, product_id in _unstated(document, "known_not_affected", statements):
        yield Issue(path, f"there is no impact statement for `{product_id}`")


@mandatory("6.1.27.10", "Action Statement")
def action_statement(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_vex"):
        return

    def statements(vulnerability: dict[str, Any]) -> list[Any]:
        return [item for _, item in _dicts(vulnerability.get("remediations"))]

    for path, product_id in _unstated(document, "known_affected", statements):
        yield Issue(path, f"there is no action statement for `{product_id}`")


@mandatory("6.1.27.11", "Vulnerabilities")
def vulnerabilities(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(
        document,
        "csaf_security_advisory",
        "csaf_vex",
        "csaf_deprecated_security_advisory",
        "csaf_vulnerability_report",
    )
    if category and "vulnerabilities" not in document:
        yield Issue((), f"`{category}` must have `vulnerabilities`")


@mandatory("6.1.27.12", "Affected Products")
def affected_products(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_security_advisory"):
        return

    for path, vulnerability in _vulnerabilities(document):
        status = vulnerability.get("product_status")
        if not isinstance(status, dict):
            yield Issue(path, "vulnerability must have `product_status/known_affected`")
        elif "known_affected" not in status:
            yield Issue(
                (*path, "product_status"), "product status must have `known_affected`"
            )


# 6.1.27.13 (Corresponding Affected Products) is not implemented: the spec does
# not define when two products are "corresponding versions" beyond a hint for
# `installed_with` product paths.


@mandatory("6.1.27.14", "Document Notes")
def withdrawn_superseded_notes(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(document, "csaf_withdrawn", "csaf_superseded")
    if category and not _has_note(document, {"description"}):
        yield Issue(
            ("document", "notes"),
            f"`{category}` must have at least one document note with category "
            "`description`",
        )


@mandatory("6.1.27.15", "Product Tree")
def no_product_tree(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(document, "csaf_withdrawn", "csaf_superseded")
    if category and "product_tree" in document:
        yield Issue(("product_tree",), f"`{category}` must not have a `product_tree`")


@mandatory("6.1.27.16", "Revision History")
def revision_history(document: dict[str, Any]) -> Iterator[Issue]:
    category = _category(document, "csaf_withdrawn", "csaf_superseded")
    # A missing history counts as empty; another type is the schema's concern.
    history = get(document, "document", "tracking", "revision_history") or []
    if category and isinstance(history, list) and len(history) < 2:
        yield Issue(
            ("document", "tracking", "revision_history"),
            f"`{category}` must have at least two revision history entries",
        )


def _reasoning(document: dict[str, Any], category: str, title: str) -> Iterator[Issue]:
    """Exactly one document note titled ``title``, with category `description`."""
    if not _category(document, category) or not _english(document):
        return

    notes = [
        (index, note)
        for index, note in _dicts(get(document, "document", "notes"))
        if note.get("title") == title
    ]
    if not notes:
        yield Issue(("document", "notes"), f"document note `{title}` missing")
    for index, note in notes[1:]:
        yield Issue(
            ("document", "notes", index), f"document note `{title}` is not unique"
        )
    for index, note in notes[:1]:
        if note.get("category") != "description":
            yield Issue(
                ("document", "notes", index),
                f"document note `{title}` must have category `description`",
            )


@mandatory("6.1.27.17", "Reasoning for Withdrawal")
def reasoning_for_withdrawal(document: dict[str, Any]) -> Iterator[Issue]:
    return _reasoning(document, "csaf_withdrawn", "Reasoning for Withdrawal")


@mandatory("6.1.27.18", "Reasoning for Supersession")
def reasoning_for_supersession(document: dict[str, Any]) -> Iterator[Issue]:
    return _reasoning(document, "csaf_superseded", "Reasoning for Supersession")


@mandatory("6.1.27.19", "Reference to Superseding Document")
def superseding_reference(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_superseded") or not _english(document):
        return

    references = [
        (index, reference)
        for index, reference in _dicts(get(document, "document", "references"))
        if isinstance(reference.get("summary"), str)
        and reference["summary"].startswith("Superseding Document")
    ]
    if not references:
        yield Issue(
            ("document", "references"),
            "`csaf_superseded` must have at least one document reference with a "
            "summary starting with `Superseding Document` and category `external`",
        )
    for index, reference in references:
        if reference.get("category") != "external":
            yield Issue(
                ("document", "references", index),
                "the `Superseding Document` reference must have category `external`",
            )


# Vulnerability note titles and the category they require (spec 3.2.4.x,
# "Vulnerabilities Property - Notes").
_SUMMARY_NOTES = {"Vulnerability Summary": "summary", "CVE Description": "description"}


@mandatory("6.1.27.20", "Vulnerability Notes")
def vulnerability_report_notes(document: dict[str, Any]) -> Iterator[Issue]:
    if not _category(document, "csaf_vulnerability_report") or not _english(document):
        return

    for path, vulnerability in _vulnerabilities(document):
        notes = vulnerability.get("notes")
        if not any(
            isinstance(note.get("title"), str)
            and _SUMMARY_NOTES.get(note["title"]) == note.get("category")
            for _, note in _dicts(notes)
        ):
            yield Issue(
                (*path, "notes") if "notes" in vulnerability else path,
                "vulnerability needs a note `Vulnerability Summary` (category "
                "`summary`) or `CVE Description` (category `description`)",
            )
