"""CSAF 2.1 mandatory tests (spec section 6.1): the rules a valid CSAF
document must pass beyond its JSON schema.

Each module registers its tests with :func:`core.mandatory`; importing
them here fills :data:`core.REGISTRY`. :func:`validate_csaf_mandatory` is
the profile's semantic validator (``semanticValidator: "csaf-2.1"`` in
schemas/manifest.json), so its errors block publication like schema errors
and show on Validate for drafts.

The official test documents in tests/fixtures/csaf/mandatory check every
registered test (tests/test_csaf_mandatory.py).
"""

from __future__ import annotations

import logging
from typing import Any

# Importing the test modules registers their tests.
from . import (  # noqa: F401
    involvement,
    metadata,
    product_tree,
    products,
    profiles,
    scores,
    status,
    tracking,
)
from .core import REGISTRY, pointer

logger = logging.getLogger(__name__)

VALIDATOR_ID = "csaf-2.1"


def validate_csaf_mandatory(
    document: dict[str, Any], _profile_id: str
) -> list[dict[str, Any]]:
    """Every registered test's issues, shaped like the schema errors."""
    errors: list[dict[str, Any]] = []

    for test in REGISTRY.values():
        try:
            issues = list(test.run(document))
        except Exception:
            # A bug in one test must not hide the others or fail the request;
            # it still shows, so the document isn't silently passed.
            logger.exception("CSAF mandatory test %s failed on a document", test.id)
            errors.append(
                {
                    "path": [],
                    "schemaPath": [],
                    "message": f"{test.id} {test.title}: the test could not be run.",
                    "validator": VALIDATOR_ID,
                    "severity": "warning",
                    "test": test.id,
                }
            )
            continue

        errors.extend(
            {
                "path": list(issue.path),
                "schemaPath": [],
                "message": f"{test.id} {test.title}: {issue.message}",
                "validator": VALIDATOR_ID,
                "severity": issue.severity,
                "test": test.id,
                "pointer": pointer(issue.path),
            }
            for issue in issues
        )

    return errors
