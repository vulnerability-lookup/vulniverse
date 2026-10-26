"""Small shared entry point for submitting RQ tasks from Flask."""

from __future__ import annotations

import os
from functools import lru_cache

from redis import Redis
from rq import Queue

ALLOWED_QUEUES = frozenset({"patch2vuln"})


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    url = os.environ.get("REDIS_URL")
    if not url:
        raise RuntimeError("REDIS_URL must be configured for background jobs")
    return Redis.from_url(url)


def get_queue(name: str) -> Queue:
    if name not in ALLOWED_QUEUES:
        raise ValueError(f"Unknown job queue: {name}")
    return Queue(name, connection=get_redis(), default_timeout=1800)
