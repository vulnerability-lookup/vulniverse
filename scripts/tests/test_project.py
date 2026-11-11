"""Run the scripts against this repository's own schemas."""

import shutil
from pathlib import Path

import pytest

from schematools import generate
from schematools.errors import GenerationError
from schematools.files import json_text, load_json_object
from schematools.sources import SOURCES
from schematools.update import update_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_generated_schemas_are_up_to_date() -> None:
    assert generate.main(["--project-root", str(PROJECT_ROOT), "--all", "--strict", "--check"]) == 0


def test_check_reports_a_stale_file(tmp_path: Path) -> None:
    shutil.copytree(PROJECT_ROOT / "schemas", tmp_path / "schemas")
    generated = PROJECT_ROOT / "frontend/src/generated"
    shutil.copytree(generated, tmp_path / "frontend/src/generated")
    stale = tmp_path / "frontend/src/generated/schemas/osv-1.9.2/ui.schema.json"
    stale.write_text("{}\n", encoding="utf-8")

    with pytest.raises(GenerationError, match="out of date"):
        generate.main(["--project-root", str(tmp_path), "--all", "--check"])


def test_manifest_profiles_are_reproduced_from_the_defaults(tmp_path: Path) -> None:
    manifest = PROJECT_ROOT / "schemas/manifest.json"
    shutil.copy(manifest, tmp_path / "manifest.json")

    update_manifest(tmp_path, {source.name: source.default_version for source in SOURCES}, False)

    assert (tmp_path / "manifest.json").read_text(encoding="utf-8") == json_text(
        load_json_object(manifest), sort_keys=True
    )
