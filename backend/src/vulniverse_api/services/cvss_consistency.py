"""Warnings for CVSS objects in CVE-shaped records whose stored values
disagree with their own vector string: a base score or severity typed by
hand, or a per-metric field (``attackVector`` …) left behind after the
vector changed. The vector is taken as the truth; the JSON Schema already
checks its shape, so a vector the library can't parse is left to it."""

from typing import Any

from cvss import CVSS2, CVSS3, CVSS4
from cvss.exceptions import CVSSError

# Base-metric fields per CVE metrics key and the vector metric each mirrors.
# Every enum value of these fields starts with its vector letter
# ("NETWORK" <-> "AV:N", "ADJACENT_NETWORK" <-> "AV:A").
_V2_FIELDS = {
    "accessVector": "AV",
    "accessComplexity": "AC",
    "authentication": "Au",
    "confidentialityImpact": "C",
    "integrityImpact": "I",
    "availabilityImpact": "A",
}

_V3_FIELDS = {
    "attackVector": "AV",
    "attackComplexity": "AC",
    "privilegesRequired": "PR",
    "userInteraction": "UI",
    "scope": "S",
    "confidentialityImpact": "C",
    "integrityImpact": "I",
    "availabilityImpact": "A",
}

_V4_FIELDS = {
    "attackVector": "AV",
    "attackComplexity": "AC",
    "attackRequirements": "AT",
    "privilegesRequired": "PR",
    "userInteraction": "UI",
    "vulnConfidentialityImpact": "VC",
    "vulnIntegrityImpact": "VI",
    "vulnAvailabilityImpact": "VA",
    "subConfidentialityImpact": "SC",
    "subIntegrityImpact": "SI",
    "subAvailabilityImpact": "SA",
}

_FORMATS = {
    "cvssV2_0": _V2_FIELDS,
    "cvssV3_0": _V3_FIELDS,
    "cvssV3_1": _V3_FIELDS,
    "cvssV4_0": _V4_FIELDS,
}

_FIX = "Open the CVSS calculator and apply it to update the stored values."


def _expected(key: str, vector: str) -> tuple[float, str | None, dict[str, str]]:
    """(base score, severity or None, vector metrics) of a vector."""
    if key == "cvssV2_0":
        parsed = CVSS2(vector)
        return float(parsed.scores()[0]), None, dict(parsed.metrics)

    if key == "cvssV4_0":
        parsed4 = CVSS4(vector)
        return (
            float(parsed4.base_score),
            parsed4.severity.upper(),
            dict(parsed4.metrics),
        )

    parsed3 = CVSS3(vector)
    return (
        float(parsed3.scores()[0]),
        parsed3.severities()[0].upper(),
        dict(parsed3.metrics),
    )


def _warning(path: list[Any], message: str) -> dict[str, Any]:
    return {
        "path": path,
        "schemaPath": [],
        "message": f"{message} {_FIX}",
        "validator": "cvss",
        "severity": "warning",
    }


def _check(score: dict[str, Any], key: str, path: list[Any]) -> list[dict[str, Any]]:
    vector = score.get("vectorString")

    if not isinstance(vector, str):
        return []

    try:
        base, severity, metrics = _expected(key, vector)
    except (CVSSError, KeyError, ValueError):
        return []

    warnings = []
    stored = score.get("baseScore")

    if isinstance(stored, (int, float)) and abs(stored - base) > 0.05:
        warnings.append(
            _warning(
                [*path, "baseScore"],
                f"Base score {stored} does not match the vector, which scores {base}.",
            )
        )

    stored_severity = score.get("baseSeverity")

    if severity and isinstance(stored_severity, str) and stored_severity != severity:
        warnings.append(
            _warning(
                [*path, "baseSeverity"],
                f"Base severity {stored_severity} does not match the vector, "
                f"which is {severity}.",
            )
        )

    for field, metric in _FORMATS[key].items():
        value = score.get(field)
        letter = metrics.get(metric)

        if isinstance(value, str) and letter and not value.startswith(letter):
            warnings.append(
                _warning(
                    [*path, field],
                    f"{field} is {value}, but the vector says {metric}:{letter}.",
                )
            )

    return warnings


def cvss_warnings(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Warnings for every CVSS object in the CNA and ADP containers."""
    containers = record.get("containers")

    if not isinstance(containers, dict):
        return []

    sources: list[tuple[list[Any], Any]] = [
        (["containers", "cna"], containers.get("cna"))
    ]
    adps = containers.get("adp")

    if isinstance(adps, list):
        sources += [
            (["containers", "adp", index], adp) for index, adp in enumerate(adps)
        ]

    warnings = []

    for path, container in sources:
        metrics = container.get("metrics") if isinstance(container, dict) else None

        if not isinstance(metrics, list):
            continue

        for index, entry in enumerate(metrics):
            if not isinstance(entry, dict):
                continue

            for key in _FORMATS:
                if isinstance(entry.get(key), dict):
                    warnings += _check(entry[key], key, [*path, "metrics", index, key])

    return warnings
