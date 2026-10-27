from __future__ import annotations

import logging

from redis import Redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "vulniverse:jobs"


def job_channel(job_id: str) -> str:
    """Return the Pub/Sub channel for a job."""
    return f"{CHANNEL_PREFIX}:{job_id}"


def publish_job_changed(
    connection: Redis,
    job_id: str,
) -> None:
    """Notify listeners that an RQ job changed state."""

    try:
        connection.publish(
            job_channel(job_id),
            "changed",
        )
    except Exception:
        # Notifications must not affect job execution.
        logger.exception(
            "Failed to publish event for job %s",
            job_id,
        )
