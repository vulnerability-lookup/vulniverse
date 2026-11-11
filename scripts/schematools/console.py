import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Console:
    """Prefixed output: information to stdout, problems to stderr."""

    scope: str

    def info(self, message: str) -> None:
        print(f"[{self.scope}] {message}")

    def warning(self, message: str) -> None:
        print(f"[{self.scope}] WARNING: {message}", file=sys.stderr)

    def error(self, message: str) -> None:
        print(f"[{self.scope}] ERROR: {message}", file=sys.stderr)
