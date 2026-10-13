#!/usr/bin/env python3
"""
Update the upstream schemas used by Vulniverse.

1. Fetch the selected upstream Git revisions.
2. Verify that the selected schema files look like the expected formats.
3. Copy the official schema files into schemas/upstream/.
4. Update schemas/manifest.json.

Example:

    python scripts/update_schemas.py \
        --cve-ref v5.2.0 \
        --cve-version 5.2.0 \
        --gcve-ref main \
        --gcve-version 1.7

Older CVE versions may publish their bundled schema at another path:

    python scripts/update_schemas.py \
        --cve-ref v5.0.0 \
        --cve-version 5.0 \
        --cve-source-path schema/v5.0/docs/CVE_JSON_5.0_bundled.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

from helper.console import Console
from helper.errors import ScriptError
from helper.json import load_json_object, write_json


console = Console("vulniverse-schemas")


CVE_REPOSITORY = "https://github.com/CVEProject/cve-schema.git"

CVE_SCHEMA_SOURCE = Path("schema/docs/CVE_Record_Format_bundled.json")

CVE_OUTPUT_FILENAME = "CVE_Record_Format_bundled.json"


GCVE_REPOSITORY = "https://github.com/gcve-eu/bcp-validator.git"

GCVE_SCHEMA_SOURCE = Path("bcp-05/schema/gcve-bcp-05.schema.json")

GCVE_OUTPUT_FILENAME = "gcve-bcp-05.schema.json"


class UpdateError(ScriptError):
    """Updating upstream schemas failed."""


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    except FileNotFoundError as error:
        raise UpdateError(f"Required command was not found: {
                          command[0]!r}") from error

    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()

        stdout = (error.stdout or "").strip()

        details = stderr or stdout or f"exit status {error.returncode}"

        raise UpdateError(f"Command failed: {' '.join(command)}\n{
                          details}") from error

    return (result.stdout or "").strip()


def require_git() -> None:
    version = run(
        [
            "git",
            "--version",
        ]
    )

    console.info(f"Using {version}")


def fetch_repository(
    repository: str,
    ref: str,
    destination: Path,
) -> str:
    """
    Fetch one Git ref into a temporary checkout.

    Returns the resolved commit so it can be displayed to the user.
    The commit is deliberately not stored in the schema tree.
    """

    destination.mkdir(
        parents=True,
        exist_ok=False,
    )

    run(
        [
            "git",
            "init",
            "--quiet",
        ],
        cwd=destination,
    )

    run(
        [
            "git",
            "remote",
            "add",
            "origin",
            repository,
        ],
        cwd=destination,
    )

    console.info(f"Fetching {repository} at {ref!r}")

    run(
        [
            "git",
            "fetch",
            "--quiet",
            "--depth=1",
            "origin",
            ref,
        ],
        cwd=destination,
    )

    run(
        [
            "git",
            "checkout",
            "--quiet",
            "--detach",
            "FETCH_HEAD",
        ],
        cwd=destination,
    )

    return run(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=destination,
    )


def validate_cve_schema(
    schema: dict[str, Any],
    *,
    expected_version: str,
) -> None:
    schema_uri = schema.get("$schema")

    if (
        not isinstance(
            schema_uri,
            str,
        )
        or "draft-07" not in schema_uri
    ):
        raise UpdateError(
            "The selected CVE file does not look like the expected "
            "Draft-07 CVE Record Format schema."
        )

    title = schema.get("title")

    if title != "CVE JSON record format":
        raise UpdateError(f"Unexpected CVE schema title: {title!r}")

    definitions = schema.get("definitions")

    if not isinstance(
        definitions,
        dict,
    ):
        raise UpdateError("The CVE schema has no 'definitions' object.")

    data_version = definitions.get("dataVersion")

    if not isinstance(
        data_version,
        dict,
    ):
        raise UpdateError(
            "The CVE schema has no definitions.dataVersion object.")

    declared_version = data_version.get("default")

    # CVE 5.0 uses a single-value enum instead of default.
    if declared_version is None:
        enum_values = data_version.get("enum")

        if (
            isinstance(
                enum_values,
                list,
            )
            and len(enum_values) == 1
        ):
            declared_version = enum_values[0]

    if declared_version != expected_version:
        raise UpdateError(
            "CVE version mismatch: "
            f"--cve-version={expected_version!r}, "
            "but the selected schema declares "
            f"dataVersion={declared_version!r}."
        )


def validate_gcve_schema(
    schema: dict[str, Any],
) -> None:
    schema_id = schema.get("$id")

    if (
        not isinstance(
            schema_id,
            str,
        )
        or "gcve-bcp-05" not in schema_id
    ):
        raise UpdateError(f"Unexpected GCVE schema identifier: {schema_id!r}")

    serialized = json.dumps(
        schema,
        sort_keys=True,
    )

    for required_term in (
        "x_gcve",
        "vulnId",
        "recordType",
    ):
        if required_term not in serialized:
            raise UpdateError(
                f"The selected GCVE schema does not contain {required_term!r}."
            )


def ensure_safe_version_label(
    value: str,
    option: str,
) -> None:
    if not value or value in {
        ".",
        "..",
    }:
        raise UpdateError(f"Invalid {option} value: {value!r}")

    if any(
        character in value
        for character in (
            "/",
            "\\",
            "\0",
        )
    ):
        raise UpdateError(
            f"{option} must be a directory-safe version label: {value!r}")


def ensure_relative_source_path(
    value: str,
    option: str,
) -> None:
    path = Path(value)

    if path.is_absolute():
        raise UpdateError(f"{option} must be a relative path: {value!r}")

    if ".." in path.parts:
        raise UpdateError(f"{option} must not contain '..': {value!r}")


def copy_file_atomic(
    source: Path,
    destination: Path,
) -> None:
    """
    Copy a file without ever exposing a partially written destination.
    """

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = destination.with_name(
        f".{destination.name}.{uuid.uuid4().hex}.tmp")

    try:
        shutil.copyfile(
            source,
            temporary,
        )

        os.replace(
            temporary,
            destination,
        )

    finally:
        if temporary.exists():
            temporary.unlink()


def load_existing_manifest(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        return {
            "schemaManifestVersion": 2,
            "currentProfiles": {},
            "profiles": {},
        }

    manifest = load_json_object(path)

    profiles = manifest.get("profiles")

    if not isinstance(
        profiles,
        dict,
    ):
        raise UpdateError(
            f"Existing manifest has no valid 'profiles' object: {path}")

    current_profiles = manifest.get("currentProfiles")

    if current_profiles is None:
        manifest["currentProfiles"] = {}

    elif not isinstance(
        current_profiles,
        dict,
    ):
        raise UpdateError(
            f"Existing manifest has no valid 'currentProfiles' object: {path}"
        )

    return manifest


def update_cve_profile(
    profiles: dict[str, Any],
    *,
    profile_id: str,
    version: str,
    schema_path: Path,
) -> None:
    existing = profiles.get(
        profile_id,
        {},
    )

    if not isinstance(
        existing,
        dict,
    ):
        existing = {}

    profile: dict[str, Any] = {
        **existing,
        "kind": "cve",
        "label": existing.get(
            "label",
            f"CVE {version}",
        ),
        "version": version,
        "baseSchema": schema_path.as_posix(),
    }

    # Old manifests may still contain provenance metadata from the
    # previous updater. The new updater does not create SOURCE.json.
    profile.pop(
        "sourceMetadata",
        None,
    )

    profile.setdefault(
        "editor",
        {
            "layout": "editor/cve.layout.json",
            "variant": "Published",
            "autoAdditionalPropertiesFrom": "containers.cna",
        },
    )

    profile.setdefault(
        "validation",
        {
            "preferredRootBranch": {
                "keyword": "oneOf",
                "index": 0,
            },
        },
    )

    profile.setdefault(
        "identifier",
        {
            "strategy": "cve",
        },
    )

    profiles[profile_id] = profile


def update_gcve_profile(
    profiles: dict[str, Any],
    *,
    profile_id: str,
    version: str,
    base_profile_id: str,
    base_schema_path: Path,
    extension_schema_path: Path,
) -> None:
    existing = profiles.get(
        profile_id,
        {},
    )

    if not isinstance(
        existing,
        dict,
    ):
        existing = {}

    profile: dict[str, Any] = {
        **existing,
        "kind": "gcve",
        "label": existing.get(
            "label",
            f"GCVE-BCP-05 {version}",
        ),
        "bcp": "GCVE-BCP-05",
        "version": version,
        "baseProfile": base_profile_id,
        "baseSchema": base_schema_path.as_posix(),
        "extensionSchemas": [
            extension_schema_path.as_posix(),
        ],
        "semanticValidator": "gcve-bcp-05",
    }

    profile.pop(
        "sourceMetadata",
        None,
    )

    profile.setdefault(
        "schemaOverlay",
        {
            "path": (f"overlays/{profile_id}.json"),
            "applyTo": "rootOneOfBranches",
        },
    )

    profile.setdefault(
        "editor",
        {
            "layout": "editor/cve.layout.json",
            "layoutExtras": [
                "editor/gcve.layout-extra.json",
            ],
            "variant": "Published",
            "augmenters": [
                "gcve-extensions",
            ],
            "autoAdditionalPropertiesFrom": "containers.cna",
        },
    )

    profile.setdefault(
        "validation",
        {
            "preferredRootBranch": {
                "keyword": "oneOf",
                "index": 0,
            },
        },
    )

    profile.setdefault(
        "identifier",
        {
            "strategy": "gcve",
        },
    )

    profiles[profile_id] = profile


def update_manifest(
    *,
    schema_root: Path,
    cve_version: str,
    gcve_version: str,
    dry_run: bool,
) -> None:
    manifest_path = schema_root / "manifest.json"

    manifest = load_existing_manifest(manifest_path)

    manifest["schemaManifestVersion"] = 2

    # generatedAt belonged to the old provenance-oriented updater.
    manifest.pop(
        "generatedAt",
        None,
    )

    profiles = manifest["profiles"]

    if not isinstance(
        profiles,
        dict,
    ):
        raise UpdateError("manifest profiles must be an object.")

    cve_profile_id = f"cve-{cve_version}"

    gcve_profile_id = f"gcve-bcp-05-{gcve_version}"

    cve_schema_path = Path("upstream") / "cve" / \
        cve_version / CVE_OUTPUT_FILENAME

    gcve_schema_path = (
        Path("upstream") / "gcve" / "bcp-05" /
        gcve_version / GCVE_OUTPUT_FILENAME
    )

    update_cve_profile(
        profiles,
        profile_id=cve_profile_id,
        version=cve_version,
        schema_path=cve_schema_path,
    )

    update_gcve_profile(
        profiles,
        profile_id=gcve_profile_id,
        version=gcve_version,
        base_profile_id=cve_profile_id,
        base_schema_path=cve_schema_path,
        extension_schema_path=gcve_schema_path,
    )

    current_profiles = manifest.setdefault(
        "currentProfiles",
        {},
    )

    if not isinstance(
        current_profiles,
        dict,
    ):
        raise UpdateError("manifest currentProfiles must be an object.")

    # Only update profiles owned by this updater. A future CSAF,
    # OSV, etc. entry remains untouched.
    current_profiles["cve"] = cve_profile_id

    current_profiles["gcve"] = gcve_profile_id

    if dry_run:
        console.info(f"Dry run: would update {manifest_path}")
        return

    write_json(
        manifest_path,
        manifest,
        sort_keys=True,
    )


def parse_arguments() -> argparse.Namespace:
    project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Fetch the upstream CVE and GCVE schemas used by Vulniverse.")
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root,
        help=("Vulniverse repository root. Defaults to the parent of scripts/."),
    )

    parser.add_argument(
        "--cve-ref",
        default="v5.2.0",
        help=("CVEProject/cve-schema Git tag, branch, or commit."),
    )

    parser.add_argument(
        "--cve-version",
        default="5.2.0",
        help=("CVE Record Format version."),
    )

    parser.add_argument(
        "--cve-repository",
        default=CVE_REPOSITORY,
        help=("Override the CVE schema repository."),
    )

    parser.add_argument(
        "--cve-source-path",
        default=CVE_SCHEMA_SOURCE.as_posix(),
        help=("Path to the bundled CVE schema inside the repository."),
    )

    parser.add_argument(
        "--gcve-ref",
        default="main",
        help=("gcve-eu/bcp-validator Git tag, branch, or commit."),
    )

    parser.add_argument(
        "--gcve-version",
        default="1.7",
        help=("GCVE-BCP-05 version."),
    )

    parser.add_argument(
        "--gcve-repository",
        default=GCVE_REPOSITORY,
        help=("Override the GCVE validator repository."),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=("Fetch and validate schemas without modifying the repository."),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    ensure_safe_version_label(
        args.cve_version,
        "--cve-version",
    )

    ensure_safe_version_label(
        args.gcve_version,
        "--gcve-version",
    )

    ensure_relative_source_path(
        args.cve_source_path,
        "--cve-source-path",
    )

    project_root = args.project_root.expanduser().resolve()

    schema_root = project_root / "schemas"

    schema_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    cve_schema_source = Path(args.cve_source_path)

    require_git()

    if args.gcve_ref in {
        "main",
        "master",
    }:
        console.warning(
            "The GCVE source is being fetched from a moving branch. "
            "Use an exact commit for reproducible updates."
        )

    with tempfile.TemporaryDirectory(
        prefix="vulniverse-schema-update-"
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)

        cve_checkout = temporary_root / "cve-schema"

        gcve_checkout = temporary_root / "gcve-bcp-validator"

        cve_commit = fetch_repository(
            args.cve_repository,
            args.cve_ref,
            cve_checkout,
        )

        gcve_commit = fetch_repository(
            args.gcve_repository,
            args.gcve_ref,
            gcve_checkout,
        )

        cve_source = cve_checkout / cve_schema_source

        gcve_source = gcve_checkout / GCVE_SCHEMA_SOURCE

        cve_schema = load_json_object(cve_source)

        gcve_schema = load_json_object(gcve_source)

        validate_cve_schema(
            cve_schema,
            expected_version=args.cve_version,
        )

        validate_gcve_schema(gcve_schema)

        cve_destination = (
            schema_root / "upstream" / "cve" / args.cve_version / CVE_OUTPUT_FILENAME
        )

        gcve_destination = (
            schema_root
            / "upstream"
            / "gcve"
            / "bcp-05"
            / args.gcve_version
            / GCVE_OUTPUT_FILENAME
        )

        if args.dry_run:
            console.info(f"Dry run: would install {cve_destination}")

            console.info(f"Dry run: would install {gcve_destination}")

        else:
            copy_file_atomic(
                cve_source,
                cve_destination,
            )

            copy_file_atomic(
                gcve_source,
                gcve_destination,
            )

    update_manifest(
        schema_root=schema_root,
        cve_version=args.cve_version,
        gcve_version=args.gcve_version,
        dry_run=args.dry_run,
    )

    console.info("Schema update completed successfully.")

    console.info(f"CVE ref {args.cve_ref!r} resolved to {cve_commit}")

    console.info(f"GCVE ref {args.gcve_ref!r} resolved to {gcve_commit}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())

    except ScriptError as error:
        console.error(str(error))

        raise SystemExit(2)
