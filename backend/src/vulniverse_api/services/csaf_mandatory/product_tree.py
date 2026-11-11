"""Mandatory tests: Product tree contents: branches, versions, product identification helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from itertools import pairwise
from typing import Any
from urllib.parse import unquote

from .core import Issue, Path, get, mandatory, select, select_all, strings

# --- Shared helpers -----------------------------------------------------------

_HELPER_PATHS = (
    "$.product_tree..branches[*].product.product_identification_helper",
    "$.product_tree.full_product_names[*].product_identification_helper",
    "$.product_tree.product_paths[*].full_product_name.product_identification_helper",
)


def _helper_values(
    document: Any, key: str, tail: str = "[*]"
) -> list[tuple[Path, Any]]:
    """``<helper>.<key><tail>`` under every product identification helper."""
    return select_all(document, [f"{path}.{key}{tail}" for path in _HELPER_PATHS])


def _branch_chains(document: Any) -> Iterator[list[tuple[Path, dict[str, Any]]]]:
    """For each branch defining a product: the branches leading to it, root first."""

    def walk(path: Path, branches: Any, chain: list[Any]) -> Iterator[list[Any]]:
        if not isinstance(branches, list):
            return
        for index, branch in enumerate(branches):
            if not isinstance(branch, dict):
                continue
            here = (*path, index)
            current = [*chain, (here, branch)]
            if "product" in branch:
                yield current
            yield from walk((*here, "branches"), branch.get("branches"), current)

    yield from walk(
        ("product_tree", "branches"), get(document, "product_tree", "branches"), []
    )


def _branch_names(document: Any, category: str) -> list[tuple[Path, str]]:
    """``name`` of every branch with the given ``category``."""
    return [
        ((*path, "name"), branch["name"])
        for path, branch in select(document, "$.product_tree..branches[*]")
        if isinstance(branch, dict)
        and branch.get("category") == category
        and isinstance(branch.get("name"), str)
    ]


# --- PURL (ECMA-427) ----------------------------------------------------------

# Registered PURL types' namespace rules and required qualifiers, from
# https://github.com/package-url/purl-spec/tree/main/types (2026-11-11).
_NAMESPACE_REQUIRED = {
    "alpm", "apk", "bitbucket", "composer", "deb", "git", "github", "golang",
    "huggingface", "maven", "qpkg", "rpm", "swift", "vscode-extension",
}  # fmt: skip
_NAMESPACE_PROHIBITED = {
    "bazel", "bitnami", "cargo", "chrome-extension", "cocoapods", "conda", "cran",
    "gem", "hackage", "julia", "mlflow", "nuget", "oci", "opam", "otp", "pub",
    "pypi", "vcpkg",
}  # fmt: skip
_REQUIRED_QUALIFIERS = {"julia": "uuid", "swid": "tag_id"}
# permitted_characters of name / version (pub's pattern is anchored at the start only)
_PERMITTED_NAME = {"chrome-extension": r"[a-p]{32}$", "pub": r"[a-z0-9_]"}
_PERMITTED_VERSION = {"chrome-extension": r"\d+(\.\d+){0,3}$"}

_PCHAR = r"(?:[A-Za-z0-9._~:-]|%[0-9A-Fa-f]{2})"
_SEGMENT = re.compile(f"{_PCHAR}+")
# Unencoded `/` in qualifier values (e.g. repository_url) is common and accepted.
_QUALIFIER_VALUE = re.compile(f"(?:{_PCHAR}|/)*")
_QUALIFIER_KEY = re.compile(r"[a-z][a-z0-9._-]*")
_PURL_TYPE = re.compile(r"[a-z][a-z0-9.-]*")

Purl = tuple[str, str, str, str | None, dict[str, str], str | None]


def _segments(text: str) -> list[str] | None:
    """Decoded ``/``-separated segments, None if any is empty or malformed."""
    parts = text.split("/")
    if not all(_SEGMENT.fullmatch(part) for part in parts):
        return None
    decoded = [unquote(part, errors="strict") for part in parts]
    return None if any("/" in part for part in decoded) else decoded


def _parse_purl(purl: str) -> Purl | None:
    """(type, namespace, name, version, qualifiers, subpath), None if invalid.

    Canonical form only, as CSAF requires: lowercase ``pkg:``, no ``pkg://``.
    """
    try:
        return _parse_purl_strict(purl)
    except UnicodeDecodeError:
        return None


def _parse_purl_strict(purl: str) -> Purl | None:
    remainder, hash_sign, subpath_text = purl.partition("#")
    remainder, question, qualifier_text = remainder.partition("?")
    if not remainder.startswith("pkg:"):
        return None
    purl_type, slash, rest = remainder[4:].partition("/")
    if not slash or not _PURL_TYPE.fullmatch(purl_type):
        return None

    subpath = None
    if hash_sign:
        segments = _segments(subpath_text.strip("/"))
        if segments is None or {".", ".."} & set(segments):
            return None
        subpath = "/".join(segments)

    qualifiers: dict[str, str] = {}
    if question:
        for pair in qualifier_text.split("&"):
            key, equals, value = pair.partition("=")
            if (
                not equals
                or not _QUALIFIER_KEY.fullmatch(key)
                or key in qualifiers
                or not _QUALIFIER_VALUE.fullmatch(value)
            ):
                return None
            qualifiers[key] = unquote(value, errors="strict")
        qualifiers = {key: value for key, value in qualifiers.items() if value}

    version = None
    if "@" in rest:
        rest, _, version_text = rest.rpartition("@")
        segments = _segments(version_text)
        if segments is None or len(segments) != 1:
            return None
        version = segments[0]
    namespace_text, _, name_text = rest.rpartition("/")
    name = _segments(name_text)
    namespace = _segments(namespace_text) if namespace_text else []
    if name is None or namespace is None:
        return None

    if purl_type in _NAMESPACE_REQUIRED and not namespace:
        return None
    if purl_type in _NAMESPACE_PROHIBITED and namespace:
        return None
    if _REQUIRED_QUALIFIERS.get(purl_type, "") not in {*qualifiers, ""}:
        return None
    if not re.match(_PERMITTED_NAME.get(purl_type, ""), name[0].lower()):
        return None
    if version and not re.match(_PERMITTED_VERSION.get(purl_type, ""), version):
        return None
    if purl_type == "cpan" and "::" in name[0]:  # stated in the type's note
        return None

    return (
        purl_type,
        "/".join(namespace),
        name[0],
        version,
        qualifiers,
        subpath,
    )


@mandatory("6.1.13", "PURL")
def purl(document: dict[str, Any]) -> Iterator[Issue]:
    for path, value in strings(_helper_values(document, "purls")):
        if _parse_purl(value) is None:
            yield Issue(path, f"invalid purl `{value}`")


@mandatory("6.1.42", "PURL Qualifiers")
def purl_qualifiers(document: dict[str, Any]) -> Iterator[Issue]:
    for path, purls in _helper_values(document, "purls", ""):
        if not isinstance(purls, list):
            continue
        first = None
        for index, value in enumerate(purls):
            parsed = _parse_purl(value) if isinstance(value, str) else None
            if parsed is None:
                continue  # 6.1.13 reports it
            without_qualifiers = parsed[:4] + parsed[5:]
            if first is None:
                first = without_qualifiers
            elif without_qualifiers != first:
                yield Issue(
                    (*path, index), "purls differ in more than their qualifiers"
                )


# --- Hashes -------------------------------------------------------------------


@mandatory("6.1.25", "Multiple Use of Same Hash Algorithm")
def multiple_hash_algorithm(document: dict[str, Any]) -> Iterator[Issue]:
    for path, file_hashes in _helper_values(document, "hashes", "[*].file_hashes"):
        if not isinstance(file_hashes, list):
            continue
        seen: set[str] = set()
        for index, algorithm in enumerate(get(i, "algorithm") for i in file_hashes):
            if not isinstance(algorithm, str):
                continue
            if algorithm in seen:
                yield Issue(
                    (*path, index, "algorithm"),
                    f"hash algorithm `{algorithm}` is used more than once",
                )
            seen.add(algorithm)


# Hex digest length of each fixed-length digest the spec lists (`openssl dgst -list`);
# shake128/shake256 have variable length: warned about, not checked.
_HASH_LENGTHS = {
    "blake2b512": 128, "blake2s256": 64, "md4": 32, "md5": 32, "md5-sha1": 72,
    "mdc2": 32, "ripemd": 40, "ripemd160": 40, "rmd160": 40, "sha1": 40,
    "sha224": 56, "sha256": 64, "sha3-224": 56, "sha3-256": 64, "sha3-384": 96,
    "sha3-512": 128, "sha384": 96, "sha512": 128, "sha512-224": 56,
    "sha512-256": 64, "sm3": 64, "ssl3-md5": 32, "ssl3-sha1": 40, "whirlpool": 128,
}  # fmt: skip


_VARIABLE_LENGTH = {"shake128", "shake256"}


@mandatory("6.1.63", "Inconsistent Hash Value Length")
def inconsistent_hash_length(document: dict[str, Any]) -> Iterator[Issue]:
    for path, file_hash in _helper_values(document, "hashes", "[*].file_hashes[*]"):
        algorithm, value = get(file_hash, "algorithm"), get(file_hash, "value")
        if not isinstance(algorithm, str):
            continue
        expected = _HASH_LENGTHS.get(algorithm)
        if expected is None:
            # The spec wants unsupported algorithms named, telling apart
            # the ones it lists (shake128/256: variable length) from others.
            listed = "listed in CSAF" if algorithm in _VARIABLE_LENGTH else "unknown"
            yield Issue(
                (*path, "algorithm"),
                f"hash algorithm `{algorithm}` ({listed}) is not supported, "
                "its length is not checked",
                "warning",
            )
        elif isinstance(value, str) and len(value) != expected:
            yield Issue(
                (*path, "value"),
                f"`{algorithm}` hash has {len(value)} characters, expected {expected}",
            )


# --- Wildcards ----------------------------------------------------------------


def _multiple_stars(document: Any, key: str, label: str) -> Iterator[Issue]:
    for path, value in strings(_helper_values(document, key)):
        if re.sub(r"\\.", "", value).count("*") > 1:
            yield Issue(path, f"{label} contains multiple unescaped stars")


@mandatory("6.1.43", "Use of Multiple Stars in Model Number")
def multiple_stars_model_number(document: dict[str, Any]) -> Iterator[Issue]:
    return _multiple_stars(document, "model_numbers", "model number")


@mandatory("6.1.44", "Use of Multiple Stars in Serial Number")
def multiple_stars_serial_number(document: dict[str, Any]) -> Iterator[Issue]:
    return _multiple_stars(document, "serial_numbers", "serial number")


@mandatory("6.1.61", "Use of Multiple Stars in SKU")
def multiple_stars_sku(document: dict[str, Any]) -> Iterator[Issue]:
    return _multiple_stars(document, "skus", "stock keeping unit")


# --- Branches -----------------------------------------------------------------


@mandatory("6.1.34", "Branches Recursion Depth")
def branches_recursion_depth(document: dict[str, Any]) -> Iterator[Issue]:
    for path, _ in select(document, "$.product_tree..branches[*].product"):
        depth = path.count("branches")
        if depth > 30:
            yield Issue(path, f"product is nested in {depth} branches (at most 30)")


@mandatory("6.1.57", "Stacked Branch Categories")
def stacked_branch_categories(document: dict[str, Any]) -> Iterator[Issue]:
    reported: set[Path] = set()

    for chain in _branch_chains(document):
        seen: set[Any] = set()
        for path, branch in chain:
            category = branch.get("category")
            if (
                category in seen
                and category != "product_family"
                and path not in reported
            ):
                reported.add(path)
                yield Issue(
                    (*path, "category"),
                    f"category `{category}` is used more than once along the path",
                )
            seen.add(category)


@mandatory("6.1.58", "Use of product_version in one Path with product_version_range")
def version_and_version_range(document: dict[str, Any]) -> Iterator[Issue]:
    reported: set[Path] = set()

    for chain in _branch_chains(document):
        categories = [branch.get("category") for _, branch in chain]
        if "product_version" in categories and "product_version_range" in categories:
            path = chain[
                max(
                    categories.index("product_version"),
                    categories.index("product_version_range"),
                )
            ][0]
            if path not in reported:
                reported.add(path)
                yield Issue(
                    (*path, "category"),
                    "both product_version and product_version_range are used "
                    "along the path",
                )


# --- Versions and version ranges ----------------------------------------------

_RANGE_WORDS = {"after", "all", "before", "earlier", "later", "prior", "versions"}


@mandatory("6.1.31", "Version Range in Product Version")
def version_range_in_product_version(document: dict[str, Any]) -> Iterator[Issue]:
    for path, name in _branch_names(document, "product_version"):
        lowered = name.lower()
        if "<" in lowered or ">" in lowered or _RANGE_WORDS & set(lowered.split()):
            yield Issue(path, f"product version `{name}` contains a version range")


_INTEGER_VERSION = re.compile(r"0|[1-9][0-9]*")
# https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
_SEMANTIC_VERSION = re.compile(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)


@mandatory("6.1.30", "Mixed Integer and Semantic Versioning")
def mixed_versioning(document: dict[str, Any]) -> Iterator[Issue]:
    first = None

    for path, version in strings(
        select_all(
            document,
            (
                "$.document.tracking.version",
                "$.document.tracking.revision_history[*].number",
            ),
        )
    ):
        if _INTEGER_VERSION.fullmatch(version):
            scheme = "integer"
        elif _SEMANTIC_VERSION.fullmatch(version):
            scheme = "semantic"
        else:
            continue  # neither: the schema test reports it
        first = first or scheme
        if scheme != first:
            yield Issue(
                path, f"version `{version}` uses {scheme} versioning, not {first}"
            )


_CONSTRAINT = re.compile(r"(!=|<=|>=|<|>)?(.*)", re.DOTALL)
# Printable ASCII; `<>=!*|%` only percent-encoded (VERS 5.3.3.2).
_VERS_VERSION = re.compile(r"(?:[\x21-\x7e]|%[0-9A-Fa-f]{2})+")
_VERS_FORBIDDEN = re.compile(r"[<>=!*|]|%(?![0-9A-Fa-f]{2})")


def _intdot_key(version: str) -> tuple[int, ...] | None:
    # Interpretation stops at the first character that is not a digit or dot.
    match = re.match(r"\d+(?:\.\d+)*", version)
    if match is None:
        return None
    key = [int(part) for part in match.group().split(".")]
    while len(key) > 1 and key[-1] == 0:
        key.pop()
    return tuple(key)


# VERS types whose version order this implementation knows; others are checked
# for everything but order, with a warning naming the type (as the spec asks).
def _semver_key(version: str) -> tuple[Any, ...] | None:
    """SemVer 2.0.0 precedence (build metadata ignored)."""
    match = _SEMANTIC_VERSION.fullmatch(version)
    if match is None:
        return None
    major, minor, patch, pre, _ = match.groups()
    identifiers = tuple(
        (0, int(part), "") if part.isdigit() else (1, 0, part)
        for part in (pre or "").split(".")
        if pre
    )
    return int(major), int(minor), int(patch), not pre, identifiers


_VERS_ORDER: dict[str, Callable[[str], Any]] = {
    "intdot": _intdot_key,
    "semver": _semver_key,
    "lexicographic": str.encode,
}

Constraint = tuple[str, str]


def _range_constraints(name: str) -> tuple[str | None, list[Constraint]] | None:
    """(VERS type or None for vls, [(comparator, version)]), None if malformed."""
    scheme = None
    body = name
    if name.startswith("vers:"):
        match = re.fullmatch(r"vers:([a-z][a-z0-9.-]*)/(.*)", name, re.DOTALL)
        if match is None:
            return None
        scheme, body = match.groups()
        if (body == "*") != (scheme == "all"):  # only `vers:all/*` means all
            return None
        if body == "*":
            return scheme, [("*", "")]

    constraints = []
    for part in body.split("|"):
        match = _CONSTRAINT.fullmatch(part)
        assert match is not None
        comparator, version = match.group(1) or "", match.group(2)
        if not _VERS_VERSION.fullmatch(version) or _VERS_FORBIDDEN.search(version):
            return None
        try:
            decoded = unquote(version, errors="strict")
        except UnicodeDecodeError:
            return None
        if re.search(r"[\t\n\v\f\r]", decoded):
            return None
        constraints.append((comparator, decoded))
    return scheme, constraints


def _single_version(constraints: list[Constraint]) -> bool:
    kept = [c for c in constraints if c[0] != "!="]
    if len(kept) == 2:
        (low, low_version), (high, high_version) = kept
        return low == ">=" and high == "<=" and low_version == high_version
    return len(kept) == 1 and kept[0][0] == ""


def _range_problem(name: str) -> str | None:
    parsed = _range_constraints(name)
    if parsed is None:
        return "is neither a valid vers nor a valid vls"
    scheme, constraints = parsed
    if scheme == "all":
        return None
    if scheme is None and _single_version(constraints):
        return "is a vls that identifies a single version"

    order = _VERS_ORDER.get(scheme or "")
    keys = [order(version) if order else version for _, version in constraints]
    if None in keys:
        return f"contains a version invalid for `{scheme}`"
    if len(set(keys)) != len(keys):
        return "contains a version more than once"
    if order and keys != sorted(keys):
        return "is not sorted by version"

    comparators = [comparator for comparator, _ in constraints if comparator != "!="]
    for current, following in pairwise(comparators):
        if current == "" and following not in ("", ">", ">="):
            return "has an equality constraint followed by a `<` or `<=` constraint"
    bounds = [comparator[0] for comparator in comparators if comparator]
    if any(a == b for a, b in pairwise(bounds)):
        return "does not alternate between lower and upper bounds"
    return None


@mandatory("6.1.50", "Product Version Range Rules")
def product_version_range_rules(document: dict[str, Any]) -> Iterator[Issue]:
    for path, name in _branch_names(document, "product_version_range"):
        problem = _range_problem(name)
        if problem:
            yield Issue(path, f"version range `{name}` {problem}")
            continue
        parsed = _range_constraints(name)
        scheme = parsed[0] if parsed else None
        if scheme not in (None, "all") and scheme not in _VERS_ORDER:
            yield Issue(
                path,
                f"vers type `{scheme}` is not supported, the order of its "
                "versions is not checked",
                "warning",
            )


@mandatory("6.1.59", "Single Version as Product Version Range")
def single_version_as_range(document: dict[str, Any]) -> Iterator[Issue]:
    for path, name in _branch_names(document, "product_version_range"):
        parsed = _range_constraints(name)
        if parsed and _single_version(parsed[1]):
            yield Issue(path, f"version range `{name}` identifies a single version")
