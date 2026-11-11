"""Mandatory tests: Document tracking: revision history, versions, status and dates."""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from itertools import pairwise
from typing import Any, NamedTuple

from .core import Issue, Path, get, mandatory, select, select_all, strings

# --- Date-time (spec 3.2 "Date and Time") ---------------------------------

_DATE_TIME = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]+))?(?:Z|([+-])([0-9]{2}):([0-9]{2}))"
)
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

Instant = tuple[int, Decimal]


def _instant(value: Any) -> Instant | None:
    """``(epoch seconds, fraction)`` of an RFC 3339 date-time without leap
    seconds, or None. The fraction stays exact: tests compare beyond µs."""
    match = _DATE_TIME.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        return None
    year, month, day, hour, minute, second = (int(g) for g in match.groups()[:6])
    fraction, sign, offset_hour, offset_minute = match.groups()[6:]
    if hour > 23 or minute > 59 or second > 59:
        return None
    offset = timedelta()
    if sign:
        if int(offset_hour) > 23 or int(offset_minute) > 59:
            return None
        offset = timedelta(hours=int(offset_hour), minutes=int(offset_minute))
        offset = -offset if sign == "-" else offset
    try:
        # shortcut: datetime rejects year 0000, which RFC 3339 allows; irrelevant
        # for advisories, upgrade if it ever matters.
        moment = datetime(
            year, month, day, hour, minute, second, tzinfo=timezone(offset)
        )
    except ValueError:
        return None
    elapsed = moment - _EPOCH
    return elapsed.days * 86400 + elapsed.seconds, Decimal(f"0.{fraction or 0}")


# --- Versions (spec 3.1.11 "Version Type") --------------------------------

_IDENTIFIER = r"(?:0|[1-9][0-9]*|[0-9]*[a-zA-Z-][0-9a-zA-Z-]*)"
_INTEGER_VERSION = re.compile(r"0|[1-9][0-9]*")
_SEMANTIC_VERSION = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    rf"(?:-({_IDENTIFIER}(?:\.{_IDENTIFIER})*))?"
    r"(?:\+[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*)?"
)


class _Version(NamedTuple):
    core: tuple[int, int, int]  # integer versions map to `n.0.0`
    pre: tuple[str, ...]  # empty for a release
    integer: bool

    @property
    def key(self) -> tuple[Any, ...]:
        """Precedence: build metadata ignored, a pre-release before its release."""
        if not self.pre:
            return (self.core, (1,))
        return (
            self.core,
            (0, tuple((0, int(i), "") if i.isdigit() else (1, 0, i) for i in self.pre)),
        )


def _version(value: Any) -> _Version | None:
    if not isinstance(value, str):
        return None
    if _INTEGER_VERSION.fullmatch(value):
        return _Version((int(value), 0, 0), (), True)
    match = _SEMANTIC_VERSION.fullmatch(value)
    if match is None:
        return None
    major, minor, patch, pre = match.groups()
    return _Version(
        (int(major), int(minor), int(patch)),
        tuple(pre.split(".")) if pre else (),
        False,
    )


# --- Revision history -----------------------------------------------------

_HISTORY = ("document", "tracking", "revision_history")


class _Revision(NamedTuple):
    instant: Instant
    version: _Version
    date: str
    number: str


def _sorted_history(document: Any) -> list[_Revision]:
    """Items sorted by `date`, then `number`; items whose date or number
    can't be parsed are left out (the schema test reports them)."""
    revisions = []
    for _, item in select(document, "$.document.tracking.revision_history[*]"):
        instant = _instant(get(item, "date"))
        version = _version(get(item, "number"))
        if instant is not None and version is not None:
            revisions.append(_Revision(instant, version, item["date"], item["number"]))
    return sorted(revisions, key=lambda r: (r.instant, r.version.key))


def _newest_revision(document: Any) -> Instant | None:
    dates = [
        instant
        for _, value in select(document, "$.document.tracking.revision_history[*].date")
        if (instant := _instant(value)) is not None
    ]
    return max(dates, default=None)


def _status(document: Any) -> Any:
    return get(document, "document", "tracking", "status")


def _released(document: Any) -> bool:
    return _status(document) in ("final", "interim")


def _numbers(document: Any) -> list[tuple[Path, str]]:
    return strings(select(document, "$.document.tracking.revision_history[*].number"))


@mandatory("6.1.14", "Sorted Revision History")
def sorted_revision_history(document: dict[str, Any]) -> Iterator[Issue]:
    history = _sorted_history(document)

    if any(a.version.key > b.version.key for a, b in pairwise(history)):
        yield Issue(
            _HISTORY,
            "items must be in ascending order when sorted by `date` and `number`",
        )


@mandatory("6.1.16", "Latest Document Version")
def latest_document_version(document: dict[str, Any]) -> Iterator[Issue]:
    for path, version in strings(select(document, "$.document.tracking.version")):
        history = _sorted_history(document)
        if _version(version) is None or not history:
            continue

        def comparable(value: str) -> str:
            value = value.split("+")[0]
            return value.split("-")[0] if _status(document) == "draft" else value

        latest = history[-1].number
        if comparable(version) != comparable(latest):
            yield Issue(
                path,
                f"document version `{version}` differs from the number `{latest}`"
                " of the last revision history item",
            )


@mandatory("6.1.17", "Document Status Draft")
def document_status_draft(document: dict[str, Any]) -> Iterator[Issue]:
    version = _version(get(document, "document", "tracking", "version"))

    if version is None or not (version.core[0] == 0 or version.pre):
        return
    for path, status in strings(select(document, "$.document.tracking.status")):
        if status != "draft":
            yield Issue(
                path, f"document status must be `draft` for this version (was {status})"
            )


@mandatory("6.1.18", "Released Revision History")
def released_revision_history(document: dict[str, Any]) -> Iterator[Issue]:
    if not _released(document):
        return
    for path, number in _numbers(document):
        version = _version(number)
        if version is not None and version.core[0] == 0:
            yield Issue(
                path,
                f"revision history of a `{_status(document)}` document contains"
                f" pre-release development version `{number}`",
            )


@mandatory("6.1.19", "Revision History Entries for Pre-release Versions")
def pre_release_revision(document: dict[str, Any]) -> Iterator[Issue]:
    for path, number in _numbers(document):
        version = _version(number)
        if version is not None and version.pre:
            yield Issue(path, f"revision history contains pre-release `{number}`")


@mandatory("6.1.20", "Non-Draft Document Version")
def non_draft_document_version(document: dict[str, Any]) -> Iterator[Issue]:
    if not _released(document):
        return
    for path, value in strings(select(document, "$.document.tracking.version")):
        version = _version(value)
        if version is not None and version.pre:
            yield Issue(
                path,
                f"version `{value}` of a `{_status(document)}` document"
                " contains a pre-release part",
            )


def _between(
    low: tuple[int, int, int], high: tuple[int, int, int]
) -> Iterator[tuple[int, int, int]]:
    """Versions that must exist between ``low`` and ``high`` (exclusive); minor
    and patch may end anywhere when the next major or minor follows."""
    current = low
    while True:
        major, minor, patch = current
        if major < high[0]:
            current = (major + 1, 0, 0)
        elif minor < high[1]:
            current = (major, minor + 1, 0)
        else:
            current = (major, minor, patch + 1)
        if current >= high:
            return
        yield current


@mandatory("6.1.21", "Missing Item in Revision History")
def missing_revision(document: dict[str, Any]) -> Iterator[Issue]:
    history = _sorted_history(document)
    if not history:
        return

    integer = all(revision.version.integer for revision in history)
    present = {r.version.core for r in history if not r.version.pre}

    def missing(core: tuple[int, int, int], where: str) -> Issue:
        number = str(core[0]) if integer else ".".join(map(str, core))
        where = where if core in present else "at all"
        return Issue(
            _HISTORY, f"missing revision history item with number `{number}` {where}"
        )

    first = history[0]
    if first.version.core[0] > 1:
        allowed = "`0` or `1`" if integer else "`0.y.z` or `1.0.0`"
        yield Issue(
            _HISTORY,
            f"revision history does not start with a version of {allowed}"
            f" when sorted by date (was `{first.number}`)",
        )
        for core in [(1, 0, 0), *_between((1, 0, 0), first.version.core)]:
            yield missing(core, f"before `{first.date}`")

    # Items lower than the highest seen so far are out of order; 6.1.14 reports them.
    highest = first
    for revision in history[1:]:
        if revision.version.core > highest.version.core:
            for core in _between(highest.version.core, revision.version.core):
                yield missing(core, f"between `{highest.date}` and `{revision.date}`")
            highest = revision


@mandatory("6.1.22", "Multiple Definition in Revision History")
def multiple_revision(document: dict[str, Any]) -> Iterator[Issue]:
    seen: set[str] = set()

    for path, number in _numbers(document):
        if number in seen:
            yield Issue(path, f"revision history contains number `{number}` twice")
        seen.add(number)


_DATE_TIME_PATHS = (
    "$.document.involvement.actions[*].date",
    "$.document.tracking.current_release_date",
    "$.document.tracking.generator.date",
    "$.document.tracking.initial_release_date",
    "$.document.tracking.revision_history[*].date",
    "$.vulnerabilities[*].disclosure_date",
    "$.vulnerabilities[*].discovery_date",
    "$.vulnerabilities[*].first_known_exploitation_dates[*].date",
    "$.vulnerabilities[*].first_known_exploitation_dates[*].exploitation_date",
    "$.vulnerabilities[*].flags[*].date",
    "$.vulnerabilities[*].metrics[*].content.epss.timestamp",
    "$.vulnerabilities[*].metrics[*].content.ssvc_v2.timestamp",
    "$.vulnerabilities[*].remediations[*].date",
    "$.vulnerabilities[*].threats[*].date",
)


@mandatory("6.1.37", "Date and Time")
def date_and_time(document: dict[str, Any]) -> Iterator[Issue]:
    for path, value in strings(select_all(document, _DATE_TIME_PATHS)):
        if _instant(value) is None:
            yield Issue(path, f"invalid date-time `{value}`")


def _after_newest_revision(
    document: Any, expressions: tuple[str, ...]
) -> Iterator[tuple[Path, str]]:
    """Values at ``expressions`` newer than the newest revision of a released
    document."""
    newest = _newest_revision(document)
    if newest is None or not _released(document):
        return
    for path, value in strings(select_all(document, expressions)):
        instant = _instant(value)
        if instant is not None and instant > newest:
            yield path, value


@mandatory("6.1.45", "Inconsistent Disclosure Date")
def inconsistent_disclosure_date(document: dict[str, Any]) -> Iterator[Issue]:
    if get(document, "document", "distribution", "tlp", "label") != "CLEAR":
        return
    for path, value in _after_newest_revision(
        document, ("$.vulnerabilities[*].disclosure_date",)
    ):
        yield Issue(path, f"disclosure date `{value}` is after the newest revision")


@mandatory("6.1.52", "Inconsistent First Known Exploitation Dates")
def inconsistent_exploitation_dates(document: dict[str, Any]) -> Iterator[Issue]:
    for path, value in _after_newest_revision(
        document,
        (
            "$.vulnerabilities[*].first_known_exploitation_dates[*].date",
            "$.vulnerabilities[*].first_known_exploitation_dates[*].exploitation_date",
        ),
    ):
        yield Issue(path, f"`{value}` is after the newest revision")


@mandatory("6.1.53", "Inconsistent Exploitation Date")
def inconsistent_exploitation_date(document: dict[str, Any]) -> Iterator[Issue]:
    for path, item in select(
        document, "$.vulnerabilities[*].first_known_exploitation_dates[*]"
    ):
        exploited = _instant(get(item, "exploitation_date"))
        date = _instant(get(item, "date"))
        if exploited is not None and date is not None and exploited > date:
            yield Issue(
                (*path, "exploitation_date"),
                "exploitation date is after the date of the item",
            )


# Some official examples fail this; see KNOWN_EXAMPLE_DEFECTS in
# tests/test_csaf_mandatory.py.
@mandatory("6.1.62", "Inconsistent Discovery Date")
def inconsistent_discovery_date(document: dict[str, Any]) -> Iterator[Issue]:
    for path, value in _after_newest_revision(
        document, ("$.vulnerabilities[*].discovery_date",)
    ):
        yield Issue(path, f"discovery date `{value}` is after the newest revision")

    for path, vulnerability in select(document, "$.vulnerabilities[*]"):
        discovered = _instant(get(vulnerability, "discovery_date"))
        disclosed = _instant(get(vulnerability, "disclosure_date"))
        if discovered is not None and disclosed is not None and discovered > disclosed:
            yield Issue(
                (*path, "discovery_date"), "discovery date is after the disclosure date"
            )


# Some official examples fail this; see KNOWN_EXAMPLE_DEFECTS in
# tests/test_csaf_mandatory.py.
@mandatory("6.1.66", "Non-Draft Initial Release Date")
def non_draft_initial_release_date(document: dict[str, Any]) -> Iterator[Issue]:
    if not _released(document):
        return
    for path, value in strings(
        select(document, "$.document.tracking.initial_release_date")
    ):
        initial = _instant(value)
        if initial is None:
            continue
        dates = {
            _instant(get(item, "date"))
            for _, item in select(document, "$.document.tracking.revision_history[*]")
            if get(item, "number") in ("1", "1.0.0")
        } - {None}
        if not dates:
            yield Issue(
                path,
                "date of the revision history item with number `1` or `1.0.0`"
                " cannot be determined",
            )
        elif initial not in dates:
            yield Issue(
                path,
                "initial release date differs from the date of the revision history"
                " item with number `1` or `1.0.0`",
            )
