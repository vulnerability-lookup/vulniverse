"""Update the upstream schemas used by Vulniverse.

For every source in :data:`schematools.sources.SOURCES`:

1. fetch the selected Git ref of its repository,
2. check that the main schema file looks like the expected format,
3. copy its files into ``schemas/upstream/``,

then write every profile into ``schemas/manifest.json``.

Example::

    python scripts/update_schemas.py \\
        --cve-ref v5.2.0 --cve-version 5.2.0 \\
        --gcve-ref main --gcve-version 1.7 \\
        --osv-ref v1.9.2 --osv-version 1.9.2 \\
        --csaf-ref csaf-2.1-cs-01-20261109-rc1 --csaf-version 2.1

Older CVE versions may publish their bundled schema at another path::

    python scripts/update_schemas.py \\
        --cve-ref v5.0.0 --cve-version 5.0 \\
        --cve-source-path schema/v5.0/docs/CVE_JSON_5.0_bundled.json
"""

import argparse
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .console import Console
from .errors import ScriptError, UpdateError
from .files import copy_file_atomic, load_json_object, write_json
from .git import fetch_repository, require_git
from .manifest import MANIFEST_VERSION, load_manifest, manifest_path
from .sources import CVE_SCHEMA_SOURCE, SOURCES, SchemaSource, update_profiles

console = Console("vulniverse-schemas")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MOVING_BRANCHES = {"main", "master"}


@dataclass(frozen=True)
class Selection:
    """What the command line selected for one source."""

    source: SchemaSource
    repository: str
    ref: str
    version: str
    # {path in the repository: path below schemas/}
    files: dict[Path, Path]


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch the upstream CVE, GCVE, OSV and CSAF schemas used by Vulniverse."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Vulniverse repository root. Defaults to the parent of scripts/.",
    )

    for source in SOURCES:
        parser.add_argument(
            f"--{source.name}-ref",
            default=source.default_ref,
            help=f"{source.title} Git tag, branch, or commit.",
        )
        parser.add_argument(
            f"--{source.name}-version", default=source.default_version, help=source.version_help
        )
        parser.add_argument(
            f"--{source.name}-repository",
            default=source.repository,
            help=f"Override the {source.title} repository.",
        )
        if source.main_file_option:
            parser.add_argument(
                f"--{source.name}-source-path",
                default=CVE_SCHEMA_SOURCE.as_posix(),
                help="Path to the bundled CVE schema inside the repository.",
            )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and validate schemas without modifying the repository.",
    )
    return parser.parse_args(argv)


def ensure_safe_version_label(value: str, option: str) -> None:
    """The version becomes a directory name below schemas/upstream/."""
    if not value or value in {".", ".."}:
        raise UpdateError(f"Invalid {option} value: {value!r}")

    if any(character in value for character in ("/", "\\", "\0")):
        raise UpdateError(f"{option} must be a directory-safe version label: {value!r}")


def ensure_relative_source_path(value: str, option: str) -> Path:
    path = Path(value)

    if path.is_absolute():
        raise UpdateError(f"{option} must be a relative path: {value!r}")

    if ".." in path.parts:
        raise UpdateError(f"{option} must not contain '..': {value!r}")

    return path


def select(args: argparse.Namespace, source: SchemaSource) -> Selection:
    """Read and check the options of one source."""
    option = f"--{source.name}-version"
    version = getattr(args, f"{source.name}_version")
    ensure_safe_version_label(version, option)
    files = source.files(version)

    if source.main_file_option:
        # Swap the repository path of the main file, keep where it goes.
        main_source = ensure_relative_source_path(
            getattr(args, f"{source.name}_source_path"), f"--{source.name}-source-path"
        )
        _, destination = source.main_file(version)
        files = {main_source: destination}

    return Selection(
        source=source,
        repository=getattr(args, f"{source.name}_repository"),
        ref=getattr(args, f"{source.name}_ref"),
        version=version,
        files=files,
    )


def check(selection: Selection, checkout: Path) -> None:
    main_file = next(iter(selection.files))
    selection.source.check(load_json_object(checkout / main_file), selection.version)


def install(selection: Selection, checkout: Path, schemas_root: Path, dry_run: bool) -> None:
    for repository_path, destination in selection.files.items():
        if dry_run:
            console.info(f"Dry run: would install {schemas_root / destination}")
        else:
            copy_file_atomic(checkout / repository_path, schemas_root / destination)


def update_manifest(schemas_root: Path, versions: dict[str, str], dry_run: bool) -> None:
    path = manifest_path(schemas_root)
    manifest = load_manifest(path, UpdateError)
    manifest["schemaManifestVersion"] = MANIFEST_VERSION
    # generatedAt belonged to the previous, provenance-oriented updater.
    manifest.pop("generatedAt", None)

    update_profiles(manifest, versions)

    if dry_run:
        console.info(f"Dry run: would update {path}")
        return

    write_json(path, manifest, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    selections = [select(args, source) for source in SOURCES]

    schemas_root = args.project_root.expanduser().resolve() / "schemas"
    schemas_root.mkdir(parents=True, exist_ok=True)

    require_git(console)

    for selection in selections:
        if selection.ref in MOVING_BRANCHES:
            console.warning(
                f"The {selection.source.name.upper()} source is being fetched from a moving "
                "branch. Use an exact commit for reproducible updates."
            )

    commits = {}

    with tempfile.TemporaryDirectory(prefix="vulniverse-schema-update-") as temporary:
        for selection in selections:
            checkout = Path(temporary) / selection.source.name
            commits[selection.source.name] = fetch_repository(
                selection.repository, selection.ref, checkout, console
            )
            check(selection, checkout)

        # Only copy once every source passed its check.
        for selection in selections:
            checkout = Path(temporary) / selection.source.name
            install(selection, checkout, schemas_root, args.dry_run)

    update_manifest(
        schemas_root,
        {selection.source.name: selection.version for selection in selections},
        args.dry_run,
    )

    console.info("Schema update completed successfully.")
    for selection in selections:
        console.info(
            f"{selection.source.name.upper()} ref {selection.ref!r} resolved to "
            f"{commits[selection.source.name]}"
        )

    return 0


def run() -> None:
    """Entry point of scripts/update_schemas.py."""
    try:
        raise SystemExit(main())
    except ScriptError as error:
        console.error(str(error))
        raise SystemExit(2) from None
