"""Typed access to values read from JSON configuration.

The manifest and layout files are plain JSON, so every value has to be
checked before use. These helpers do that check once, with a clear error,
instead of an ``isinstance`` block at every use.
"""

from typing import Any

from .errors import ScriptError

JsonObject = dict[str, Any]


def require_str(value: Any, what: str, error: type[ScriptError] = ScriptError) -> str:
    if not isinstance(value, str):
        raise error(f"{what} must be a string.")
    return value


def require_dict(value: Any, what: str, error: type[ScriptError] = ScriptError) -> JsonObject:
    if not isinstance(value, dict):
        raise error(f"{what} must be an object.")
    return value


def require_list(value: Any, what: str, error: type[ScriptError] = ScriptError) -> list[Any]:
    if not isinstance(value, list):
        raise error(f"{what} must be an array.")
    return value


def str_list(value: Any, what: str, error: type[ScriptError] = ScriptError) -> list[str]:
    """An array whose items must all be strings."""
    items = require_list(value, what, error)

    for item in items:
        require_str(item, f"Each entry of {what}", error)

    return items


def as_dict(value: Any) -> JsonObject:
    """The value if it is an object, otherwise an empty one."""
    return value if isinstance(value, dict) else {}
