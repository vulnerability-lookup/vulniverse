from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .app_config import CONFIG_PATH, SAMPLE_CONFIG_PATH


@dataclass(frozen=True)
class Patch2VulnConfig:
    enabled: bool
    executable: str
    ollama_host: str
    model: str
    timeout_seconds: int


@lru_cache(maxsize=1)
def get_patch2vuln_config() -> Patch2VulnConfig:
    path = CONFIG_PATH if CONFIG_PATH.exists() else SAMPLE_CONFIG_PATH

    with path.open("rb") as file:
        config = tomllib.load(file)

    settings = config.get("panels", {}).get("patch2vuln", {})

    return Patch2VulnConfig(
        enabled=bool(settings.get("enabled", False)),
        executable=os.environ.get(
            "PATCH2VULN_EXECUTABLE",
            settings.get(
                "executable",
                "/opt/patch2vuln/patch2vuln.py",
            ),
        ),
        ollama_host=settings.get(
            "ollama_host",
            "http://localhost:11434",
        ),
        model=settings.get("model", "qwen3.8:27b"),
        timeout_seconds=int(settings.get("timeout_seconds", 300)),
    )


def run_patch2vuln(
    sources: list[str],
    patches: list[bytes],
    context: dict[str, str],
) -> dict[str, Any]:
    config = get_patch2vuln_config()

    if not config.enabled:
        raise RuntimeError("Patch2Vuln is disabled")

    with tempfile.TemporaryDirectory(prefix="patch2vuln-") as tmp:
        directory = Path(tmp)

        inputs = list(sources)

        # Write uploaded patches into the job's temporary directory.
        for index, content in enumerate(patches):
            path = directory / f"patch-{index}.patch"
            path.write_bytes(content)
            inputs.append(str(path))

        if not inputs:
            raise ValueError("No patch inputs provided")

        advisory_path = directory / "advisory.json"
        analysis_path = directory / "analysis.json"

        command = [
            sys.executable,
            config.executable,
            *inputs,
            "--ollama-host",
            config.ollama_host,
            "--model",
            config.model,
            "--no-tag-version-detection",
            "--analysis-output",
            str(analysis_path),
            "--max-download-bytes",
            "4194304",
            "-o",
            str(advisory_path),
        ]

        options = {
            "vendor": "--vendor",
            "product": "--product",
            "affectedVersion": "--affected-version",
            "fixedVersion": "--fixed-version",
            "versionType": "--version-type",
        }

        for key, flag in options.items():
            value = context.get(key)

            if value:
                command.extend([flag, value])

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Patch2Vuln analysis timed out") from exc

        if result.returncode != 0:
            raise RuntimeError(f"Patch2Vuln exited with code {result.returncode}")

        if not advisory_path.exists():
            raise RuntimeError("Patch2Vuln did not produce an advisory")

        record = json.loads(advisory_path.read_text(encoding="utf-8"))

        if (
            not isinstance(record, dict)
            or record.get("dataType") != "CVE_RECORD"
            or record.get("dataVersion") != "5.2"
            or not isinstance(record.get("containers"), dict)
            or not isinstance(record["containers"].get("cna"), dict)
        ):
            raise RuntimeError("Invalid Patch2Vuln record")

        analysis = None

        if analysis_path.exists():
            analysis = json.loads(analysis_path.read_text(encoding="utf-8"))

        return {
            "record": record,
            "analysis": analysis,
        }
