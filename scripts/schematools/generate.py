"""Generate the editor's schemas from schemas/manifest.json.

For each profile it writes ``frontend/src/generated/schemas/<profile>/``:

- ``authoring.schema.json``: the schema the editor validates and renders
  with (see :mod:`schematools.authoring`),
- ``ui.schema.json``: the JSON Forms layout (see :mod:`schematools.layout`),
- ``field-paths.json``: the scalar fields, for Templates path autocomplete
  (see :mod:`schematools.catalog`),

plus ``frontend/src/generated/gcve/extension-schemas.json`` when a profile
uses the ``gcve-extensions`` augmenter.

``--check`` writes nothing and fails when a generated file on disk differs
from what would be generated, so CI catches a forgotten regeneration.
"""

import argparse
from pathlib import Path
from typing import Any

from . import gcve
from .authoring import augmenter_ids, create_authoring_schema
from .catalog import frontend_path_catalog
from .console import Console
from .errors import GenerationError, ScriptError
from .files import json_text, write_json
from .jsontypes import JsonObject, require_dict, require_str
from .layout import build_ui_schema, load_editor_layout
from .manifest import load_manifest, manifest_path, resolve_profile

console = Console("vulniverse-schema-generator")

PROJECT_ROOT = Path(__file__).resolve().parents[2]

GENERATED_SCHEMAS = Path("frontend/src/generated/schemas")

# {path relative to the project root: JSON value}
Outputs = dict[Path, Any]


def generate_profile(
    project_root: Path, manifest: JsonObject, profile_id: str
) -> tuple[Outputs, list[str]]:
    """The files of one profile, and the layout paths missing from its schema."""
    schemas_root = project_root / "schemas"
    profile = resolve_profile(manifest, profile_id, GenerationError)
    editor_config = require_dict(
        profile.get("editor"), f"{profile_id} editor configuration", GenerationError
    )

    authoring_schema = create_authoring_schema(profile_id, profile, schemas_root)
    ui_schema, missing_paths = build_ui_schema(
        authoring_schema, load_editor_layout(schemas_root, editor_config), editor_config
    )

    directory = GENERATED_SCHEMAS / profile_id
    outputs: Outputs = {
        directory / "authoring.schema.json": authoring_schema,
        directory / "ui.schema.json": ui_schema,
        directory / "field-paths.json": frontend_path_catalog(authoring_schema),
    }

    if "gcve-extensions" in augmenter_ids(editor_config):
        outputs[gcve.FRONTEND_BUNDLE] = gcve.load_extension_schemas(schemas_root)

    return outputs, missing_paths


def report_missing(profile_id: str, missing_paths: list[str], strict: bool) -> None:
    if not missing_paths:
        return

    console.warning(f"Configured layout paths were not present in {profile_id}:")
    for path in sorted(set(missing_paths)):
        console.warning(f"  - {path}")

    if strict:
        raise GenerationError("Schema generation found missing paths.")


def stale_files(project_root: Path, outputs: Outputs) -> list[Path]:
    """The outputs whose file on disk is missing or differs."""
    stale = []

    for relative, value in outputs.items():
        path = project_root / relative
        if not path.exists() or path.read_text(encoding="utf-8") != json_text(value):
            stale.append(relative)

    return stale


def selected_profiles(args: argparse.Namespace, manifest: JsonObject) -> list[str]:
    if args.all:
        # Older profiles stay in the manifest for backend validation only.
        return sorted(set(manifest["currentProfiles"].values()))

    if args.profile:
        return [args.profile]

    return [
        require_str(
            manifest["currentProfiles"].get("cve"),
            "currentProfiles.cve",
            GenerationError,
        )
    ]


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Vulniverse editor schemas from a configured schema profile."
    )
    parser.add_argument(
        "--project-root", type=Path, default=PROJECT_ROOT, help="Vulniverse repository root."
    )
    which = parser.add_mutually_exclusive_group()
    which.add_argument(
        "--profile",
        default=None,
        help="Profile ID from schemas/manifest.json. Defaults to currentProfiles.cve.",
    )
    which.add_argument(
        "--all",
        action="store_true",
        help="Generate the current profile of every format (currentProfiles).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if configured layout paths do not exist in the schema.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write nothing; fail if a generated file is out of date.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    project_root = args.project_root.expanduser().resolve()
    manifest = load_manifest(manifest_path(project_root / "schemas"), GenerationError)
    stale: list[Path] = []

    for profile_id in selected_profiles(args, manifest):
        outputs, missing_paths = generate_profile(project_root, manifest, profile_id)

        if args.check:
            stale.extend(stale_files(project_root, outputs))
        else:
            for relative, value in outputs.items():
                write_json(project_root / relative, value)
            console.info(f"Generated editor schema for {profile_id}.")

        report_missing(profile_id, missing_paths, args.strict)

    if stale:
        for relative in sorted(set(stale)):
            console.error(f"Out of date: {relative}")
        raise GenerationError(
            "Generated schemas are out of date; run scripts/generate_editor_schemas.py --all."
        )

    return 0


def run() -> None:
    """Entry point of scripts/generate_editor_schemas.py."""
    try:
        raise SystemExit(main())
    except ScriptError as error:
        console.error(str(error))
        raise SystemExit(2) from None
