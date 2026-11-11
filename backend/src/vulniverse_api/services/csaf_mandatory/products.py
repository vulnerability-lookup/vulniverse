"""Mandatory tests about product and product group IDs (6.1.1 to 6.1.5)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .core import (
    GROUP_REFERENCE_PATHS,
    PRODUCT_DEFINITION_PATHS,
    PRODUCT_REFERENCE_PATHS,
    Issue,
    defined_group_ids,
    defined_product_ids,
    get,
    mandatory,
    select,
    select_all,
    strings,
)


@mandatory("6.1.1", "Missing Definition of Product ID")
def missing_product_definition(document: dict[str, Any]) -> Iterator[Issue]:
    defined = defined_product_ids(document)

    for path, product_id in strings(select_all(document, PRODUCT_REFERENCE_PATHS)):
        if product_id not in defined:
            yield Issue(path, f"definition of product id `{product_id}` missing")


@mandatory("6.1.2", "Multiple Definition of Product ID")
def multiple_product_definition(document: dict[str, Any]) -> Iterator[Issue]:
    seen: set[str] = set()

    for path, product_id in strings(select_all(document, PRODUCT_DEFINITION_PATHS)):
        if product_id in seen:
            yield Issue(path, f"product id `{product_id}` is defined more than once")
        seen.add(product_id)


@mandatory("6.1.3", "Circular Definition of Product ID")
def circular_product_definition(document: dict[str, Any]) -> Iterator[Issue]:
    """A product path may not lead back, directly or through other
    product paths, to the product it defines."""
    # {defined product id: the ids its path is built from}
    built_from: dict[str, set[str]] = {}
    definitions = []

    for path, product_path in select(document, "$.product_tree.product_paths[*]"):
        defined = get(product_path, "full_product_name", "product_id")
        if not isinstance(defined, str):
            continue

        references = {
            value
            for _, value in strings(
                [
                    *select(product_path, "$.beginning_product_reference"),
                    *select(product_path, "$.subpaths[*].next_product_reference"),
                ]
            )
        }
        built_from.setdefault(defined, set()).update(references)
        definitions.append((path, defined))

    for path, defined in definitions:
        seen: set[str] = set()
        pending = list(built_from[defined])

        while pending:
            current = pending.pop()
            if current == defined:
                yield Issue(
                    (*path, "full_product_name", "product_id"),
                    f"product id `{defined}` is defined through itself",
                )
                break
            if current not in seen:
                seen.add(current)
                pending.extend(built_from.get(current, ()))


@mandatory("6.1.4", "Missing Definition of Product Group ID")
def missing_group_definition(document: dict[str, Any]) -> Iterator[Issue]:
    defined = defined_group_ids(document)

    for path, group_id in strings(select_all(document, GROUP_REFERENCE_PATHS)):
        if group_id not in defined:
            yield Issue(path, f"definition of product group id `{group_id}` missing")


@mandatory("6.1.5", "Multiple Definition of Product Group ID")
def multiple_group_definition(document: dict[str, Any]) -> Iterator[Issue]:
    seen: set[str] = set()

    for path, group_id in strings(
        select(document, "$.product_tree.product_groups[*].group_id")
    ):
        if group_id in seen:
            yield Issue(
                path, f"product group id `{group_id}` is defined more than once"
            )
        seen.add(group_id)
