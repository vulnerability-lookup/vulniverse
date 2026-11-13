"""Building CSAF 2.1 advisories from other formats.

- :func:`csaf_cwes` turns a CWE ID and name into CSAF 2.1's ``cwes`` entry,
  which needs the CWE release the name belongs to (mandatory test 6.1.11).
- :func:`csaf_from_cve` drafts a CSAF advisory from a CVE or GCVE record
  (the "Create CSAF advisory" action).
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from .csaf_mandatory.scores import cwe_release
from .cve_fields import cna as cna_of
from .cve_fields import dicts, english, obj, text, vulnerability_ids

CSAF_SCHEMA_URL = "https://docs.oasis-open.org/csaf/csaf/v2.1/schema/csaf.json"

CVE_ID = re.compile(r"^CVE-\d{4}-\d{4,}$")
CWE_PREFIX = re.compile(r"^CWE-(\d+)\s*[:\-–]?\s*")

# CVE version status -> CSAF product status.
PRODUCT_STATUS = {
    "affected": "known_affected",
    "unaffected": "known_not_affected",
    "unknown": "under_investigation",
}

# CVE metrics -> CSAF metric content (FIRST's CVSS objects in both).
CVSS_KEYS = (
    ("cvssV4_0", "cvss_v4"),
    ("cvssV3_1", "cvss_v3"),
    ("cvssV3_0", "cvss_v3"),
    ("cvssV2_0", "cvss_v2"),
)

# CVE versionType -> VERS scheme. Anything else is "generic".
VERS_SCHEMES = {"semver": "semver", "maven": "maven", "pypi": "pypi", "npm": "npm"}


def csaf_cwes(cwe_id: Any, name: Any) -> list[dict[str, Any]]:
    """``[{"id": "CWE-79", "name": ..., "version": ...}]``, or [] when the ID
    or name is unusable or the CWE was never a weakness."""
    number = str(cwe_id).removeprefix("CWE-")

    if not number.isdigit() or not isinstance(name, str) or not name:
        return []

    version = cwe_release(number, name)
    return (
        [{"id": f"CWE-{number}", "name": name, "version": version}] if version else []
    )


def _version_range(version: dict[str, Any]) -> str | None:
    """A CVE version range as a VERS range, or None for a single version."""
    start = text(version.get("version"))
    less_than = text(version.get("lessThan"))
    less_or_equal = text(version.get("lessThanOrEqual"))

    if not less_than and not less_or_equal:
        return "vers:all/*" if start in ("*", "") else None

    constraints = []
    if start not in ("", "0", "*"):
        constraints.append(f">={start}")
    if less_than and less_than != "*":
        constraints.append(f"<{less_than}")
    if less_or_equal and less_or_equal != "*":
        constraints.append(f"<={less_or_equal}")

    if not constraints:
        return "vers:all/*"

    scheme = VERS_SCHEMES.get(text(version.get("versionType")).lower(), "generic")
    return f"vers:{scheme}/{'|'.join(constraints)}"


class _Products:
    """The product tree being built, with the product IDs per status."""

    def __init__(self) -> None:
        self.vendors: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.status: dict[str, list[str]] = {}
        self.count = 0

    def add(
        self, vendor: str, product: str, version: str | None, category: str, status: str
    ) -> None:
        self.count += 1
        product_id = f"CSAFPID-{self.count:04d}"
        name = " ".join(part for part in (vendor, product, version) if part)
        leaf: dict[str, Any] = {"name": name, "product_id": product_id}
        branches = self.vendors.setdefault(vendor, {}).setdefault(product, [])
        branches.append(
            {"category": category, "name": version, "product": leaf}
            if version
            else {"product": leaf}
        )
        self.status.setdefault(
            PRODUCT_STATUS.get(status, "under_investigation"), []
        ).append(product_id)

    def tree(self) -> dict[str, Any]:
        vendors = []
        for vendor, products in self.vendors.items():
            names = []
            for product, entries in products.items():
                # A product without versions sits on its product_name branch.
                if len(entries) == 1 and "category" not in entries[0]:
                    names.append(
                        {"category": "product_name", "name": product, **entries[0]}
                    )
                else:
                    names.append(
                        {
                            "category": "product_name",
                            "name": product,
                            "branches": entries,
                        }
                    )
            vendors.append({"category": "vendor", "name": vendor, "branches": names})
        return {"branches": vendors} if vendors else {}


def _products(cna: dict[str, Any]) -> _Products:
    products = _Products()

    for affected in dicts(cna.get("affected")):
        vendor = text(affected.get("vendor")) or "unknown vendor"
        product = (
            text(affected.get("product"))
            or text(affected.get("packageName"))
            or "unknown product"
        )
        versions = dicts(affected.get("versions"))

        if not versions:
            products.add(
                vendor,
                product,
                None,
                "",
                text(affected.get("defaultStatus")) or "affected",
            )
            continue

        for version in versions:
            version_range = _version_range(version)
            status = text(version.get("status"))
            if version_range:
                products.add(
                    vendor, product, version_range, "product_version_range", status
                )
            else:
                products.add(
                    vendor,
                    product,
                    text(version.get("version")),
                    "product_version",
                    status,
                )

    return products


def csaf_from_cve(
    record: dict[str, Any], now: datetime | None = None
) -> dict[str, Any]:
    """A CSAF 2.1 draft (status draft, version 0.1.0) from a CVE/GCVE record.

    The advisory's own fields (tracking ID, publisher namespace) are left
    for the author: an advisory ID names the advisory, not the
    vulnerability, and the record doesn't know the publisher's URI.
    GCVE's x_gcve has no place in CSAF and is not carried over.
    """
    date = (
        (now or datetime.now(UTC))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    cna = cna_of(record)
    cve_id, gcve_ids = vulnerability_ids(record)
    source_id = gcve_ids[0] if gcve_ids else cve_id or "the record"

    description = english(cna.get("descriptions"))
    title = text(cna.get("title")) or (description[:120] if description else "")
    products = _products(cna)
    affected = products.status.get("known_affected", [])

    vulnerability: dict[str, Any] = {}
    if CVE_ID.match(cve_id):
        vulnerability["cve"] = cve_id
    if gcve_ids:
        vulnerability["ids"] = [
            {"system_name": "GCVE", "text": vuln_id} for vuln_id in gcve_ids
        ]
    if title:
        vulnerability["title"] = title
    if description:
        vulnerability["notes"] = [
            {
                "category": "description",
                "title": "Vulnerability description",
                "text": description,
            }
        ]
    if text(cna.get("datePublic")):
        vulnerability["disclosure_date"] = cna["datePublic"]
    if products.status:
        vulnerability["product_status"] = products.status

    cwes: list[dict[str, Any]] = []
    for problem in dicts(cna.get("problemTypes")):
        for entry in dicts(problem.get("descriptions")):
            cwe_id = text(entry.get("cweId"))
            name = CWE_PREFIX.sub("", text(entry.get("description")))
            for cwe in csaf_cwes(cwe_id, name):
                if cwe["id"] not in {existing["id"] for existing in cwes}:
                    cwes.append(cwe)
    if cwes:
        vulnerability["cwes"] = cwes

    metrics = []
    for metric in dicts(cna.get("metrics")):
        for cve_key, csaf_key in CVSS_KEYS:
            if isinstance(metric.get(cve_key), dict) and affected:
                metrics.append(
                    {"content": {csaf_key: metric[cve_key]}, "products": affected}
                )
    if metrics:
        vulnerability["metrics"] = metrics

    remediations = []
    for key, category in (("solutions", "vendor_fix"), ("workarounds", "workaround")):
        details = english(cna.get(key))
        if details and affected:
            remediations.append(
                {"category": category, "details": details, "product_ids": affected}
            )
    if remediations:
        vulnerability["remediations"] = remediations

    references = [
        {
            "category": "external",
            "url": reference["url"],
            "summary": text(reference.get("name")) or reference["url"],
        }
        for reference in dicts(cna.get("references"))
        if text(reference.get("url"))
    ]
    if references:
        vulnerability["references"] = references

    acknowledgments = [
        {
            "names": [text(credit.get("value"))],
            **(
                {"summary": text(credit.get("type")).replace("_", " ")}
                if text(credit.get("type"))
                else {}
            ),
        }
        for credit in dicts(cna.get("credits"))
        if text(credit.get("value"))
    ]
    if acknowledgments:
        vulnerability["acknowledgments"] = acknowledgments

    provider = obj(cna.get("providerMetadata"))

    document: dict[str, Any] = {
        "$schema": CSAF_SCHEMA_URL,
        "document": {
            "category": "csaf_base",
            "csaf_version": "2.1",
            "distribution": {"tlp": {"label": "CLEAR"}},
            "lang": "en",
            "publisher": {
                "category": "vendor",
                "name": text(provider.get("shortName")),
                "namespace": "",
            },
            "title": title,
            "tracking": {
                "id": "",
                "status": "draft",
                "version": "0.1.0",
                "initial_release_date": date,
                "current_release_date": date,
                "revision_history": [
                    {
                        "date": date,
                        "number": "0.1.0",
                        "summary": f"Initial draft from {source_id}.",
                    }
                ],
            },
        },
    }
    if products.vendors:
        document["product_tree"] = products.tree()
    if vulnerability:
        document["vulnerabilities"] = [vulnerability]

    return document
