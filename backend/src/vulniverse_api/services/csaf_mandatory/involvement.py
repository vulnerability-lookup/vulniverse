"""Mandatory tests about the involvement (6.1.24, 6.1.64.1 to 6.1.64.13) and
document-local vulnerability IDs (6.1.65.1, 6.1.65.2)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Any

from .core import (
    Issue,
    Path,
    get,
    group_members,
    mandatory,
    select,
    select_all,
    strings,
)

ACTIONS = "$.document.involvement.actions[*]"
ENTITY_REFERENCE_PATHS = (
    "$.document.involvement.actions[*].acting_entity_refs[*]",
    "$.document.involvement.actions[*].receiving_entity_refs[*]",
)


def _actions(document: Any) -> list[tuple[Path, dict[str, Any]]]:
    return [(path, a) for path, a in select(document, ACTIONS) if isinstance(a, dict)]


def _strings(value: Any) -> list[str]:
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


def _is_group(ref: str) -> bool:
    return ref.startswith("EGID-")


def _entity_groups(document: Any) -> dict[str, set[str]]:
    groups: dict[str, set[str]] = {}
    for _, group in select(document, "$.document.involvement.entity_groups[*]"):
        group_id = get(group, "entity_group_id")
        if isinstance(group_id, str):
            groups.setdefault(group_id, set()).update(
                _strings(get(group, "entity_ids"))
            )
    return groups


def _expand(refs: Any, groups: dict[str, set[str]]) -> frozenset[str]:
    """Entity refs with each entity group replaced by its members."""
    return frozenset(
        member
        for ref in _strings(refs)
        for member in (groups.get(ref, ()) if _is_group(ref) else (ref,))
    )


def _duplicates(document: Any, expression: str, noun: str) -> Iterator[Issue]:
    seen: set[str] = set()
    for path, value in strings(select(document, expression)):
        if value in seen:
            yield Issue(path, f"{noun} `{value}` is defined more than once")
        seen.add(value)


def _missing(
    references: list[tuple[Path, str]], defined: set[str], noun: str
) -> Iterator[Issue]:
    for path, value in references:
        if value not in defined:
            yield Issue(path, f"definition of {noun} `{value}` missing")


def _defined(document: Any, expression: str) -> set[str]:
    return {value for _, value in strings(select(document, expression))}


def _instant(value: Any) -> Any:
    """The date as an aware datetime, so other timezones compare equal."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return value


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _signatures(document: Any) -> list[tuple[Path, tuple[Any, ...], dict[str, Any]]]:
    """Each action's content except `action_id`, `status` and `summary`,
    groups expanded (6.1.24, 6.1.64.2)."""
    entity_groups = _entity_groups(document)
    product_groups = group_members(document)
    all_vulns = frozenset(_defined(document, "$.vulnerabilities[*].dl_vuln_id"))
    signatures = []

    for path, action in _actions(document):
        products = set(_strings(action.get("product_ids")))
        for group_id in _strings(action.get("group_ids")):
            products.update(product_groups.get(group_id, ()))
        vulns = frozenset(_strings(action.get("dl_vuln_ids")))
        signature = (
            _text(action.get("category")),
            _instant(action.get("date")),
            _expand(action.get("acting_entity_refs"), entity_groups),
            _expand(action.get("receiving_entity_refs"), entity_groups),
            frozenset() if vulns == all_vulns else vulns,
            frozenset(products),
            frozenset(_strings(action.get("referenced_action_ids"))),
        )
        signatures.append((path, signature, action))

    return signatures


@mandatory("6.1.24", "Multiple Definition in Actions")
def multiple_definition_in_actions(document: dict[str, Any]) -> Iterator[Issue]:
    seen: dict[tuple[Any, ...], Any] = {}

    for path, signature, action in _signatures(document):
        key = (
            signature,
            _text(action.get("status")),
            _text(action.get("summary")),
        )
        if key in seen:
            yield Issue(path, f"action is the same as action `{seen[key]}`")
        else:
            seen[key] = action.get("action_id")


@mandatory("6.1.64.1", "Missing Receiving Entity Refs")
def missing_receiving_entity_refs(document: dict[str, Any]) -> Iterator[Issue]:
    for path, action in _actions(document):
        if (
            action.get("category")
            in ("confirmation", "coordination", "dispute", "notification")
            and "receiving_entity_refs" not in action
        ):
            yield Issue(path, "receiving_entity_refs missing")


@mandatory("6.1.64.2", "Contradicting Definition in Actions")
def contradicting_definition_in_actions(document: dict[str, Any]) -> Iterator[Issue]:
    seen: dict[tuple[Any, ...], list[dict[str, Any]]] = {}

    for path, signature, action in _signatures(document):
        status = _text(action.get("status"))
        for other in seen.get(signature, []):
            if _text(other.get("status")) != status:
                yield Issue(
                    path,
                    f"action contradicts action `{other.get('action_id')}` in status",
                )
                break
        seen.setdefault(signature, []).append(action)


@mandatory("6.1.64.3", "Missing Recipient on Attempt")
def missing_recipient_on_attempt(document: dict[str, Any]) -> Iterator[Issue]:
    for path, action in _actions(document):
        if (
            action.get("status") == "attempted"
            and "receiving_entity_refs" not in action
        ):
            yield Issue(path, "receiving_entity_refs missing on attempted action")


@mandatory("6.1.64.4", "Actor and Recipient")
def actor_and_recipient(document: dict[str, Any]) -> Iterator[Issue]:
    groups = _entity_groups(document)

    for path, action in _actions(document):
        both = _expand(action.get("acting_entity_refs"), groups) & _expand(
            action.get("receiving_entity_refs"), groups
        )
        for entity in sorted(both):
            yield Issue(path, f"entity `{entity}` is actor and recipient")


@mandatory("6.1.64.5", "Missing Definition of Entity ID")
def missing_entity_definition(document: dict[str, Any]) -> Iterator[Issue]:
    references = [
        (path, ref)
        for path, ref in strings(select_all(document, ENTITY_REFERENCE_PATHS))
        if not _is_group(ref)
    ] + strings(
        select(document, "$.document.involvement.entity_groups[*].entity_ids[*]")
    )
    yield from _missing(
        references,
        _defined(document, "$.document.involvement.entities[*].entity_id"),
        "entity id",
    )


@mandatory("6.1.64.6", "Multiple Definition of Entity ID")
def multiple_entity_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _duplicates(
        document, "$.document.involvement.entities[*].entity_id", "entity id"
    )


@mandatory("6.1.64.7", "Missing Definition of Entity Group ID")
def missing_entity_group_definition(document: dict[str, Any]) -> Iterator[Issue]:
    references = [
        (path, ref)
        for path, ref in strings(select_all(document, ENTITY_REFERENCE_PATHS))
        if _is_group(ref)
    ]
    yield from _missing(
        references,
        _defined(document, "$.document.involvement.entity_groups[*].entity_group_id"),
        "entity group id",
    )


@mandatory("6.1.64.8", "Multiple Definition of Entity Group ID")
def multiple_entity_group_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _duplicates(
        document,
        "$.document.involvement.entity_groups[*].entity_group_id",
        "entity group id",
    )


@mandatory("6.1.64.9", "Missing Definition of Action ID")
def missing_action_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _missing(
        strings(select(document, f"{ACTIONS}.referenced_action_ids[*]")),
        _defined(document, f"{ACTIONS}.action_id"),
        "action id",
    )


@mandatory("6.1.64.10", "Multiple Definition of Action ID")
def multiple_action_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _duplicates(document, f"{ACTIONS}.action_id", "action id")


@mandatory("6.1.64.11", "Circular Reference of Action ID")
def circular_action_reference(document: dict[str, Any]) -> Iterator[Issue]:
    references: dict[str, set[str]] = {}
    for _, action in _actions(document):
        action_id = action.get("action_id")
        if isinstance(action_id, str):
            references.setdefault(action_id, set()).update(
                _strings(action.get("referenced_action_ids"))
            )

    for path, action in _actions(document):
        action_id = action.get("action_id")
        if not isinstance(action_id, str):
            continue
        seen: set[str] = set()
        pending = _strings(action.get("referenced_action_ids"))
        while pending:
            current = pending.pop()
            if current == action_id:
                yield Issue(
                    (*path, "referenced_action_ids"),
                    f"action `{action_id}` refers to itself through its references",
                )
                break
            if current not in seen:
                seen.add(current)
                pending.extend(references.get(current, ()))


@mandatory("6.1.64.12", "Confirmation from Unmentioned Entity")
def confirmation_from_unmentioned_entity(document: dict[str, Any]) -> Iterator[Issue]:
    """Whoever confirms must have received each action being confirmed."""
    groups = _entity_groups(document)
    actions = _actions(document)

    for path, action in actions:
        if action.get("category") != "confirmation":
            continue
        acting = _expand(action.get("acting_entity_refs"), groups)

        for referenced_id in _strings(action.get("referenced_action_ids")):
            for _, referenced in actions:
                if referenced is action or referenced.get("action_id") != referenced_id:
                    continue
                receiving = _expand(referenced.get("receiving_entity_refs"), groups)
                for entity in sorted(acting - receiving):
                    yield Issue(
                        path,
                        f"confirming entity `{entity}` did not receive "
                        f"action `{referenced_id}`",
                    )


@mandatory("6.1.64.13", "Missing Referenced Action IDs")
def missing_referenced_action_ids(document: dict[str, Any]) -> Iterator[Issue]:
    for path, action in _actions(document):
        if (
            action.get("category") in ("confirmation", "dispute")
            and "referenced_action_ids" not in action
        ):
            yield Issue(path, "referenced_action_ids missing")


@mandatory("6.1.65.1", "Missing Definition of Document-local Vuln ID")
def missing_vuln_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _missing(
        strings(select(document, f"{ACTIONS}.dl_vuln_ids[*]")),
        _defined(document, "$.vulnerabilities[*].dl_vuln_id"),
        "document-local vuln id",
    )


@mandatory("6.1.65.2", "Multiple Definition of Document-local Vuln ID")
def multiple_vuln_definition(document: dict[str, Any]) -> Iterator[Issue]:
    yield from _duplicates(
        document, "$.vulnerabilities[*].dl_vuln_id", "document-local vuln id"
    )
