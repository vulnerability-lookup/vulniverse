from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parents[4]
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_PATH = CONFIG_DIR / "vulniverse.toml"
SAMPLE_CONFIG_PATH = CONFIG_DIR / "vulniverse.toml.sample"


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
        return {"panels": {}, "modules": {}}

    with path.open("rb") as handle:
        data: dict[str, Any] = tomllib.load(handle)

    return {
        "panels": dict(data.get("panels", {})),
        "modules": dict(data.get("modules", {})),
    }
