import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from .errors import ScriptError
from .jsontypes import JsonObject


def load_json_object(path: Path) -> JsonObject:
    """Read a JSON file that must contain an object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ScriptError(f"File does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ScriptError(f"Invalid JSON in {path}: {error}") from error

    if not isinstance(value, dict):
        raise ScriptError(f"Expected a JSON object in {path}")

    return value


def json_text(value: Any, *, sort_keys: bool = False) -> str:
    """The exact text every generated JSON file is written with."""
    return json.dumps(value, indent=2, sort_keys=sort_keys, ensure_ascii=False) + "\n"


def write_json(path: Path, value: Any, *, sort_keys: bool = False) -> None:
    """Write JSON atomically: readers never see a half-written file."""
    _replace_atomically(
        path,
        lambda temporary: temporary.write_text(
            json_text(value, sort_keys=sort_keys), encoding="utf-8"
        ),
    )


def copy_file_atomic(source: Path, destination: Path) -> None:
    """Copy a file without ever exposing a partially written destination."""
    _replace_atomically(destination, lambda temporary: shutil.copyfile(source, temporary))


def _replace_atomically(path: Path, write: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")

    try:
        write(temporary)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
