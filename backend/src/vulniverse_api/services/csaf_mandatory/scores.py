"""Mandatory tests: Metrics: CVSS, SSVC, EPSS, qualitative severity, and CWE."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from cvss import (
    CVSS2,
    CVSS3,
    CVSS4,
    CVSSError,
    constants2,
    constants3,
)
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for

from .core import Issue, get, mandatory, select, strings
from .metadata import language_problem

DATA = Path(__file__).with_name("data")

CVSS_KEYS = ("cvss_v2", "cvss_v3", "cvss_v4")


def _contents(document: Any, key: str) -> list[tuple[tuple[str | int, ...], Any]]:
    """Every ``content.<key>`` object of the vulnerabilities' metrics."""
    return [
        (path, value)
        for path, value in select(
            document, f"$.vulnerabilities[*].metrics[*].content.{key}"
        )
        if isinstance(value, dict)
    ]


def _cvss_objects(document: Any) -> Iterator[tuple[tuple[str | int, ...], str, dict]]:
    for key in CVSS_KEYS:
        for path, value in _contents(document, key):
            yield path, key, value


# --- Referenced schemas (6.1.8, 6.1.46) --------------------------------------


@cache
def _validator(url: str) -> Validator:
    """A validator for one referenced schema, from the profile's vendored files."""
    # Imported here: record_validation imports this package.
    from ..profiles import resolve_profile
    from ..record_validation import schema_resources

    registry = schema_resources(resolve_profile("csaf-2.1"))
    schema = registry.contents(url)
    validator_class = validator_for(schema, default=Draft202012Validator)
    return validator_class(schema, registry=registry, format_checker=FormatChecker())


def _schema_issues(
    path: tuple[str | int, ...], value: dict, url: str
) -> Iterator[Issue]:
    validator = _validator(url)

    for error in validator.iter_errors(value):
        message = error.message
        if error.validator == "pattern":  # the pattern itself can be huge
            message = f"{error.instance!r} doesn't match the schema's pattern"
        yield Issue((*path, *error.absolute_path), message)

    # The CVSS v2/v3 schemas don't forbid other properties themselves, the
    # spec does.
    schema = validator.schema
    if isinstance(schema, dict) and not (
        {"additionalProperties", "unevaluatedProperties"} & schema.keys()
    ):
        for name in value.keys() - schema.get("properties", {}).keys():
            yield Issue((*path, name), f"additional property `{name}` is not allowed")


def _cvss_schema_url(key: str, value: dict) -> str:
    if key == "cvss_v3":
        return (
            "https://www.first.org/cvss/cvss-v3.0.json"
            if value.get("version") == "3.0"
            else "https://www.first.org/cvss/cvss-v3.1.json"
        )
    return f"https://www.first.org/cvss/cvss-v{key[-1]}.0.json"


@mandatory("6.1.8", "Invalid CVSS")
def invalid_cvss(document: dict[str, Any]) -> Iterator[Issue]:
    for path, key, value in _cvss_objects(document):
        yield from _schema_issues(path, value, _cvss_schema_url(key, value))


# --- CVSS computation (6.1.9) ------------------------------------------------


def _computed(key: str, vector: str) -> dict[str, float | str]:
    """The scores and severities ``vector`` gives, by property name."""
    if key == "cvss_v2":
        base, temporal, environmental = CVSS2(vector).scores()
        # The library leaves out groups the vector doesn't set; with all of
        # their metrics NOT_DEFINED they equal the previous score.
        temporal = base if temporal is None else temporal
        environmental = temporal if environmental is None else environmental
        return {
            "baseScore": base,
            "temporalScore": temporal,
            "environmentalScore": environmental,
        }

    if key == "cvss_v3":
        cvss3 = CVSS3(vector)
        scores = cvss3.scores()
        severities = [severity.upper() for severity in cvss3.severities()]
        return {
            "baseScore": scores[0],
            "baseSeverity": severities[0],
            "temporalScore": scores[1],
            "temporalSeverity": severities[1],
            "environmentalScore": scores[2],
            "environmentalSeverity": severities[2],
        }

    cvss4 = CVSS4(vector)
    return {"baseScore": cvss4.base_score, "baseSeverity": cvss4.severity.upper()}


@mandatory("6.1.9", "Invalid CVSS Computation")
def invalid_cvss_computation(document: dict[str, Any]) -> Iterator[Issue]:
    for path, key, value in _cvss_objects(document):
        vector = value.get("vectorString")
        if not isinstance(vector, str):
            continue
        try:
            computed = _computed(key, vector)
        except CVSSError:
            continue  # An invalid vector is 6.1.8's finding.

        for name, expected in computed.items():
            given = value.get(name)
            is_number = isinstance(given, int | float) and not isinstance(given, bool)
            if (is_number or isinstance(given, str)) and given != expected:
                yield Issue(
                    (*path, name),
                    f"`{name}` is `{given}`, but the vector gives `{expected}`",
                )


# --- CVSS properties and vector (6.1.10) -------------------------------------

CVSS4_PROPERTIES = {
    "AV": "attackVector",
    "AC": "attackComplexity",
    "AT": "attackRequirements",
    "PR": "privilegesRequired",
    "UI": "userInteraction",
    "VC": "vulnConfidentialityImpact",
    "VI": "vulnIntegrityImpact",
    "VA": "vulnAvailabilityImpact",
    "SC": "subConfidentialityImpact",
    "SI": "subIntegrityImpact",
    "SA": "subAvailabilityImpact",
    "E": "exploitMaturity",
    "CR": "confidentialityRequirement",
    "IR": "integrityRequirement",
    "AR": "availabilityRequirement",
    "MAV": "modifiedAttackVector",
    "MAC": "modifiedAttackComplexity",
    "MAT": "modifiedAttackRequirements",
    "MPR": "modifiedPrivilegesRequired",
    "MUI": "modifiedUserInteraction",
    "MVC": "modifiedVulnConfidentialityImpact",
    "MVI": "modifiedVulnIntegrityImpact",
    "MVA": "modifiedVulnAvailabilityImpact",
    "MSC": "modifiedSubConfidentialityImpact",
    "MSI": "modifiedSubIntegrityImpact",
    "MSA": "modifiedSubAvailabilityImpact",
    "S": "Safety",
    "AU": "Automatable",
    "R": "Recovery",
    "V": "valueDensity",
    "RE": "vulnerabilityResponseEffort",
    "U": "providerUrgency",
}

CVSS_PROPERTIES = {
    "cvss_v2": constants2.METRICS_ABBREVIATIONS_JSON,
    "cvss_v3": constants3.METRICS_ABBREVIATIONS_JSON,
    "cvss_v4": CVSS4_PROPERTIES,
}

# CVSS v2 values whose vector abbreviation isn't their first letter.
CVSS2_ABBREVIATIONS = {
    "ADJACENT_NETWORK": "A",
    "PROOF_OF_CONCEPT": "POC",
    "OFFICIAL_FIX": "OF",
    "TEMPORARY_FIX": "TF",
    "UNCONFIRMED": "UC",
    "UNCORROBORATED": "UR",
    "LOW_MEDIUM": "LM",
    "MEDIUM_HIGH": "MH",
    "NOT_DEFINED": "ND",
}


def _abbreviation(key: str, metric: str, value: str) -> str:
    """The vector value for a property value, e.g. ``NETWORK`` -> ``N``."""
    if key == "cvss_v2":
        return CVSS2_ABBREVIATIONS.get(value, value[:1])
    if value == "NOT_DEFINED":
        return "X"
    return value.title() if metric == "U" else value[:1]


def _vector_metrics(vector: str) -> dict[str, str]:
    parts = vector.split("/")
    if parts[0].startswith("CVSS:"):
        parts = parts[1:]
    return dict(part.split(":", 1) for part in parts if ":" in part)


@mandatory("6.1.10", "Inconsistent CVSS")
def inconsistent_cvss(document: dict[str, Any]) -> Iterator[Issue]:
    for path, key, value in _cvss_objects(document):
        vector = value.get("vectorString")
        if not isinstance(vector, str):
            continue
        metrics = _vector_metrics(vector)
        not_defined = "ND" if key == "cvss_v2" else "X"

        for metric, name in CVSS_PROPERTIES[key].items():
            given = value.get(name)
            if not isinstance(given, str) or not given:
                continue
            in_vector = metrics.get(metric, not_defined)
            allowed = {in_vector}
            if metric not in metrics and metric.startswith("M"):
                # An unset modified metric takes the base metric's value.
                allowed.add(metrics.get(metric[1:], not_defined))
            if _abbreviation(key, metric, given) not in allowed:
                yield Issue(
                    (*path, name),
                    f"`{name}` is `{given}`, but the vector has `{metric}:{in_vector}`",
                )


# --- CWE (6.1.11) -------------------------------------------------------------


@cache
def _cwe_data() -> dict[str, Any]:
    with (DATA / "cwe.json").open(encoding="utf-8") as data_file:
        data: dict[str, Any] = json.load(data_file)
    return data


def _cwe_entry(cwe_number: str, version: str) -> str | int | None:
    """The weakness name of a CWE in a release, 0/1 for a category/view,
    None if the release doesn't define it."""
    data = _cwe_data()
    index = data["versions"].index(version)
    entry = None
    for since, value in data["cwes"].get(cwe_number, []):
        if since > index:
            break
        entry = value
    return entry


@mandatory("6.1.11", "CWE")
def cwe(document: dict[str, Any]) -> Iterator[Issue]:
    for path, item in select(document, "$.vulnerabilities[*].cwes[*]"):
        cwe_id, name, version = (get(item, key) for key in ("id", "name", "version"))
        if not (
            isinstance(cwe_id, str)
            and cwe_id.startswith("CWE-")
            and isinstance(version, str)
        ):
            continue

        if version not in _cwe_data()["versions"]:
            # shortcut: releases newer than data/cwe.json fail too, refresh it
            # when MITRE publishes one.
            yield Issue((*path, "version"), f"cwe version `{version}` is unknown")
            continue

        entry = _cwe_entry(cwe_id.removeprefix("CWE-"), version)
        if entry is None:
            yield Issue((*path, "id"), f"`{cwe_id}` doesn't exist in version {version}")
        elif isinstance(entry, int):
            kind = "view" if entry else "category"
            yield Issue((*path, "id"), f"`{cwe_id}` is a {kind}, not a weakness")
        elif isinstance(name, str) and name != entry:
            yield Issue(
                (*path, "name"),
                f"the name of `{cwe_id}` in version {version} is `{entry}`",
            )


# --- SSVC (6.1.46, 6.1.47, 6.1.48) -------------------------------------------

SSVC_SCHEMA = (
    "https://certcc.github.io/SSVC/data/schema/v2/SelectionList_2_0_0.schema.json"
)


def _namespace_languages(namespace: str) -> list[str]:
    """The language tags in an SSVC namespace's extensions."""
    _base, *extensions = namespace.split("/")
    tags = [extensions[0]] if extensions and extensions[0] else []
    for segment in extensions[1:]:
        if segment.startswith("."):
            if "$" in segment:
                tags.append(segment.split("$", 1)[1])
        elif segment:
            tags.append(segment)
    return tags


@mandatory("6.1.46", "Invalid SSVC")
def invalid_ssvc(document: dict[str, Any]) -> Iterator[Issue]:
    for path, value in _contents(document, "ssvc_v2"):
        yield from _schema_issues(path, value, SSVC_SCHEMA)

        for namespace_path, namespace in strings(
            select(value, "$.selections[*].namespace")
        ):
            for tag in _namespace_languages(namespace):
                if problem := language_problem(tag):
                    yield Issue((*path, *namespace_path), problem)


@mandatory("6.1.47", "Inconsistent SSVC Target IDs")
def inconsistent_ssvc_target_ids(document: dict[str, Any]) -> Iterator[Issue]:
    tracking_id = get(document, "document", "tracking", "id")
    vulnerabilities = select(document, "$.vulnerabilities[*]")

    for path, vulnerability in vulnerabilities:
        known = {
            value
            for _, value in strings(
                [
                    *select(vulnerability, "$.cve"),
                    *select(vulnerability, "$.ids[*].text"),
                ]
            )
        }
        for target_path, target in strings(
            select(vulnerability, "$.metrics[*].content.ssvc_v2.target_ids[*]")
        ):
            if target not in known:
                yield Issue(
                    (*path, *target_path),
                    f"ssvc target id `{target}` is neither the cve nor an id "
                    "of the vulnerability",
                )
            elif target == tracking_id and len(vulnerabilities) > 1:
                yield Issue(
                    (*path, *target_path),
                    f"ssvc target id `{target}` is the document's tracking id, "
                    "but the document has more than one vulnerability",
                )


@cache
def _decision_points() -> dict[str, Any]:
    with (DATA / "ssvc-decision-points.json").open(encoding="utf-8") as data_file:
        data: dict[str, Any] = json.load(data_file)["decision_points"]
    return data


# https://certcc.github.io/SSVC/reference/code/namespaces/#registered-namespace
REGISTERED_NAMESPACES = {"ssvc", "cvss", "cisa", "basic", "example", "test", "nist"}
# Reserved for documentation and tests: nothing to check.
FREE_NAMESPACES = {"example", "test"}
# Reserved and never to be used.
INVALID_NAMESPACES = {"invalid", "x_invalid"}


@mandatory("6.1.48", "SSVC Decision Points")
def ssvc_decision_points(document: dict[str, Any]) -> Iterator[Issue]:
    for path, selection in select(
        document, "$.vulnerabilities[*].metrics[*].content.ssvc_v2.selections[*]"
    ):
        namespace, key, version = (
            get(selection, name) for name in ("namespace", "key", "version")
        )
        if not all(isinstance(item, str) for item in (namespace, key, version)):
            continue
        assert isinstance(namespace, str)  # for mypy

        # Extensions (after "/") can't change keys, versions or value order.
        base = namespace.split("/", 1)[0]
        base_name = base.split("#", 1)[0]
        if base_name in INVALID_NAMESPACES:
            yield Issue(
                (*path, "namespace"), f"ssvc namespace `{base_name}` is reserved"
            )
            continue
        if base_name not in REGISTERED_NAMESPACES or base_name in FREE_NAMESPACES:
            continue

        versions = _decision_points().get(base, {}).get(key, {})
        if version not in versions:
            yield Issue(
                path,
                f"ssvc decision point `{key}` version {version} doesn't exist "
                f"in namespace `{base}`",
            )
            continue

        definition = versions[version]
        defined = definition["values"]
        given = strings(select(selection, "$.values[*].key"))
        for value_path, value_key in given:
            if value_key not in defined:
                yield Issue(
                    (*path, *value_path),
                    f"ssvc decision point `{definition['name']}` doesn't have the "
                    f"value `{value_key}` in version {version}",
                )
        order = [defined.index(k) for _, k in given if k in defined]
        if order != sorted(order):
            yield Issue(
                (*path, "values"),
                f"the values of ssvc decision point `{definition['name']}` aren't "
                "in the order of their definition",
            )


# --- Timestamps (6.1.49, 6.1.51) ---------------------------------------------


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _too_new(document: dict[str, Any], key: str, label: str) -> Iterator[Issue]:
    """``content.<key>.timestamp`` after the newest revision of a final or
    interim document."""
    status = get(document, "document", "tracking", "status")
    if status not in ("final", "interim"):
        return

    dates = [
        parsed
        for _, value in select(document, "$.document.tracking.revision_history[*].date")
        if (parsed := _timestamp(value)) is not None
    ]
    if not dates:
        return
    newest = max(dates)

    for path, value in select(
        document, f"$.vulnerabilities[*].metrics[*].content.{key}.timestamp"
    ):
        parsed = _timestamp(value)
        if parsed is not None and parsed > newest:
            yield Issue(
                path,
                f"the document is {status}, but the {label} timestamp is newer "
                "than the newest revision",
            )


@mandatory("6.1.49", "Inconsistent SSVC Timestamp")
def inconsistent_ssvc_timestamp(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _too_new(document, "ssvc_v2", "ssvc")


@mandatory("6.1.51", "Inconsistent EPSS Timestamp")
def inconsistent_epss_timestamp(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _too_new(document, "epss", "epss")


# --- CVSS and qualitative severity (6.1.56) ----------------------------------


@mandatory("6.1.56", "Use of CVSS and Qualitative Severity Rating")
def cvss_and_qualitative_severity(document: dict[str, Any]) -> Iterator[Issue]:
    for vulnerability_path, vulnerability in select(document, "$.vulnerabilities[*]"):
        scored: set[tuple[str, Any]] = set()
        rated: list[tuple[tuple[str | int, ...], tuple[str, Any]]] = []

        for path, metric in select(vulnerability, "$.metrics[*]"):
            content = get(metric, "content")
            if not isinstance(content, dict):
                continue
            source = get(metric, "source")
            products = strings(select(metric, "$.products[*]"))
            if any(key in content for key in CVSS_KEYS):
                scored.update((product, source) for _, product in products)
            if "qualitative_severity_rating" in content:
                rated.extend(
                    ((*vulnerability_path, *path, *product_path), (product, source))
                    for product_path, product in products
                )

        for product_path, pair in rated:
            if pair in scored:
                yield Issue(
                    product_path,
                    f"a cvss score and a qualitative severity rating are given "
                    f"for `{pair[0]}` by the same source",
                )
