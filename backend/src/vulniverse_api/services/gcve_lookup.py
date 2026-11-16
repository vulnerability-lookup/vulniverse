"""Looking up public GCVE and CVE records with the GCVE client (``gcve``,
an optional extra: ``pip install vulniverse-api[gcve]``).

The client finds a record where the GNA that allocated it publishes it
(its dump, then its pull API), else at an aggregator (CIRCL's
Vulnerability-Lookup, which also answers CVE IDs). It keeps the signed
GNA registry and the dumps in the instance folder.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from flask import current_app

from .csaf_convert import csaf_from_cve
from .cve_fields import cna as cna_of

REGISTRY_MAX_AGE_SECONDS = 24 * 60 * 60


class LookupUnavailable(RuntimeError):
    """The gcve extra isn't installed."""


def _base_path() -> Path:
    return Path(current_app.instance_path) / "gcve"


def _ensure_registry(base: Path) -> None:
    """Download the GNA registry when missing or a day old, and check its
    signature before it is used."""
    from gcve import registry

    path = base / registry.GCVE_PATH
    if path.exists() and time.time() - path.stat().st_mtime < REGISTRY_MAX_AGE_SECONDS:
        return

    # shortcut: two requests refreshing at the same moment both download;
    # fine at Vulniverse's load, add a lock if lookups become frequent.
    registry.update_registry_public_key(base)
    registry.update_registry_signature(base)
    registry.update_registry(base)
    path.touch()

    if not registry.verify_registry_integrity(base):
        path.unlink(missing_ok=True)
        raise RuntimeError("The GCVE registry's signature is invalid.")


def lookup_public_record(identifier: str) -> dict[str, Any] | None:
    """The public record of a GCVE or CVE ID, where it was found, and the
    same record as a CSAF vulnerability (for comparing with an advisory).
    None if no publication channel has it.

    Raises LookupUnavailable without the gcve extra, ValueError for an
    invalid ID, LookupError for a GNA missing from the registry and
    requests' exceptions when a source can't be reached.
    """
    try:
        from gcve.lookup import lookup_gcve
    except ImportError as error:
        raise LookupUnavailable from error

    base = _base_path()
    _ensure_registry(base)
    result = lookup_gcve(identifier, base)

    if result is None:
        return None

    vulnerabilities = csaf_from_cve(result.record).get("vulnerabilities") or [{}]

    # The conversion makes up a title from the description when the record
    # has none; comparing with it would report a difference that isn't one.
    if not cna_of(result.record).get("title"):
        vulnerabilities[0].pop("title", None)

    return {
        "record": result.record,
        "source": result.source,
        "url": result.url,
        "csaf": vulnerabilities[0],
    }
