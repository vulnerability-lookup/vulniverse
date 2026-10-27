from __future__ import annotations

from flask import Response
from flask_login import current_user
from redis.exceptions import RedisError
from rq.exceptions import NoSuchJobError
from rq.job import Job

from . import api_bp
from ..jobs.queue import get_redis, ALLOWED_QUEUES
from ..jobs.sse import stream_job_events


@api_bp.get("/jobs/<string:job_id>/events")
def job_events(job_id: str):
    """Stream status updates for an authorized background job."""

    connection = get_redis()

    try:
        job = Job.fetch(
            job_id,
            connection=connection,
        )

        # Refresh ownership metadata if necessary.
        job.get_meta(refresh=True)

    except NoSuchJobError:
        return {"message": "Job not found"}, 404

    except RedisError:
        return {"message": "Job service unavailable"}, 503

    # Verify that the job belongs to the authenticated user.
    if job.meta.get("owner_id") != str(current_user.get_id()):
        return {"message": "Job not found"}, 404

    # Only allow jobs from explicitly configured queues.
    if job.origin not in ALLOWED_QUEUES:
        return {"message": "Job not found"}, 404

    return Response(
        stream_job_events(connection, job.id),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
