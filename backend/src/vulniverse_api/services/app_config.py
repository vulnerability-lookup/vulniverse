from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[4]
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "vulniverse.toml"
SAMPLE_CONFIG_PATH = CONFIG_DIR / "vulniverse.toml.sample"

# Every key an [integrations.<target>] table must define for that target to
# be considered configured. Missing any of these means "not configured" —
# not a startup error, since most deployments won't set every integration.
REQUIRED_INTEGRATION_KEYS = frozenset({
    "cve_url",
    "short_name",
    "cve_api_org",
    "cve_api_user",
    "cve_api_key",
})


@lru_cache(maxsize=1)
def load_app_config() -> dict[str, dict[str, Any]]:
    """Load config/vulniverse.toml, falling back to the committed
    .sample file (and then to empty tables) if it's absent, so a
    deployment with no config file behaves like an all-defaults one.
    Cached for the process lifetime; restart the backend to pick up
    edits, matching how compiled schema validators are cached.
    """
    path = CONFIG_PATH if CONFIG_PATH.exists() else SAMPLE_CONFIG_PATH

    if not path.exists():
        return {"panels": {}, "modules": {}, "integrations": {}}

    with path.open("rb") as handle:
        data: dict[str, Any] = tomllib.load(handle)

    return {
        "panels": dict(data.get("panels", {})),
        "modules": dict(data.get("modules", {})),
        "integrations": {
            target: dict(fields)
            for target, fields in data.get("integrations", {}).items()
        },
    }


def get_integration(target: str) -> dict[str, str] | None:
    """Credentials for one [integrations.<target>] table, or None if the
    target isn't configured (table absent, or missing a required key).
    Never exposed via /api/v1/capabilities — callers use this server-side
    only, e.g. to build outgoing request headers.
    """
    fields = load_app_config()["integrations"].get(target)

    if fields is None or not REQUIRED_INTEGRATION_KEYS.issubset(fields):
        return None

    return {key: str(fields[key]) for key in REQUIRED_INTEGRATION_KEYS}


def is_integration_configured(target: str) -> bool:
    return get_integration(target) is not None
