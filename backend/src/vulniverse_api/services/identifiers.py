import re
from typing import Any, Callable

from .profiles import resolve_profile
from .record_validation import find_x_gcve_occurrences


def extract_cve_identifier(
    document: dict[str, Any],
) -> str | None:
    metadata = document.get("cveMetadata", {})
    if not isinstance(metadata, dict):
        return None

    value = metadata.get("cveId")
    return value if isinstance(value, str) and value else None


def extract_gcve_identifier(
    document: dict[str, Any],
) -> str | None:
    containers = document.get("containers")
    if not isinstance(containers, dict):
        return None

    cna = containers.get("cna")
    if not isinstance(cna, dict):
        return None

    extensions = cna.get("x_gcve")
    if not isinstance(extensions, list):
        return None

    for extension in extensions:
        if not isinstance(extension, dict):
            continue

        if extension.get("recordType") != "advisory":
            continue

        vuln_id = extension.get("vulnId")
        if isinstance(vuln_id, str) and vuln_id.strip():
            return vuln_id

    return None


def extract_osv_identifier(
    document: dict[str, Any],
) -> str | None:
    value = document.get("id")
    return value if isinstance(value, str) and value else None


IDENTIFIER_STRATEGIES: dict[
    str,
    Callable[[dict[str, Any]], str | None],
] = {
    "cve": extract_cve_identifier,
    "gcve": extract_gcve_identifier,
    "osv": extract_osv_identifier,
}


def extract_identifier(
    document: dict[str, Any],
    profile_id: str,
) -> str | None:
    profile = resolve_profile(profile_id)

    strategy = profile.get("identifier", {}).get("strategy")

    if strategy not in IDENTIFIER_STRATEGIES:
        raise ValueError(
            f"Unsupported identifier strategy: {strategy}"
        )

    return IDENTIFIER_STRATEGIES[strategy](document)


# A CVE/GCVE ID's only letters are its prefix, and that is case-insensitive
# (VL even hands out "gcve-…"); everything after it is kept as written.
ID_SHAPE = re.compile(r"^(?:cve|gcve-[0-9]+)-[0-9]{4}-", re.IGNORECASE)
ID_PREFIX = re.compile(r"^g?cve", re.IGNORECASE)


def canonical_id(value: Any) -> Any:
    """Uppercase the cve/gcve prefix of a CVE/GCVE-shaped ID; anything
    else (OSV IDs like GHSA-xxxx-xxxx-xxxx, non-strings) is unchanged."""
    if isinstance(value, str) and ID_SHAPE.match(value):
        return ID_PREFIX.sub(lambda match: match.group().upper(), value)

    return value


def normalize_id_case(document: dict[str, Any]) -> None:
    """Canonicalize the document's CVE/GCVE ID fields in place, so a typed
    "gcve-1-2026-0001" is stored as "GCVE-1-2026-0001"."""
    metadata = document.get("cveMetadata")

    if isinstance(metadata, dict):
        for key in ("cveId", "vulnId"):
            if key in metadata:
                metadata[key] = canonical_id(metadata[key])

    containers = document.get("containers")
    cna = containers.get("cna") if isinstance(containers, dict) else None
    entries = cna.get("x_gcve") if isinstance(cna, dict) else None

    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and "vulnId" in entry:
                entry["vulnId"] = canonical_id(entry["vulnId"])
