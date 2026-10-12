from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Console:
    scope: str

    @property
    def prefix(self) -> str:
        return f"[{self.scope}]"

    def info(
        self,
        message: str,
    ) -> None:
        print(
            f"{self.prefix} {message}"
        )

    def warning(
        self,
        message: str,
    ) -> None:
        print(
            f"{self.prefix} WARNING: {message}",
            file=sys.stderr,
        )

    def error(
        self,
        message: str,
    ) -> None:
        print(
            f"{self.prefix} ERROR: {message}",
            file=sys.stderr,
        )
