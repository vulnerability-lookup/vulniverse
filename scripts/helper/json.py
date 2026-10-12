from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

from .errors import ScriptError


class JsonFileError(ScriptError):
    """A JSON file could not be processed."""


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

    except FileNotFoundError as error:
        raise JsonFileError(
            f"File does not exist: {path}"
        ) from error

    except json.JSONDecodeError as error:
        raise JsonFileError(
            f"Invalid JSON in {path}: {error}"
        ) from error

    if not isinstance(
        value,
        dict,
    ):
        raise JsonFileError(
            f"Expected a JSON object in {path}"
        )

    return value


def write_json(
    path: Path,
    value: Any,
    *,
    sort_keys: bool = False,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(
        f".{path.name}.{uuid.uuid4().hex}.tmp"
    )

    temporary.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=sort_keys,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    os.replace(
        temporary,
        path,
    )
