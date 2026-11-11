import subprocess
from pathlib import Path

from .console import Console
from .errors import UpdateError


def run(command: list[str], *, cwd: Path | None = None) -> str:
    """Run a command and return its output; failures raise UpdateError."""
    try:
        result = subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    except FileNotFoundError as error:
        raise UpdateError(f"Required command was not found: {command[0]!r}") from error
    except subprocess.CalledProcessError as error:
        details = (
            (error.stderr or "").strip()
            or (error.stdout or "").strip()
            or f"exit status {error.returncode}"
        )
        raise UpdateError(f"Command failed: {' '.join(command)}\n{details}") from error

    return (result.stdout or "").strip()


def require_git(console: Console) -> None:
    console.info(f"Using {run(['git', '--version'])}")


def fetch_repository(repository: str, ref: str, destination: Path, console: Console) -> str:
    """Fetch one Git ref (shallow) into ``destination`` and check it out.

    Returns the resolved commit, so it can be shown to the user. It is
    deliberately not stored in the schema tree.
    """
    destination.mkdir(parents=True, exist_ok=False)
    run(["git", "init", "--quiet"], cwd=destination)
    run(["git", "remote", "add", "origin", repository], cwd=destination)

    console.info(f"Fetching {repository} at {ref!r}")
    run(["git", "fetch", "--quiet", "--depth=1", "origin", ref], cwd=destination)
    run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination)

    return run(["git", "rev-parse", "HEAD"], cwd=destination)
