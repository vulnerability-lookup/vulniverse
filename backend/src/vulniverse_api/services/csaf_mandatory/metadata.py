"""Mandatory tests: Document metadata: language, category, translation, distribution, licenses, extensions."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from ..profiles import SCHEMAS_ROOT
from .core import Issue, get, mandatory, select, select_all, strings

DATA = Path(__file__).parent / "data"


@cache
def _data(name: str) -> dict[str, set[str]]:
    """A vendored registry extract (see its ``_source``): ``{key: {value, …}}``."""
    raw = json.loads((DATA / name).read_text(encoding="utf-8"))
    return {key: set(value.split()) for key, value in raw.items() if key != "_source"}


# --- 6.1.12 Language -----------------------------------------------------------

# RFC 5646 langtag (lower case); private use and grandfathered tags are handled apart.
_LANGTAG = re.compile(
    r"(?P<language>[a-z]{2,3}(?:-[a-z]{3}){0,3}|[a-z]{4,8})"
    r"(?:-(?P<script>[a-z]{4}))?"
    r"(?:-(?P<region>[a-z]{2}|\d{3}))?"
    r"(?P<variants>(?:-(?:[a-z0-9]{5,8}|\d[a-z0-9]{3}))*)"
    r"(?P<extensions>(?:-[a-wyz0-9](?:-[a-z0-9]{2,8})+)*)"
    r"(?:-x(?:-[a-z0-9]{1,8})+)?"
)
_PRIVATE_USE = re.compile(r"x(?:-[a-z0-9]{1,8})+")


def language_problem(tag: str) -> str | None:
    """Why ``tag`` isn't a valid BCP 47 language tag (RFC 5646), or None.
    Shared with the SSVC namespace test (6.1.46)."""
    registry = _data("language-subtags.json")
    lowered = tag.lower()
    if lowered in registry["grandfathered"] or _PRIVATE_USE.fullmatch(lowered):
        return None

    match = _LANGTAG.fullmatch(lowered)
    if match is None:
        return f"language tag `{tag}` is invalid"

    primary, *extlangs = match["language"].split("-")
    variants = match["variants"].split("-")[1:]
    singletons = re.findall(r"-([a-wyz0-9])(?=-)", match["extensions"] or "")
    slots = [
        ("language", primary),
        *(("extlang", extlang) for extlang in extlangs),
        ("script", match["script"]),
        ("region", match["region"]),
        *(("variant", variant) for variant in variants),
    ]
    misplaced = []
    for kind, subtag in slots:
        if subtag is None or subtag in registry[kind]:
            continue
        if not any(subtag in subtags for subtags in registry.values()):
            return (
                f"language tag `{tag}` contains subtag `{subtag}` not in the registry"
            )
        misplaced.append(subtag)

    if misplaced or len(set(variants)) < len(variants):
        return f"language tag `{tag}` is invalid although its subtags are registered"
    if len(set(singletons)) < len(singletons):
        return f"language tag `{tag}` repeats an extension"
    return None


@mandatory("6.1.12", "Language")
def language(document: dict[str, Any]) -> Iterator[Issue]:
    for path, tag in strings(
        select_all(document, ("$.document.lang", "$.document.source_lang"))
    ):
        problem = language_problem(tag)
        if problem:
            yield Issue(path, problem)


# --- 6.1.15 Translator, 6.1.28 Translation ---------------------------------------


@mandatory("6.1.15", "Translator")
def translator(document: dict[str, Any]) -> Iterator[Issue]:
    if get(document, "document", "publisher", "category") != "translator":
        return
    meta = get(document, "document")
    if "source_lang" not in meta:
        yield Issue(("document",), "`source_lang` is missing for a translator")
    elif not meta["source_lang"]:
        yield Issue(
            ("document", "source_lang"), "`source_lang` is empty for a translator"
        )


@mandatory("6.1.28", "Translation")
def translation(document: dict[str, Any]) -> Iterator[Issue]:
    lang = get(document, "document", "lang")
    source_lang = get(document, "document", "source_lang")
    if (
        isinstance(lang, str)
        and isinstance(source_lang, str)
        and lang.lower() == source_lang.lower()
    ):
        yield Issue(
            ("document", "source_lang"),
            f"document language and source language are both `{source_lang}`",
        )


# --- 6.1.26 Prohibited Document Category Name -----------------------------------

_PROFILE_VALUES = {
    "csaf_deprecated_security_advisory",
    "csaf_informational_advisory",
    "csaf_security_advisory",
    "csaf_security_incident_response",
    "csaf_superseded",
    "csaf_vex",
    "csaf_withdrawn",
    "csaf_vulnerability_report",
}
# Graphical variants of dash, hyphen, minus and underscore outside the categories
# stripped below (the ones the spec's test documents use).
_DASH_VARIANTS = {
    chr(code)
    for code in (
        *(0x02CD, 0x02D7, 0x0332, 0x0333, 0x034F, 0x2017, 0x2043, 0x2053),
        *(0x207B, 0x208B, 0x2212, 0x23AF, 0x23B5, 0x23BA, 0x23BB, 0x23BC),
        *(0x23BD, 0x23E4, 0x2500, 0x2501, 0x254C, 0x254D, 0x2574, 0x2576),
        *(0x2578, 0x257A, 0x2581, 0x2796, 0x29FF, 0x1BC03, 0x1BC08, 0x1BC0D),
        *(0x1BC11, 0x1BC12, 0x1BC13, 0x1BC86, 0x1BC96, 0x1BC97, 0x1BC99),
    )
}


def _squash(value: str) -> str:
    """Drop dashes, underscores, white space and invisible characters; fold case."""
    return "".join(
        char
        for char in value
        if char not in _DASH_VARIANTS
        and not char.isspace()
        and unicodedata.category(char) not in ("Pd", "Pc", "Zs", "Cc", "Cf")
    ).casefold()


_PROHIBITED = {_squash(value) for value in _PROFILE_VALUES} | {
    _squash(value.removeprefix("csaf_")) for value in _PROFILE_VALUES
}


@mandatory("6.1.26", "Prohibited Document Category Name")
def prohibited_category(document: dict[str, Any]) -> Iterator[Issue]:
    for path, category in strings(select(document, "$.document.category")):
        if category in _PROFILE_VALUES or category == "csaf_base":
            continue
        if category.casefold().startswith("csaf_"):
            yield Issue(path, f"category `{category}` uses the reserved prefix `csaf_`")
        elif _squash(category) in _PROHIBITED:
            yield Issue(path, f"category `{category}` is the name of another profile")


# --- 6.1.38 to 6.1.41 Sharing group ---------------------------------------------

MAX_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
NIL_UUID = "00000000-0000-0000-0000-000000000000"
RESERVED_NAMES = {MAX_UUID: "Public", NIL_UUID: "No sharing allowed"}
SHARING_GROUP = ("document", "distribution", "sharing_group")


@mandatory("6.1.38", "Non-Public Sharing Group with Max UUID")
def non_public_max_uuid(document: dict[str, Any]) -> Iterator[Issue]:
    if get(document, *SHARING_GROUP, "id") != MAX_UUID:
        return
    for path, label in strings(select(document, "$.document.distribution.tlp.label")):
        if label != "CLEAR":
            yield Issue(path, f"max uuid sharing group used with `TLP:{label}`")


@mandatory("6.1.39", "Public Sharing Group with No Max UUID")
def public_without_max_uuid(document: dict[str, Any]) -> Iterator[Issue]:
    if get(document, "document", "distribution", "tlp", "label") != "CLEAR":
        return
    draft = get(document, "document", "tracking", "status") == "draft"
    for path, group_id in strings(
        select(document, "$.document.distribution.sharing_group.id")
    ):
        if group_id != MAX_UUID and not (group_id == NIL_UUID and draft):
            yield Issue(path, f"`TLP:CLEAR` document uses sharing group `{group_id}`")


@mandatory("6.1.40", "Invalid Sharing Group Name")
def invalid_sharing_group_name(document: dict[str, Any]) -> Iterator[Issue]:
    group_id = get(document, *SHARING_GROUP, "id")
    for path, name in strings(
        select(document, "$.document.distribution.sharing_group.name")
    ):
        for reserved_id, reserved_name in RESERVED_NAMES.items():
            if name == reserved_name and group_id != reserved_id:
                yield Issue(
                    path, f"name `{name}` is reserved for sharing group `{reserved_id}`"
                )


@mandatory("6.1.41", "Missing Sharing Group Name")
def missing_sharing_group_name(document: dict[str, Any]) -> Iterator[Issue]:
    group = get(document, *SHARING_GROUP)
    expected = RESERVED_NAMES.get(get(group, "id"))
    if expected is None:
        return
    if "name" not in group:
        yield Issue(SHARING_GROUP, f"sharing group name `{expected}` missing")
    elif group["name"] != expected:
        yield Issue(
            (*SHARING_GROUP, "name"), f"sharing group name must be `{expected}`"
        )


# --- 6.1.54 License Expression, 6.1.55 License Text -----------------------------

_IDSTRING = r"[A-Za-z0-9.\-]+"
_LICENSE_REF = re.compile(rf"LicenseRef-{_IDSTRING}")
_ADDITION_REF = re.compile(rf"AdditionRef-{_IDSTRING}")
_LICENSE_ID = re.compile(rf"{_IDSTRING}\+?")
_RESERVED_PREFIX = re.compile(r"(licenseref|additionref|documentref)-", re.IGNORECASE)
_TOKEN = re.compile(r"[()]| |[^() ]+")


def _license_expression_error(expression: str) -> str | None:
    """Annex B ABNF of SPDX 3.1 with CSAF's restrictions: no ``DocumentRef``,
    case-sensitive operators and prefixes, single spaces between tokens."""
    if expression != expression.strip(" ") or "  " in expression:
        return "unexpected white space"
    words = [token for token in _TOKEN.findall(expression) if token != " "]
    position = 0

    def peek() -> str | None:
        return words[position] if position < len(words) else None

    def take() -> str:
        nonlocal position
        position += 1
        return words[position - 1]

    def operand(reference: re.Pattern[str]) -> None:
        if peek() is None:
            raise ValueError("unexpected end")
        word = take()
        if _RESERVED_PREFIX.match(word):
            # Only `LicenseRef-`/`AdditionRef-` in this exact case; no DocumentRef.
            valid = bool(reference.fullmatch(word))
        else:
            valid = bool(_LICENSE_ID.fullmatch(word)) and (
                reference is _LICENSE_REF or not word.endswith("+")
            )
        if word in ("AND", "OR", "WITH") or not valid:
            raise ValueError(f"unexpected `{word}`")

    def term() -> None:
        if peek() == "(":
            take()
            disjunction()
            if peek() != ")":
                raise ValueError("missing `)`")
            take()
            return
        operand(_LICENSE_REF)
        if peek() == "WITH":
            take()
            operand(_ADDITION_REF)

    def conjunction() -> None:
        term()
        while peek() == "AND":
            take()
            term()

    def disjunction() -> None:
        conjunction()
        while peek() == "OR":
            take()
            conjunction()

    try:
        disjunction()
    except ValueError as error:
        return str(error)
    return None if peek() is None else f"unexpected `{peek()}`"


@mandatory("6.1.54", "License Expression")
def license_expression(document: dict[str, Any]) -> Iterator[Issue]:
    for path, expression in strings(select(document, "$.document.license_expression")):
        error = _license_expression_error(expression)
        if error:
            yield Issue(path, f"invalid license expression: {error}")


def _is_listed(identifier: str) -> bool:
    """In the SPDX License List or AboutCode's ScanCode LicenseDB."""
    lists = _data("licenses.json")
    lowered = identifier.removesuffix("+").lower()
    for prefix in ("licenseref-scancode-", "additionref-scancode-"):
        if lowered.startswith(prefix):
            return lowered.removeprefix(prefix) in lists["scancode"]
    return lowered in lists["spdx"] or lowered in lists["spdx_exceptions"]


@mandatory("6.1.55", "License Text")
def license_text(document: dict[str, Any]) -> Iterator[Issue]:
    expression = get(document, "document", "license_expression")
    lang = get(document, "document", "lang")
    if not isinstance(expression, str) or (
        isinstance(lang, str) and lang.lower().split("-")[0] != "en"
    ):
        return
    identifiers = re.findall(r"[^\s()]+", expression)
    if all(
        _is_listed(word) for word in identifiers if word not in ("AND", "OR", "WITH")
    ):
        return

    notes = [
        (path, note)
        for path, note in select(document, "$.document.notes[*]")
        if get(note, "title") == "License"
    ]
    if len(notes) != 1:
        yield Issue(
            ("document", "notes") if "notes" in document["document"] else ("document",),
            f"exactly one note with title `License` required, found {len(notes)}",
        )
    elif get(notes[0][1], "category") != "legal_disclaimer":
        path, note = notes[0]
        yield Issue(
            (*path, "category") if "category" in note else path,
            "license note must have category `legal_disclaimer`",
        )


# --- 6.1.60.1 Extension Content Schema ------------------------------------------

_EXTENSION_PATHS = (
    "$.document.x_extensions[*]",
    "$.product_tree..branches[*].product.x_extensions[*]",
    "$.product_tree.full_product_names[*].x_extensions[*]",
    "$.product_tree.product_paths[*].full_product_name.x_extensions[*]",
    "$.vulnerabilities[*].metrics[*].content.x_extensions[*]",
    "$.vulnerabilities[*].x_extensions[*]",
    "$.x_extensions[*]",
)
_SCHEMA_URL = "https://docs.oasis-open.org/csaf/csaf/v2.1/schema/"


@cache
def _extension_content_validator() -> Draft202012Validator:
    folder = SCHEMAS_ROOT / "upstream" / "csaf" / "2.1" / "json_schema"
    schemas = {
        name: json.loads((folder / name).read_text(encoding="utf-8"))
        for name in ("extension-content.json", "extension-metaschema.json")
    }
    registry: Registry[Any] = Registry().with_resources(
        (_SCHEMA_URL + name, DRAFT202012.create_resource(schema))
        for name, schema in schemas.items()
    )
    return Draft202012Validator(schemas["extension-content.json"], registry=registry)


@mandatory("6.1.60.1", "Content Schema")
def extension_content_schema(document: dict[str, Any]) -> Iterator[Issue]:
    validator = _extension_content_validator()
    for path, extension in select_all(document, _EXTENSION_PATHS):
        for error in validator.iter_errors(extension):
            yield Issue(
                (*path, *error.absolute_path),
                f"extension content schema: {error.message}",
            )
