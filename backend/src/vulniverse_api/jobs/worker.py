from __future__ import annotations

from typing import Any

from rq import Worker
from rq.job import Job

from .events import publish_job_changed


class NotifyingWorker(Worker):
    """RQ worker that publishes job-state changes."""

    def _notify(self, job: Job) -> None:
        publish_job_changed(
            self.connection,
            job.id,
        )

    def prepare_job_execution(
        self,
        job: Job,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().prepare_job_execution(
            job,
            *args,
            **kwargs,
        )

        # RQ has persisted the STARTED status.
        self._notify(job)

    def handle_job_success(
        self,
        job: Job,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().handle_job_success(
            job,
            *args,
            **kwargs,
        )

        # RQ has persisted the successful result.
        self._notify(job)

    def handle_job_failure(
        self,
        job: Job,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().handle_job_failure(
            job,
            *args,
            **kwargs,
        )

        # RQ has persisted failure or retry state.
        self._notify(job)
