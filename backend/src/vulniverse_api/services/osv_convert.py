"""Drafting an OSV 1.9.2 record from a CVE/GCVE record (the "Convert to…"
action).

OSV describes packages in an ecosystem (PyPI, npm, Maven, …). A product's
ecosystem and package name come from its CVE ``packageURL`` when it has
one; otherwise from the ``ecosystem`` the user picked, with the
``packageName`` or product name.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

from .cve_fields import cna as cna_of
from .cve_fields import dicts, english, obj, text, vulnerability_ids

OSV_SCHEMA_VERSION = "1.9.2"

# Package URL type -> OSV ecosystem, for the ecosystems a purl names
# without further detail. Others (deb, rpm, …) need a release suffix in
# OSV ("Debian:12"), so the user picks those.
PURL_ECOSYSTEMS = {
    "cargo": "crates.io",
    "composer": "Packagist",
    "conan": "ConanCenter",
    "cran": "CRAN",
    "gem": "RubyGems",
    "golang": "Go",
    "hackage": "Hackage",
    "hex": "Hex",
    "maven": "Maven",
    "npm": "npm",
    "nuget": "NuGet",
    "pub": "Pub",
    "pypi": "PyPI",
    "swift": "SwiftURL",
}

PURL = re.compile(r"^pkg:([a-zA-Z][a-zA-Z0-9.+-]*)/(.+)$")

# CVE versionType -> OSV range type. GIT needs the repository.
RANGE_TYPES = {"semver": "SEMVER", "git": "GIT"}

SEVERITY_TYPES = (
    ("cvssV4_0", "CVSS_V4"),
    ("cvssV3_1", "CVSS_V3"),
    ("cvssV3_0", "CVSS_V3"),
    ("cvssV2_0", "CVSS_V2"),
)

# CVE reference tags -> OSV reference type; the first match wins.
REFERENCE_TYPES = (
    ("patch", "FIX"),
    ("vendor-advisory", "ADVISORY"),
    ("third-party-advisory", "ADVISORY"),
    ("exploit", "EVIDENCE"),
    ("issue-tracking", "REPORT"),
    ("mailing-list", "DISCUSSION"),
    ("technical-description", "ARTICLE"),
    ("product", "PACKAGE"),
)

CREDIT_TYPES = {
    "finder": "FINDER",
    "reporter": "REPORTER",
    "analyst": "ANALYST",
    "coordinator": "COORDINATOR",
    "remediation developer": "REMEDIATION_DEVELOPER",
    "remediation reviewer": "REMEDIATION_REVIEWER",
    "remediation verifier": "REMEDIATION_VERIFIER",
    "tool": "TOOL",
    "sponsor": "SPONSOR",
    "other": "OTHER",
}


def package_from_purl(purl: str) -> dict[str, str] | None:
    """OSV's package (ecosystem, name, purl without version) for a package
    URL of a known ecosystem, else None."""
    match = PURL.match(purl.strip())
    if match is None:
        return None

    purl_type = match[1].lower()
    ecosystem = PURL_ECOSYSTEMS.get(purl_type)
    if ecosystem is None:
        return None

    path = match[2].split("#", 1)[0].split("?", 1)[0]
    last = path.rsplit("/", 1)[-1]
    if "@" in last:
        path = path[: path.rfind("@")]
    parts = [unquote(part) for part in path.split("/") if part]
    if not parts:
        return None

    namespace, name = "/".join(parts[:-1]), parts[-1]
    if purl_type == "maven" and namespace:
        osv_name = f"{namespace}:{name}"
    elif namespace and purl_type in ("npm", "golang", "composer", "swift"):
        osv_name = f"{namespace}/{name}"
    else:
        osv_name = name

    return {"ecosystem": ecosystem, "name": osv_name, "purl": f"pkg:{purl_type}/{path}"}


def _range(version: dict[str, Any], repo: str) -> dict[str, Any] | None:
    """A CVE version range as an OSV range, or None for a single version."""
    start = text(version.get("version"))
    less_than = text(version.get("lessThan"))
    less_or_equal = text(version.get("lessThanOrEqual"))

    if not less_than and not less_or_equal:
        return None

    range_type = RANGE_TYPES.get(text(version.get("versionType")).lower(), "ECOSYSTEM")
    if range_type == "GIT" and not repo:
        range_type = "ECOSYSTEM"

    events: list[dict[str, str]] = [
        {"introduced": start if start not in ("", "*") else "0"}
    ]
    if less_than and less_than != "*":
        events.append({"fixed": less_than})
    elif less_or_equal and less_or_equal != "*":
        events.append({"last_affected": less_or_equal})

    osv_range: dict[str, Any] = {"type": range_type, "events": events}
    if range_type == "GIT":
        osv_range["repo"] = repo
    return osv_range


def _affected(cna: dict[str, Any], ecosystem: str) -> list[dict[str, Any]]:
    result = []

    for affected in dicts(cna.get("affected")):
        package = package_from_purl(text(affected.get("packageURL")))
        if package is None:
            name = text(affected.get("packageName")) or text(affected.get("product"))
            if not ecosystem or not name:
                continue
            package = {"ecosystem": ecosystem, "name": name}

        repo = text(affected.get("repo"))
        ranges, versions = [], []
        for version in dicts(affected.get("versions")):
            if text(version.get("status")) != "affected":
                continue  # OSV only lists affected versions.
            osv_range = _range(version, repo)
            if osv_range:
                ranges.append(osv_range)
            elif text(version.get("version")) not in ("", "*"):
                versions.append(version["version"])

        if (
            not affected.get("versions")
            and text(affected.get("defaultStatus")) == "affected"
        ):
            # Every version is affected.
            ranges.append({"type": "ECOSYSTEM", "events": [{"introduced": "0"}]})

        if ranges or versions:
            entry: dict[str, Any] = {"package": package}
            if ranges:
                entry["ranges"] = ranges
            if versions:
                entry["versions"] = versions
            result.append(entry)

    return result


def osv_from_cve(
    record: dict[str, Any],
    ecosystem: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """An OSV draft from a CVE/GCVE record.

    The OSV ``id`` is left empty: OSV IDs carry the publishing database's
    prefix, and Vulniverse's record IDs are unique across formats, so the
    source record's ID can't be reused. The GCVE and CVE IDs go into
    ``aliases``; x_gcve goes into ``database_specific``, which the OSV
    profile validates like GCVE.
    """
    modified = (
        (now or datetime.now(UTC))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    cna = cna_of(record)
    cve_id, gcve_ids = vulnerability_ids(record)

    osv: dict[str, Any] = {
        "schema_version": OSV_SCHEMA_VERSION,
        "id": "",
        "modified": modified,
    }

    if text(cna.get("datePublic")):
        osv["published"] = cna["datePublic"]

    aliases = [*gcve_ids, *([cve_id] if cve_id else [])]
    if aliases:
        osv["aliases"] = aliases

    if text(cna.get("title")):
        osv["summary"] = cna["title"]
    if description := english(cna.get("descriptions")):
        osv["details"] = description

    severity: list[dict[str, str]] = []
    for metric in dicts(cna.get("metrics")):
        for cve_key, osv_type in SEVERITY_TYPES:
            vector = text(obj(metric.get(cve_key)).get("vectorString"))
            entry = {"type": osv_type, "score": vector}
            if vector and entry not in severity:
                severity.append(entry)
    if severity:
        osv["severity"] = severity

    if affected := _affected(cna, ecosystem):
        osv["affected"] = affected

    references = []
    for reference in dicts(cna.get("references")):
        url = text(reference.get("url"))
        if not url:
            continue
        tags = [tag for tag in reference.get("tags") or [] if isinstance(tag, str)]
        reference_type = next(
            (kind for tag, kind in REFERENCE_TYPES if tag in tags), "WEB"
        )
        references.append({"type": reference_type, "url": url})
    if references:
        osv["references"] = references

    credits = [
        {
            "name": text(credit.get("value")),
            **(
                {"type": CREDIT_TYPES[text(credit.get("type")).lower()]}
                if text(credit.get("type")).lower() in CREDIT_TYPES
                else {}
            ),
        }
        for credit in dicts(cna.get("credits"))
        if text(credit.get("value"))
    ]
    if credits:
        osv["credits"] = credits

    database_specific: dict[str, Any] = {}
    cwe_ids = list(
        dict.fromkeys(
            text(entry.get("cweId"))
            for problem in dicts(cna.get("problemTypes"))
            for entry in dicts(problem.get("descriptions"))
            if text(entry.get("cweId"))
        )
    )
    if cwe_ids:
        database_specific["cwe_ids"] = cwe_ids
    if dicts(cna.get("x_gcve")):
        database_specific["x_gcve"] = cna["x_gcve"]
    if database_specific:
        osv["database_specific"] = database_specific

    return osv
