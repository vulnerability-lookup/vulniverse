#!/usr/bin/env python3
"""
Update Vulniverse's vendored CVE and GCVE schemas.

The script:

1. Fetches explicitly selected Git refs from the official repositories.
2. Copies the official schema files without modifying them.
3. Verifies basic schema identity and the expected CVE format version.
4. Records the resolved commit, SHA-256 digest, retrieval time, and source path.
5. Copies upstream license/readme files when available.
6. Updates schemas/manifest.json while preserving older profiles.
7. Installs each version directory atomically.

Example:
    python scripts/update_schemas.py \
        --cve-ref v5.2.0 \
        --cve-version 5.2.0 \
        --gcve-ref main \
        --gcve-version 1.7

Older CVE format versions publish the bundled schema at a different
path than the current default (schema/docs/CVE_Record_Format_bundled.json)
— override it with --cve-source-path, e.g. for 5.0.x:
    python scripts/update_schemas.py \
        --cve-ref v5.0.0 \
        --cve-version 5.0.0 \
        --cve-source-path schema/v5.0/docs/CVE_JSON_5.0_bundled.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any


CVE_REPOSITORY = "https://github.com/CVEProject/cve-schema.git"
CVE_SCHEMA_SOURCE = Path("schema/docs/CVE_Record_Format_bundled.json")

GCVE_REPOSITORY = "https://github.com/gcve-eu/bcp-validator.git"
GCVE_SCHEMA_SOURCE = Path("bcp-05/schema/gcve-bcp-05.schema.json")

LICENSE_CANDIDATES = (
    Path("LICENSE"),
    Path("LICENSE.md"),
    Path("LICENSE.txt"),
    Path("COPYING"),
    Path("COPYING.md"),
)

README_CANDIDATES = (
    Path("README.md"),
    Path("bcp-05/README.md"),
)


class UpdateError(RuntimeError):
    """Raised when an upstream schema update cannot be completed safely."""


def log(message: str) -> None:
    print(f"[vulniverse-schemas] {message}")


def warn(message: str) -> None:
    print(f"[vulniverse-schemas] WARNING: {message}", file=sys.stderr)


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture_output else None,
            stderr=subprocess.PIPE if capture_output else None,
        )
    except FileNotFoundError as error:
        raise UpdateError(
            f"Required command was not found: {command[0]!r}"
        ) from error
    except subprocess.CalledProcessError as error:
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        details = stderr or stdout or f"exit status {error.returncode}"
        raise UpdateError(
            f"Command failed: {' '.join(command)}\n{details}"
        ) from error

    return (result.stdout or "").strip()


def require_git() -> None:
    version = run(["git", "--version"])
    log(f"Using {version}")


def fetch_repository(
    repository: str,
    ref: str,
    destination: Path,
) -> str:
    """
    Fetch one Git ref into a temporary repository and return the resolved commit.

    ``git fetch origin <ref>`` supports normal branches/tags and reachable commit
    hashes. The checkout is detached so no local branch metadata is required.
    """
    destination.mkdir(parents=True, exist_ok=False)

    run(["git", "init", "--quiet"], cwd=destination)
    run(["git", "remote", "add", "origin", repository], cwd=destination)

    log(f"Fetching {repository} at {ref!r}")
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
        ["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"],
        cwd=destination,
    )

    return run(["git", "rev-parse", "HEAD"], cwd=destination)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise UpdateError(f"Expected upstream file is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise UpdateError(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(value, dict):
        raise UpdateError(f"Schema must contain a JSON object: {path}")

    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_cve_schema(
    schema: dict[str, Any],
    *,
    expected_version: str,
) -> None:
    schema_uri = schema.get("$schema")

    if not isinstance(schema_uri, str) or "draft-07" not in schema_uri:
        raise UpdateError(
            "The selected CVE file does not look like the expected "
            "Draft-07 CVE Record Format schema."
        )

    title = schema.get("title")
    if title != "CVE JSON record format":
        raise UpdateError(f"Unexpected CVE schema title: {title!r}")

    definitions = schema.get("definitions")
    if not isinstance(definitions, dict):
        raise UpdateError("The CVE schema has no 'definitions' object.")

    data_version = definitions.get("dataVersion")
    if not isinstance(data_version, dict):
        raise UpdateError(
            "The CVE schema has no definitions.dataVersion object."
        )

    # Newer schemas (5.1.x, 5.2.x) declare their self-identifying
    # version as a "default"; 5.0.x instead pins it via a single-
    # value "enum" (e.g. ["5.0"]) with no "default" key at all.
    # Accept either so older versions vendor without loosening the
    # identity check.
    declared_version = data_version.get("default")

    if declared_version is None:
        enum_values = data_version.get("enum")

        if isinstance(enum_values, list) and len(enum_values) == 1:
            declared_version = enum_values[0]

    if declared_version != expected_version:
        raise UpdateError(
            "CVE version mismatch: "
            f"--cve-version={expected_version!r}, but the selected schema "
            f"declares dataVersion={declared_version!r}."
        )


def validate_gcve_schema(schema: dict[str, Any]) -> None:
    schema_id = schema.get("$id")
    if not isinstance(schema_id, str) or "gcve-bcp-05" not in schema_id:
        raise UpdateError(f"Unexpected GCVE schema identifier: {schema_id!r}")

    serialized = json.dumps(schema, sort_keys=True)
    for required_term in ("x_gcve", "vulnId", "recordType"):
        if required_term not in serialized:
            raise UpdateError(
                f"The selected GCVE schema does not contain {required_term!r}."
            )


def copy_supporting_files(
    checkout: Path,
    target: Path,
) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    seen_targets: set[str] = set()

    for candidate in (*LICENSE_CANDIDATES, *README_CANDIDATES):
        source = checkout / candidate
        if not source.is_file():
            continue

        normalized = "_".join(candidate.parts)
        target_name = f"UPSTREAM_{normalized}"

        if target_name in seen_targets:
            continue

        destination = target / target_name
        shutil.copy2(source, destination)
        seen_targets.add(target_name)

        copied.append(
            {
                "sourcePath": candidate.as_posix(),
                "vendoredPath": target_name,
                "sha256": sha256_file(destination),
            }
        )

    return copied


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def install_directory_atomically(
    staged_directory: Path,
    destination: Path,
) -> None:
    """Replace a version directory without leaving a partial installation."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    backup = destination.with_name(
        f".{destination.name}.backup-{uuid.uuid4().hex}"
    )

    had_existing = destination.exists()

    if had_existing:
        os.replace(destination, backup)

    try:
        os.replace(staged_directory, destination)
    except Exception:
        if had_existing and backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def stage_schema_version(
    *,
    checkout: Path,
    source_relative_path: Path,
    destination: Path,
    output_filename: str,
    source_metadata: dict[str, Any],
    dry_run: bool,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".{destination.name}.staging-",
        dir=destination.parent,
    ) as temporary_directory:
        staged = Path(temporary_directory)
        source = checkout / source_relative_path

        shutil.copy2(source, staged / output_filename)

        metadata = dict(source_metadata)
        metadata["sha256"] = sha256_file(staged / output_filename)
        metadata["supportingFiles"] = copy_supporting_files(checkout, staged)

        write_json(staged / "SOURCE.json", metadata)

        if dry_run:
            log(f"Dry run: would install {destination}")
            return

        # TemporaryDirectory owns `staged`, so first move it to a sibling path.
        movable_staged = destination.with_name(
            f".{destination.name}.new-{uuid.uuid4().hex}"
        )
        os.replace(staged, movable_staged)

        install_directory_atomically(movable_staged, destination)


def load_existing_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schemaManifestVersion": 1,
            "currentProfiles": {},
            "profiles": {},
        }

    manifest = load_json(path)

    if not isinstance(manifest.get("profiles"), dict):
        raise UpdateError(
            f"Existing manifest has no valid 'profiles' object: {path}"
        )

    manifest.setdefault("schemaManifestVersion", 1)
    manifest.setdefault("currentProfiles", {})

    return manifest


def update_manifest(
    *,
    schema_root: Path,
    cve_version: str,
    gcve_version: str,
    generated_at: str,
    dry_run: bool,
) -> None:
    manifest_path = schema_root / "manifest.json"
    manifest = load_existing_manifest(manifest_path)

    cve_profile = f"cve-{cve_version}"
    gcve_profile = f"gcve-bcp-05-{gcve_version}"

    cve_schema = (
        Path("upstream")
        / "cve"
        / cve_version
        / "CVE_Record_Format_bundled.json"
    )
    cve_source = cve_schema.parent / "SOURCE.json"

    gcve_schema = (
        Path("upstream")
        / "gcve"
        / "bcp-05"
        / gcve_version
        / "gcve-bcp-05.schema.json"
    )
    gcve_source = gcve_schema.parent / "SOURCE.json"

    profiles = manifest["profiles"]
    profiles[cve_profile] = {
        "kind": "cve",
        "version": cve_version,
        "baseSchema": cve_schema.as_posix(),
        "sourceMetadata": cve_source.as_posix(),
    }
    profiles[gcve_profile] = {
        "kind": "gcve",
        "bcp": "GCVE-BCP-05",
        "version": gcve_version,
        "baseProfile": cve_profile,
        "baseSchema": cve_schema.as_posix(),
        "extensionSchemas": [gcve_schema.as_posix()],
        "semanticValidator": "gcve-bcp-05",
        "sourceMetadata": gcve_source.as_posix(),
    }

    manifest["generatedAt"] = generated_at
    manifest["currentProfiles"] = {
        "cve": cve_profile,
        "gcve": gcve_profile,
    }

    if dry_run:
        log(f"Dry run: would update {manifest_path}")
        return

    write_json(manifest_path, manifest)


def parse_arguments() -> argparse.Namespace:
    default_project_root = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Fetch and vendor pinned CVE and GCVE schemas for Vulniverse."
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=default_project_root,
        help="Vulniverse repository root. Defaults to the parent of scripts/.",
    )

    parser.add_argument(
        "--cve-ref",
        default="v5.2.0",
        help="CVEProject/cve-schema Git tag, branch, or commit.",
    )
    parser.add_argument(
        "--cve-version",
        default="5.2.0",
        help=(
            "Version label used in the destination and manifest. "
            "Must match definitions.dataVersion.default."
        ),
    )
    parser.add_argument(
        "--cve-repository",
        default=CVE_REPOSITORY,
        help="Override the CVE schema Git repository.",
    )
    parser.add_argument(
        "--cve-source-path",
        default=CVE_SCHEMA_SOURCE.as_posix(),
        help=(
            "Path to the bundled CVE schema file within the checked-out "
            "repository, relative to its root. Older format versions use "
            "a different layout than the current default "
            f"({CVE_SCHEMA_SOURCE.as_posix()}) — e.g. 5.0.x publishes it at "
            "schema/v5.0/docs/CVE_JSON_5.0_bundled.json."
        ),
    )

    parser.add_argument(
        "--gcve-ref",
        default="main",
        help=(
            "gcve-eu/bcp-validator Git branch, tag, or commit. "
            "Use an exact commit for reproducible builds."
        ),
    )
    parser.add_argument(
        "--gcve-version",
        default="1.7",
        help=(
            "BCP-05 specification version label used in the destination "
            "and manifest."
        ),
    )
    parser.add_argument(
        "--gcve-repository",
        default=GCVE_REPOSITORY,
        help="Override the GCVE validator Git repository.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and verify sources without changing the repository.",
    )

    return parser.parse_args()


def ensure_safe_version_label(value: str, option: str) -> None:
    if not value or value in {".", ".."}:
        raise UpdateError(f"Invalid {option} value: {value!r}")

    if any(character in value for character in ("/", "\\", "\0")):
        raise UpdateError(
            f"{option} must be a directory-safe version label: {value!r}"
        )


def ensure_relative_source_path(value: str, option: str) -> None:
    path = Path(value)

    if path.is_absolute():
        raise UpdateError(f"{option} must be a relative path: {value!r}")

    if ".." in path.parts:
        raise UpdateError(f"{option} must not contain '..': {value!r}")


def main() -> int:
    args = parse_arguments()

    ensure_safe_version_label(args.cve_version, "--cve-version")
    ensure_safe_version_label(args.gcve_version, "--gcve-version")
    ensure_relative_source_path(args.cve_source_path, "--cve-source-path")

    cve_schema_source = Path(args.cve_source_path)

    project_root = args.project_root.expanduser().resolve()
    schema_root = project_root / "schemas"
    schema_root.mkdir(parents=True, exist_ok=True)

    require_git()

    if args.gcve_ref in {"main", "master"}:
        warn(
            "The GCVE source is being fetched from a moving branch. "
            "SOURCE.json will record the resolved commit; use that commit "
            "as --gcve-ref in reproducible CI builds."
        )

    retrieved_at = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
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

        cve_schema = load_json(cve_source)
        gcve_schema = load_json(gcve_source)

        validate_cve_schema(
            cve_schema,
            expected_version=args.cve_version,
        )
        validate_gcve_schema(gcve_schema)

        cve_destination = (
            schema_root / "upstream" / "cve" / args.cve_version
        )
        gcve_destination = (
            schema_root
            / "upstream"
            / "gcve"
            / "bcp-05"
            / args.gcve_version
        )

        stage_schema_version(
            checkout=cve_checkout,
            source_relative_path=cve_schema_source,
            destination=cve_destination,
            output_filename="CVE_Record_Format_bundled.json",
            source_metadata={
                "project": "CVEProject/cve-schema",
                "repository": args.cve_repository,
                "requestedRef": args.cve_ref,
                "resolvedCommit": cve_commit,
                "version": args.cve_version,
                "sourcePath": cve_schema_source.as_posix(),
                "retrievedAt": retrieved_at,
            },
            dry_run=args.dry_run,
        )

        stage_schema_version(
            checkout=gcve_checkout,
            source_relative_path=GCVE_SCHEMA_SOURCE,
            destination=gcve_destination,
            output_filename="gcve-bcp-05.schema.json",
            source_metadata={
                "project": "gcve-eu/bcp-validator",
                "repository": args.gcve_repository,
                "requestedRef": args.gcve_ref,
                "resolvedCommit": gcve_commit,
                "specification": "GCVE-BCP-05",
                "specificationVersion": args.gcve_version,
                "sourcePath": GCVE_SCHEMA_SOURCE.as_posix(),
                "retrievedAt": retrieved_at,
                "scope": (
                    "Validates the GCVE x_gcve extension and related BCP-05 "
                    "structure; full records must also be validated against "
                    "the selected CVE base schema."
                ),
            },
            dry_run=args.dry_run,
        )

    update_manifest(
        schema_root=schema_root,
        cve_version=args.cve_version,
        gcve_version=args.gcve_version,
        generated_at=retrieved_at,
        dry_run=args.dry_run,
    )

    log("Schema update completed successfully.")
    log(f"CVE ref {args.cve_ref!r} resolved to {cve_commit}")
    log(f"GCVE ref {args.gcve_ref!r} resolved to {gcve_commit}")

    if not args.dry_run:
        log(f"Updated schema tree: {schema_root}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except UpdateError as error:
        print(
            f"[vulniverse-schemas] ERROR: {error}",
            file=sys.stderr,
        )
        raise SystemExit(2)
