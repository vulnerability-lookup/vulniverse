from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any, NamedTuple

METHODOLOGY_VERSION = 1
METHODOLOGY_SINCE = "2026-09-29"


class Check(NamedTuple):
    name: str
    pillar: str
    weight: int
    rule: str


PILLARS: tuple[tuple[str, str], ...] = (
    (
        "describe",
        "Describe: can a reader tell what the vulnerability is?",
    ),
    (
        "scope",
        "Scope: can a reader tell whether they are affected?",
    ),
    (
        "assess",
        "Assess: can a reader tell how bad it is?",
    ),
    (
        "act",
        "Act: can a reader tell what to do about it?",
    ),
)


CHECKS: tuple[Check, ...] = (
    Check(
        "description",
        "describe",
        10,
        (
            "English description quality: full credit from 200 characters, "
            "0.7 from 80, 0.4 from 40."
        ),
    ),
    Check(
        "title",
        "describe",
        5,
        "A non-placeholder title is present.",
    ),
    Check(
        "cwe",
        "describe",
        10,
        (
            "A CWE identifier is present in problemTypes; a meaningful "
            "free-text problem type receives partial credit."
        ),
    ),
    Check(
        "affected",
        "scope",
        10,
        (
            "An affected entry identifies vendor and product; identifying "
            "only one receives partial credit."
        ),
    ),
    Check(
        "versions",
        "scope",
        8,
        (
            "Affected versions or version bounds are stated; defaultStatus "
            "alone receives partial credit."
        ),
    ),
    Check(
        "cpe",
        "scope",
        7,
        "A CPE is stated in affected data or cpeApplicability.",
    ),
    Check(
        "severity",
        "assess",
        15,
        (
            "A CVSS v3/v4 vector, SSVC decision, or other vendor severity "
            "statement is present; CVSS v2 alone receives partial credit."
        ),
    ),
    Check(
        "modern_severity",
        "assess",
        5,
        "A CVSS v4 vector or SSVC decision is present.",
    ),
    Check(
        "impacts",
        "assess",
        5,
        "An impact description or CAPEC identifier is present.",
    ),
    Check(
        "references",
        "act",
        7,
        "At least one reference URL is present.",
    ),
    Check(
        "reference_tags",
        "act",
        5,
        "At least one reference carries tags.",
    ),
    Check(
        "remediation",
        "act",
        8,
        (
            "A patch reference receives full credit; vendor-advisory, "
            "mitigation, or release-notes receives partial credit."
        ),
    ),
    Check(
        "solutions",
        "act",
        5,
        "At least one solution or workaround is present.",
    ),
)


CHECK_WEIGHTS: dict[str, int] = {check.name: check.weight for check in CHECKS}


PILLAR_WEIGHTS: dict[str, int] = {
    pillar: sum(check.weight for check in CHECKS if check.pillar == pillar)
    for pillar, _label in PILLARS
}


GRADES: tuple[tuple[str, float], ...] = (
    ("A", 90.0),
    ("B", 75.0),
    ("C", 60.0),
    ("D", 45.0),
    ("E", 0.0),
)


_CWE_ID = re.compile(
    r"\ACWE-\d+\Z",
    re.IGNORECASE,
)

_PLACEHOLDER = re.compile(
    (
        r"\A\W*"
        r"(reserved|rejected|n/?a|none|tbd|todo|placeholder|unknown)"
        r"\b"
    ),
    re.IGNORECASE,
)

_NOT_A_VALUE = frozenset(
    {
        "",
        "n/a",
        "na",
        "none",
        "unknown",
        "unspecified",
        "-",
    }
)

_CVSS_KEYS: tuple[str, ...] = (
    "cvssV4_0",
    "cvssV3_1",
    "cvssV3_0",
)


assert (
    sum(
        CHECK_WEIGHTS.values(),
    )
    == 100
)

assert all(weight == 25 for weight in PILLAR_WEIGHTS.values())


def _is_real_value(
    value: Any,
) -> bool:
    if not isinstance(
        value,
        str,
    ):
        return False

    return value.strip().lower() not in _NOT_A_VALUE


def _dict_items(
    value: Any,
) -> list[dict[str, Any]]:
    """
    Accept both the normal array form and a single object.

    Vulnerability-Lookup deliberately tolerates malformed/single-object
    shapes here rather than failing the entire score calculation.
    """

    if isinstance(
        value,
        dict,
    ):
        value = [value]

    if not isinstance(
        value,
        list,
    ):
        return []

    return [
        item
        for item in value
        if isinstance(
            item,
            dict,
        )
    ]


def _cna_container(
    record: dict[str, Any],
) -> dict[str, Any]:
    containers = record.get("containers")

    if not isinstance(
        containers,
        dict,
    ):
        return {}

    cna = containers.get("cna")

    return (
        cna
        if isinstance(
            cna,
            dict,
        )
        else {}
    )


def _english_description(
    descriptions: Any,
) -> str | None:
    """
    Match Vulnerability-Lookup's English-description selection:
    use the first non-empty description whose language starts with "en".
    """

    if not isinstance(
        descriptions,
        (list, tuple),
    ):
        return None

    for description in descriptions:
        if not isinstance(
            description,
            dict,
        ):
            continue

        value = description.get("value")

        language = str(
            description.get(
                "lang",
                "",
            )
        ).lower()

        if value and language.startswith("en"):
            return str(value)

    return None


def _description_credit(
    length: int,
) -> float:
    if length >= 200:
        return 1.0

    if length >= 80:
        return 0.7

    if length >= 40:
        return 0.4

    return 0.0


def _cvss_vectors(
    container: dict[str, Any],
    keys: Sequence[str] = _CVSS_KEYS,
) -> bool:
    for metric in _dict_items(container.get("metrics")):
        for key in keys:
            value = metric.get(key)

            if isinstance(
                value,
                dict,
            ) and _is_real_value(value.get("vectorString")):
                return True

    return False


def _has_ssvc(
    container: dict[str, Any],
) -> bool:
    for metric in _dict_items(container.get("metrics")):
        other = metric.get("other")

        if not isinstance(
            other,
            dict,
        ):
            continue

        other_type = str(other.get("type") or "").strip().lower()

        if other_type == "ssvc":
            return True

    return False


def _has_other_rating(
    container: dict[str, Any],
) -> bool:
    for metric in _dict_items(container.get("metrics")):
        other = metric.get("other")

        if not isinstance(
            other,
            dict,
        ):
            continue

        if other.get("content") or _is_real_value(other.get("type")):
            return True

    return False


def _cwe_ids(
    container: dict[str, Any],
) -> list[str]:
    result: list[str] = []

    for problem in _dict_items(container.get("problemTypes")):
        for description in _dict_items(problem.get("descriptions")):
            cwe_id = description.get("cweId")

            if isinstance(
                cwe_id,
                str,
            ) and _CWE_ID.match(cwe_id.strip()):
                result.append(cwe_id)

    return result


def _has_problem_text(
    container: dict[str, Any],
) -> bool:
    return any(
        _is_real_value(description.get("description"))
        for problem in _dict_items(container.get("problemTypes"))
        for description in _dict_items(problem.get("descriptions"))
    )


def _reference_tags(
    container: dict[str, Any],
) -> list[str]:
    result: list[str] = []

    for reference in _dict_items(container.get("references")):
        tags = reference.get("tags")

        if not isinstance(
            tags,
            list,
        ):
            continue

        result.extend(
            tag.strip().lower()
            for tag in tags
            if isinstance(
                tag,
                str,
            )
        )

    return result


def _grade(
    score: float,
) -> str:
    for letter, minimum in GRADES:
        if score >= minimum:
            return letter

    return "E"


def _calculate_credits(
    record: dict[str, Any],
) -> dict[str, float]:
    cna = _cna_container(record)

    credits: dict[str, float] = {check.name: 0.0 for check in CHECKS}

    # ------------------------------------------------------------------
    # Describe
    # ------------------------------------------------------------------

    description = (_english_description(cna.get("descriptions")) or "").strip()

    description_length = 0 if _PLACEHOLDER.match(
        description) else len(description)

    credits["description"] = _description_credit(description_length)

    credits["title"] = 1.0 if _is_real_value(cna.get("title")) else 0.0

    cwe_ids = _cwe_ids(cna)

    if cwe_ids:
        credits["cwe"] = 1.0

    elif _has_problem_text(cna):
        credits["cwe"] = 0.25

    # ------------------------------------------------------------------
    # Scope
    # ------------------------------------------------------------------

    affected = _dict_items(cna.get("affected"))

    has_vendor_and_product = any(
        _is_real_value(entry.get("vendor")) and _is_real_value(
            entry.get("product"))
        for entry in affected
    )

    has_vendor_or_product = any(
        _is_real_value(entry.get("vendor")) or _is_real_value(
            entry.get("product"))
        for entry in affected
    )

    if has_vendor_and_product:
        credits["affected"] = 1.0

    elif has_vendor_or_product:
        credits["affected"] = 0.5

    has_version = any(
        (
            _is_real_value(version.get("version"))
            or _is_real_value(version.get("lessThan"))
            or _is_real_value(version.get("lessThanOrEqual"))
        )
        for entry in affected
        for version in _dict_items(entry.get("versions"))
    )

    has_default_status = any(
        _is_real_value(entry.get("defaultStatus")) for entry in affected
    )

    if has_version:
        credits["versions"] = 1.0

    elif has_default_status:
        credits["versions"] = 0.5

    has_affected_cpe = any(
        isinstance(
            entry.get("cpes"),
            list,
        )
        and any(_is_real_value(cpe) for cpe in entry["cpes"])
        for entry in affected
    )

    has_cpe_applicability = any(
        _is_real_value(match.get("criteria"))
        for block in _dict_items(cna.get("cpeApplicability"))
        for node in _dict_items(block.get("nodes"))
        for match in _dict_items(node.get("cpeMatch"))
    )

    credits["cpe"] = 1.0 if (
        has_affected_cpe or has_cpe_applicability) else 0.0

    # ------------------------------------------------------------------
    # Assess
    # ------------------------------------------------------------------

    has_cvss_3_or_4 = _cvss_vectors(cna)

    has_ssvc = _has_ssvc(cna)

    if has_cvss_3_or_4 or has_ssvc or _has_other_rating(cna):
        credits["severity"] = 1.0

    elif _cvss_vectors(
        cna,
        ("cvssV2_0",),
    ):
        credits["severity"] = 0.5

    credits["modern_severity"] = (
        1.0
        if (
            has_ssvc
            or _cvss_vectors(
                cna,
                ("cvssV4_0",),
            )
        )
        else 0.0
    )

    credits["impacts"] = (
        1.0
        if any(
            (
                _is_real_value(impact.get("capecId"))
                or bool(_dict_items(impact.get("descriptions")))
            )
            for impact in _dict_items(cna.get("impacts"))
        )
        else 0.0
    )

    # ------------------------------------------------------------------
    # Act
    # ------------------------------------------------------------------

    references = _dict_items(cna.get("references"))

    credits["references"] = (
        1.0
        if any(_is_real_value(reference.get("url")) for reference in references)
        else 0.0
    )

    tags = _reference_tags(cna)

    credits["reference_tags"] = 1.0 if tags else 0.0

    if any("patch" in tag for tag in tags):
        credits["remediation"] = 1.0

    elif any(
        tag
        in {
            "vendor-advisory",
            "mitigation",
            "release-notes",
        }
        for tag in tags
    ):
        credits["remediation"] = 0.6

    credits["solutions"] = (
        1.0
        if (_dict_items(cna.get("solutions")) or _dict_items(cna.get("workarounds")))
        else 0.0
    )

    return credits


def score_record_quality(
    record: dict[str, Any],
) -> dict[str, Any]:
    """
    Score one CVE JSON 5 / GCVE record using Vulnerability-Lookup's
    assigner-scorecard methodology v1.

    This function evaluates the current document regardless of publication
    state. The official Vulnerability-Lookup aggregate scorecard separately
    excludes rejected/unpublished records before invoking its per-record
    scorer.
    """

    credits = _calculate_credits(record)

    score = round(
        sum(credits[check.name] * check.weight for check in CHECKS),
        2,
    )

    checks = [
        {
            "name": check.name,
            "pillar": check.pillar,
            "weight": check.weight,
            "rule": check.rule,
            "credit": credits[check.name],
            "points": round(
                credits[check.name] * check.weight,
                2,
            ),
        }
        for check in CHECKS
    ]

    pillars = [
        {
            "name": pillar,
            "label": label,
            "score": round(
                sum(
                    credits[check.name] * check.weight
                    for check in CHECKS
                    if check.pillar == pillar
                ),
                2,
            ),
            "maximum": PILLAR_WEIGHTS[pillar],
        }
        for pillar, label in PILLARS
    ]

    return {
        "score": score,
        "grade": _grade(score),
        "methodologyVersion": METHODOLOGY_VERSION,
        "methodologySince": METHODOLOGY_SINCE,
        "pillars": pillars,
        "checks": checks,
    }
