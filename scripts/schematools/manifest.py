"""schemas/manifest.json: the profiles Vulniverse knows about.

Each profile describes one record format version (``cve-5.2.0``,
``osv-1.9.2``, ...): where its schema lives, how the backend validates it and
how the editor lays it out. ``currentProfiles`` names the newest profile of
each format.
"""

from pathlib import Path

from .errors import ScriptError
from .files import load_json_object
from .jsontypes import JsonObject, require_dict

MANIFEST_VERSION = 2


def manifest_path(schemas_root: Path) -> Path:
    return schemas_root / "manifest.json"


def load_manifest(path: Path, error: type[ScriptError] = ScriptError) -> JsonObject:
    """The manifest, with ``profiles`` and ``currentProfiles`` checked. A
    missing file yields an empty manifest, so a fresh checkout can start one."""
    if not path.exists():
        return {"schemaManifestVersion": MANIFEST_VERSION, "currentProfiles": {}, "profiles": {}}

    manifest = load_json_object(path)
    require_dict(manifest.get("profiles"), f"'profiles' in {path}", error)
    manifest["currentProfiles"] = require_dict(
        manifest.get("currentProfiles", {}), f"'currentProfiles' in {path}", error
    )

    return manifest


def resolve_profile(manifest: JsonObject, profile_id: str, error: type[ScriptError]) -> JsonObject:
    profile = manifest["profiles"].get(profile_id)

    if not isinstance(profile, dict):
        raise error(f"Unknown schema profile: {profile_id}")

    return profile
