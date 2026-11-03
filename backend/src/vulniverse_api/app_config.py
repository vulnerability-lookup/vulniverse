from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "vulniverse.toml"
SAMPLE_CONFIG_PATH = CONFIG_DIR / "vulniverse.toml.sample"

# cpeEntries defaults off because there is no local full-CPE catalog to
# serve it from yet (see services/cpe_catalog.py) — setting it to true
# in config wouldn't make /cpe/cpes work, so it stays off regardless.
DEFAULT_FEATURES: dict[str, bool] = {
    "cpeVendors": True,
    "cpeProducts": True,
    "cpeEntries": False,
    "cwe": True,
    "capec": True,
}


def _panel_enabled(value: Any) -> bool:
    """A panel entry is either the legacy plain bool ("id" = true/false)
    or a table ([panels.id] with an `enabled` key, possibly alongside
    other panel-specific config such as patch2vuln's executable/
    ollama_host/model/timeout_seconds). Only `enabled` is ever a
    capability the frontend needs — the rest is backend-internal
    config for whatever reads this panel's own table directly, and
    deliberately never reaches the /capabilities response.
    """
    if isinstance(value, dict):
        return bool(value.get("enabled", True))

    return bool(value)


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
        return {
            "server": {
                "mode": "local",
            },
            "panels": {},
            "actions": {},
            "features": dict(DEFAULT_FEATURES),
        }

    with path.open("rb") as handle:
        data: dict[str, Any] = tomllib.load(handle)

    return {
        "server": {
            "mode": data.get("server", {}).get("mode", "local"),
        },
        "features": {
            **DEFAULT_FEATURES,
            **{
                key: bool(value)
                for key, value in dict(data.get("features", {})).items()
                if key in DEFAULT_FEATURES
            },
        },
        "panels": {
            name: _panel_enabled(value)
            for name, value in dict(data.get("panels", {})).items()
        },
        "actions": dict(data.get("actions", {})),
    }
