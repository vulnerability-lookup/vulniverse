from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import FormatChecker
from jsonschema.exceptions import ValidationError
from jsonschema.protocols import Validator
from jsonschema.validators import validator_for


PROJECT_ROOT = Path(__file__).parents[4]

CVE_SCHEMA_PATH = (
    PROJECT_ROOT
    / "schemas"
    / "upstream"
    / "cve"
    / "5.2.0"
    / "CVE_Record_Format_bundled.json"
)


@lru_cache(maxsize=4)
def get_cve_validator() -> Validator:
    with CVE_SCHEMA_PATH.open(encoding="utf-8") as schema_file:
        schema = json.load(schema_file)

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)

    return validator_class(
        schema,
        format_checker=FormatChecker(),
    )


def expand_composite_error(
    error: ValidationError,
) -> list[ValidationError]:
    """
    Replace a oneOf/anyOf failure with the specific errors from
    whichever candidate schema came closest to matching, instead
    of the single generic "is not valid under any of the given
    schemas" message that hides all of them.

    A branch that fails on the discriminator itself (e.g. CVE's
    cveMetadata.state enum picking between the published/rejected
    variants) failed for the trivial reason that the document
    wasn't attempting to satisfy that branch at all — such a
    branch can look "closest" by raw error count purely because it
    happens to be a smaller/more permissive schema, hiding the
    real errors from the branch the document actually matches.
    Branches without such a mismatch are preferred; only if every
    branch has one do we fall back to raw error count.
    """

    if not error.context:
        return [error]

    branches: dict[Any, list[ValidationError]] = {}

    for sub_error in error.context:
        branch_key = tuple(sub_error.absolute_schema_path)[:2]
        branches.setdefault(branch_key, []).append(sub_error)

    candidates = [
        branch_errors
        for branch_errors in branches.values()
        if not any(
            sub_error.validator in ("enum", "const")
            for sub_error in branch_errors
        )
    ] or list(branches.values())

    closest_branch = min(
        candidates,
        key=len,
    )

    expanded: list[ValidationError] = []

    for sub_error in closest_branch:
        expanded.extend(
            expand_composite_error(sub_error),
        )

    return expanded


def validate_record(
    record: dict[str, Any],
    profile: str,
) -> list[dict[str, Any]]:
    validator = get_cve_validator()

    validation_errors: list[ValidationError] = []

    for error in validator.iter_errors(record):
        validation_errors.extend(
            expand_composite_error(error),
        )

    validation_errors.sort(
        key=lambda error: list(error.absolute_path),
    )

    errors = [
        {
            "path": list(error.absolute_path),
            "schemaPath": list(error.absolute_schema_path),
            "message": error.message,
            "validator": error.validator,
        }
        for error in validation_errors
    ]

    if profile.startswith("gcve-"):
        errors.extend(validate_gcve_semantics(record))

    return errors


def validate_gcve_semantics(
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    # Add GCVE-specific checks incrementally.
    return []
