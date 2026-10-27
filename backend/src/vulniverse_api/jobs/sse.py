from __future__ import annotations

import json
import time
from collections.abc import Iterator

from redis import Redis
from rq.exceptions import NoSuchJobError
from rq.job import Job

from .events import job_channel


TERMINAL_STATUSES = {"completed", "failed"}

STATUS_MAP = {
    "queued": "queued",
    "started": "running",
    "finished": "completed",
    "failed": "failed",
    "canceled": "failed",
    "stopped": "failed",
    "deferred": "queued",
    "scheduled": "queued",
    "rate_limited": "queued",
    "ready_to_enqueue": "queued",
}


def get_job_status(
    connection: Redis,
    job_id: str,
) -> str:
    """Retrieve the authoritative RQ job status."""

    try:
        job = Job.fetch(job_id, connection=connection)
    except NoSuchJobError:
        # The job may have expired while streaming.
        return "failed"

    status = job.get_status(refresh=True)

    # RQ may return a string-backed enum.
    value = getattr(status, "value", status)

    return STATUS_MAP.get(str(value), "queued")


def format_status_event(
    job_id: str,
    status: str,
) -> str:
    """Format a job status as an SSE message."""

    payload = json.dumps({
        "jobId": job_id,
        "status": status,
    })

    return f"event: status\ndata: {payload}\n\n"


def stream_job_events(
    connection: Redis,
    job_id: str,
) -> Iterator[str]:
    """Stream job updates from Valkey Pub/Sub."""

    channel = job_channel(job_id)

    with connection.pubsub(
        ignore_subscribe_messages=True,
    ) as pubsub:

        # Subscribe before reading the current job state.
        pubsub.subscribe(channel)

        # Reconnect after 3 seconds if disconnected.
        yield "retry: 3000\n\n"

        # Always send an initial status snapshot.
        status = get_job_status(connection, job_id)

        yield format_status_event(job_id, status)

        if status in TERMINAL_STATUSES:
            return

        last_status = status
        last_check = time.monotonic()

        while True:
            # Wait for a notification, at most 15 seconds.
            notification = pubsub.get_message(
                timeout=15.0,
            )

            now = time.monotonic()

            if notification is not None:
                # Something changed. Query RQ for the real state.
                status = get_job_status(connection, job_id)

                if status != last_status:
                    yield format_status_event(job_id, status)
                    last_status = status

                last_check = now

                if status in TERMINAL_STATUSES:
                    return

            elif now - last_check >= 60:
                # Fallback if a Pub/Sub message was missed.
                status = get_job_status(connection, job_id)

                if status != last_status:
                    yield format_status_event(job_id, status)
                    last_status = status

                last_check = now

                if status in TERMINAL_STATUSES:
                    return

            else:
                # SSE heartbeat to prevent idle connection timeouts.
                yield ": heartbeat\n\n"
