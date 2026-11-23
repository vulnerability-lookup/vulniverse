#!/usr/bin/env python3
"""Sets or checks Vulniverse's version everywhere it is recorded.

    python3 scripts/set_version.py 1.0.0-rc.1        # set it
    python3 scripts/set_version.py --check v1.0.0-rc.1   # fail if anything differs

The version is a semver string, optionally with a leading "v" (a git tag)
and an alpha/beta/rc pre-release ("1.0.0-rc.1"). The backend gets its
Python spelling ("1.0.0rc1"). The release workflow runs --check on every
version tag, so a tag can't be released with stale version numbers.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SEMVER = re.compile(r"^(\d+\.\d+\.\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
PYTHON_PRERELEASE = {"alpha": "a", "beta": "b", "rc": "rc"}


def parse(raw: str) -> str:
    version = raw.removeprefix("v")
    if not SEMVER.match(version):
        sys.exit(f"Not a version: {raw!r} (expected e.g. 1.0.0 or 1.0.0-rc.1)")
    return version


def python_version(version: str) -> str:
    """1.0.0-rc.1 -> 1.0.0rc1, 0.1.0-alpha.2 -> 0.1.0a2, 1.0.0 -> 1.0.0."""
    match = SEMVER.match(version)
    assert match
    release, kind, number = match.groups()
    return f"{release}{PYTHON_PRERELEASE[kind]}{number}" if kind else release


# Each place: (file, how to read the version, how to write it).
def _json_versions(path: Path, *keys: tuple[str, ...]):
    def read() -> list[str]:
        data = json.loads(path.read_text())
        return [_dig(data, key) for key in keys]

    def write(version: str) -> None:
        data = json.loads(path.read_text())
        for key in keys:
            _dig(data, key[:-1])[key[-1]] = version
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    return read, write


def _dig(data, key: tuple[str, ...]):
    for part in key:
        data = data[part]
    return data


def _toml_version(path: Path, pattern: str):
    # Regex, not a TOML writer: it keeps the file's formatting and comments.
    regex = re.compile(pattern, re.MULTILINE)

    def read() -> list[str]:
        found = regex.search(path.read_text())
        assert found, f"{path}: no version found"
        return [found.group(2)]

    def write(version: str) -> None:
        text, count = regex.subn(
            rf"\g<1>{python_version(version)}\g<3>", path.read_text(), count=1
        )
        assert count == 1, f"{path}: no version found"
        path.write_text(text)

    return read, write


PLACES = {
    "frontend/package.json": _json_versions(
        ROOT / "frontend/package.json", ("version",)
    ),
    "frontend/package-lock.json": _json_versions(
        ROOT / "frontend/package-lock.json", ("version",), ("packages", "", "version")
    ),
    "packages/editor/package.json": _json_versions(
        ROOT / "packages/editor/package.json", ("version",)
    ),
    "backend/pyproject.toml": _toml_version(
        ROOT / "backend/pyproject.toml", r'^(version = ")([^"]+)(")'
    ),
    "backend/uv.lock": _toml_version(
        ROOT / "backend/uv.lock", r'^(name = "vulniverse-api"\nversion = ")([^"]+)(")'
    ),
}


def main(argv: list[str]) -> None:
    assert python_version("1.0.0-rc.1") == "1.0.0rc1"
    assert python_version("0.1.0-alpha.2") == "0.1.0a2"
    assert python_version("2.3.4") == "2.3.4"

    check = argv[:1] == ["--check"]
    args = argv[1:] if check else argv
    if len(args) != 1:
        sys.exit(__doc__)
    version = parse(args[0])

    if check:
        wrong = []
        for name, (read, _) in PLACES.items():
            expected = (
                python_version(version) if name.startswith("backend/") else version
            )
            wrong += [
                f"  {name}: {found} (expected {expected})"
                for found in read()
                if found != expected
            ]
        if wrong:
            sys.exit(
                f"Version {version} isn't set everywhere:\n"
                + "\n".join(wrong)
                + f"\nRun: python3 scripts/set_version.py {version}"
            )
        print(f"Version {version} is set everywhere.")
        return

    for name, (_, write) in PLACES.items():
        write(version)
        print(f"{name}: {version}")


if __name__ == "__main__":
    main(sys.argv[1:])
