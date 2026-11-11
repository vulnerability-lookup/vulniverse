"""Shared machinery for the CSAF 2.1 mandatory tests (spec section 6.1).

A test is a function ``(document) -> Iterable[Issue]`` registered with
:func:`mandatory`. Tests read the document with :func:`select`, a JSONPath
subset matching the paths the spec lists for each test. Documents reach
these tests whether or not they are schema-valid (drafts are validated
too), so a test must skip values of the wrong type instead of failing.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import Any, Literal

Path = tuple[str | int, ...]


@dataclass(frozen=True)
class Issue:
    """One failure: where (a path into the document) and why."""

    path: Path
    message: str
    # The spec asks for warnings where an implementation lacks support
    # (e.g. an unknown hash algorithm); they don't fail the test.
    severity: Literal["error", "warning"] = "error"


TestFunction = Callable[[dict[str, Any]], Iterable[Issue]]


@dataclass(frozen=True)
class MandatoryTest:
    id: str
    title: str
    run: TestFunction


# In registration order; see __init__.py for the modules that fill it.
REGISTRY: dict[str, MandatoryTest] = {}


def mandatory(test_id: str, title: str) -> Callable[[TestFunction], TestFunction]:
    """Register a mandatory test under its spec number, e.g. ``"6.1.1"``."""

    def register(function: TestFunction) -> TestFunction:
        if test_id in REGISTRY:
            raise ValueError(f"Mandatory test {test_id} is registered twice.")
        REGISTRY[test_id] = MandatoryTest(test_id, title, function)
        return function

    return register


# --- JSONPath subset ----------------------------------------------------------

_TOKEN = re.compile(
    r"\.\.(?P<descend>[A-Za-z_$][\w$]*)|\.(?P<key>[A-Za-z_$][\w$]*)"
    r"|\['(?P<quoted>[^']*)'\]|\[(?P<wild>\*)\]|\[(?P<index>\d+)\]"
)


def _steps(expression: str) -> list[tuple[str, str]]:
    if not expression.startswith("$"):
        raise ValueError(f"JSONPath must start with $: {expression}")

    steps: list[tuple[str, str]] = []
    position = 1

    while position < len(expression):
        match = _TOKEN.match(expression, position)
        if match is None:
            raise ValueError(f"Unsupported JSONPath at {position}: {expression}")
        kind = match.lastgroup
        assert kind is not None
        steps.append((kind, match.group(kind)))
        position = match.end()

    return steps


def _descendants(path: Path, value: Any) -> Iterator[tuple[Path, Any]]:
    """``value`` and everything below it, depth first, in document order."""
    yield path, value

    if isinstance(value, dict):
        for key, child in value.items():
            yield from _descendants((*path, key), child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _descendants((*path, index), child)


def select(document: Any, expression: str) -> list[tuple[Path, Any]]:
    """Every ``(path, value)`` matching ``expression``.

    Supports ``$``, ``.key``, ``['key']``, ``[*]``, ``[0]`` and recursive
    descent ``..key``. A step that doesn't fit the value (a key on a list,
    a missing key) simply matches nothing.
    """
    current: list[tuple[Path, Any]] = [((), document)]

    for kind, name in _steps(expression):
        found: list[tuple[Path, Any]] = []

        for path, value in current:
            if kind in ("key", "quoted"):
                if isinstance(value, dict) and name in value:
                    found.append(((*path, name), value[name]))
            elif kind == "wild":
                if isinstance(value, list):
                    found.extend(
                        ((*path, index), item) for index, item in enumerate(value)
                    )
                elif isinstance(value, dict):
                    found.extend(((*path, key), item) for key, item in value.items())
            elif kind == "index":
                if isinstance(value, list) and int(name) < len(value):
                    found.append(((*path, int(name)), value[int(name)]))
            else:  # descend
                for inner_path, inner in _descendants(path, value):
                    if isinstance(inner, dict) and name in inner:
                        found.append(((*inner_path, name), inner[name]))

        current = found

    return current


def select_all(document: Any, expressions: Iterable[str]) -> list[tuple[Path, Any]]:
    return [
        match for expression in expressions for match in select(document, expression)
    ]


def strings(matches: Iterable[tuple[Path, Any]]) -> list[tuple[Path, str]]:
    """Only the matches whose value is a string."""
    return [(path, value) for path, value in matches if isinstance(value, str)]


def pointer(path: Path) -> str:
    """A JSON pointer (``/vulnerabilities/0/cve``), as the spec's results use."""
    return "".join(
        "/" + str(part).replace("~", "~0").replace("/", "~1") for part in path
    )


def get(value: Any, *keys: str | int) -> Any:
    """``value[k1][k2]…``, or None as soon as a step doesn't exist."""
    for key in keys:
        if isinstance(key, int):
            value = (
                value[key]
                if isinstance(value, list) and -len(value) <= key < len(value)
                else None
            )
        else:
            value = value.get(key) if isinstance(value, dict) else None
        if value is None:
            return None
    return value


# --- Product IDs (used by many tests) ----------------------------------------

# Where a Full Product Name (full_product_name_t) defines a product ID.
PRODUCT_DEFINITION_PATHS = (
    "$.product_tree..branches[*].product.product_id",
    "$.product_tree.full_product_names[*].product_id",
    "$.product_tree.product_paths[*].full_product_name.product_id",
)

# Every reference to a product ID (spec 6.1.1).
PRODUCT_REFERENCE_PATHS = (
    "$.document.involvement.actions[*].product_ids[*]",
    "$.document.notes[*].product_ids[*]",
    "$.product_tree.product_groups[*].product_ids[*]",
    "$.product_tree.product_paths[*].beginning_product_reference",
    "$.product_tree.product_paths[*].subpaths[*].next_product_reference",
    "$.vulnerabilities[*].first_known_exploitation_dates[*].product_ids[*]",
    "$.vulnerabilities[*].flags[*].product_ids[*]",
    "$.vulnerabilities[*].ids[*].product_ids[*]",
    "$.vulnerabilities[*].metrics[*].products[*]",
    "$.vulnerabilities[*].notes[*].product_ids[*]",
    "$.vulnerabilities[*].product_status.first_affected[*]",
    "$.vulnerabilities[*].product_status.first_fixed[*]",
    "$.vulnerabilities[*].product_status.fixed[*]",
    "$.vulnerabilities[*].product_status.known_affected[*]",
    "$.vulnerabilities[*].product_status.known_not_affected[*]",
    "$.vulnerabilities[*].product_status.last_affected[*]",
    "$.vulnerabilities[*].product_status.recommended[*]",
    "$.vulnerabilities[*].product_status.under_investigation[*]",
    "$.vulnerabilities[*].product_status.unknown[*]",
    "$.vulnerabilities[*].remediations[*].product_ids[*]",
    "$.vulnerabilities[*].threats[*].product_ids[*]",
)

# Every reference to a product group ID (spec 6.1.4).
GROUP_REFERENCE_PATHS = (
    "$.document.involvement.actions[*].group_ids[*]",
    "$.document.notes[*].group_ids[*]",
    "$.vulnerabilities[*].first_known_exploitation_dates[*].group_ids[*]",
    "$.vulnerabilities[*].flags[*].group_ids[*]",
    "$.vulnerabilities[*].ids[*].group_ids[*]",
    "$.vulnerabilities[*].notes[*].group_ids[*]",
    "$.vulnerabilities[*].remediations[*].group_ids[*]",
    "$.vulnerabilities[*].threats[*].group_ids[*]",
)


def defined_product_ids(document: Any) -> set[str]:
    return {
        value for _, value in strings(select_all(document, PRODUCT_DEFINITION_PATHS))
    }


def defined_group_ids(document: Any) -> set[str]:
    return {
        value
        for _, value in strings(
            select(document, "$.product_tree.product_groups[*].group_id")
        )
    }


def group_members(document: Any) -> dict[str, list[str]]:
    """``{group_id: [product_id, …]}`` of the product groups."""
    members: dict[str, list[str]] = {}

    for _, group in select(document, "$.product_tree.product_groups[*]"):
        group_id = get(group, "group_id")
        ids = get(group, "product_ids")
        if isinstance(group_id, str) and isinstance(ids, list):
            members.setdefault(group_id, []).extend(
                i for i in ids if isinstance(i, str)
            )

    return members
