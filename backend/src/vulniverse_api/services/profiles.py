from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parents[4]
SCHEMAS_ROOT = PROJECT_ROOT / "schemas"
MANIFEST_PATH = SCHEMAS_ROOT / "manifest.json"


class UnknownProfileError(ValueError):
    """Raised when a profile is not declared in schemas/manifest.json."""


class ProfileConfigurationError(ValueError):
    """Raised when a declared profile has invalid configuration."""


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(
        encoding="utf-8",
    ) as manifest_file:
        manifest = json.load(
            manifest_file,
        )

    if not isinstance(manifest, dict):
        raise ProfileConfigurationError(
            "Schema manifest root must be an object."
        )

    profiles = manifest.get(
        "profiles",
    )

    if not isinstance(
        profiles,
        dict,
    ):
        raise ProfileConfigurationError(
            "Schema manifest has no valid 'profiles' object."
        )

    return manifest


def resolve_profile(
    profile_id: str,
) -> dict[str, Any]:
    profiles = load_manifest()[
        "profiles"
    ]

    profile = profiles.get(
        profile_id,
    )

    if not isinstance(
        profile,
        dict,
    ):
        raise UnknownProfileError(
            profile_id
        )

    return profile


def known_profiles() -> set[str]:
    profiles = load_manifest()[
        "profiles"
    ]

    return set(
        profiles
    )
