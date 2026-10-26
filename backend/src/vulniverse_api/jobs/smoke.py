"""Trivial job to verify that Docker, Valkey, and RQ are connected."""


def echo(value: str) -> dict[str, str]:
    return {"echo": value}
