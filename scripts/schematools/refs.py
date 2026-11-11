"""Inline ``$ref`` references, so the editor gets one self-contained schema.

JSON Forms renders a schema by walking its properties; it cannot follow a
reference into another file, and the editor's validator only knows draft-07.
So the generator replaces every reference with a copy of its target.
"""

import copy
import json
from typing import Any

from .errors import GenerationError
from .jsontypes import JsonObject

# (id of the schema document, JSON pointer inside it). The document is part
# of the key because two files may share a local pointer like "#/$defs/x".
RefKey = tuple[int, str]


def decode_pointer_token(token: str) -> str:
    return token.replace("~1", "/").replace("~0", "~")


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    """The value ``pointer`` (``#`` or ``#/a/b/0``) points to in ``document``."""
    if pointer == "#":
        return document

    if not pointer.startswith("#/"):
        raise GenerationError(f"Only local JSON references are supported: {pointer}")

    current = document

    for raw_token in pointer[2:].split("/"):
        token = decode_pointer_token(raw_token)

        if isinstance(current, dict):
            if token not in current:
                raise GenerationError(f"Reference does not exist: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            try:
                current = current[int(token)]
            except (ValueError, IndexError) as error:
                raise GenerationError(f"Invalid list reference: {pointer}") from error
        else:
            raise GenerationError(f"Reference cannot be traversed: {pointer}")

    return current


def dereference(
    node: Any,
    root: JsonObject,
    active_refs: tuple[RefKey, ...] = (),
    resources: dict[str, JsonObject] | None = None,
    in_resource: bool = False,
) -> Any:
    """A copy of ``node`` with its ``$ref`` values inlined.

    Local references (``#/...``) resolve against ``root``. A reference to a
    URL listed in ``resources`` (the manifest's ``schemaResources``, e.g.
    CSAF's CVSS schemas) is inlined from that file, whose own local
    references then resolve against it. Other external references are left
    as they are.

    A reference that is already being expanded higher up (``active_refs``)
    is recursive and stays a ``$ref``; inside a resource that would point
    into the wrong document, so it is an error there.
    """

    def descend(value: Any) -> Any:
        return dereference(value, root, active_refs, resources, in_resource)

    if isinstance(node, list):
        return [descend(item) for item in node]

    if not isinstance(node, dict):
        return copy.deepcopy(node)

    reference = node.get("$ref")

    if not isinstance(reference, str):
        return {key: descend(value) for key, value in node.items()}

    if reference.startswith("#/"):
        target_root, pointer, inside = root, reference, in_resource
    else:
        url, _, fragment = reference.partition("#")
        target = (resources or {}).get(url)

        if target is None:
            return {key: descend(value) for key, value in node.items()}

        target_root, pointer, inside = target, f"#{fragment}" if fragment else "#", True

    key = (id(target_root), pointer)

    if key in active_refs:
        if inside:
            # Kept as-is it would resolve against the main schema instead.
            raise GenerationError(f"Recursive reference inside a schema resource: {reference}")
        return copy.deepcopy(node)

    expanded = dereference(
        resolve_json_pointer(target_root, pointer),
        target_root,
        active_refs + (key,),
        resources,
        inside,
    )

    if not isinstance(expanded, dict):
        return expanded

    result = copy.deepcopy(expanded)

    if target_root is not root and pointer == "#":
        # A whole schema file inlined: its own dialect and identity
        # declarations would confuse the editor's validator, e.g. the
        # draft-04 "id" of FIRST's CVSS 2.0/3.0 schemas.
        for declaration in ("$schema", "$id", "id"):
            if isinstance(result.get(declaration), str):
                del result[declaration]

    # Keywords next to the $ref (e.g. a title) are kept on top.
    for name, value in node.items():
        if name != "$ref":
            result[name] = descend(value)

    return result


def drop_unused_definitions(schema: JsonObject) -> None:
    """Remove ``$defs``/``definitions`` once nothing points into them.

    After :func:`dereference` only recursive references remain (CSAF's
    product tree); those still need the definitions they point into.
    """
    serialized = json.dumps(schema)

    for container in ("$defs", "definitions"):
        if f'"#/{container}/' not in serialized:
            schema.pop(container, None)


def strip_nested_ids(node: Any, *, is_root: bool = True) -> None:
    """Remove ``$id`` from inlined subschemas, in place.

    The same ``$id`` inlined twice makes Ajv report that one identifier
    resolves to several schemas.
    """
    if isinstance(node, list):
        for item in node:
            strip_nested_ids(item, is_root=False)
        return

    if not isinstance(node, dict):
        return

    if not is_root:
        node.pop("$id", None)

    for value in node.values():
        strip_nested_ids(value, is_root=False)
