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
