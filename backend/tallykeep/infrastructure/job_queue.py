"""Job queue — interface plus an RQ-backed (Redis Queue) implementation.

Spec module 01: long-running and out-of-band work runs through the job queue
(custodial provider API calls, blockchain scans, multi-step sweeps). The queue
adds scheduling, retries, timeouts, persistence, and rate-limit handling around
the underlying adapter calls.

For testing without a real Redis we provide an `InMemoryJobQueue` that runs jobs
synchronously on enqueue. Both backends share the same `JobQueue` interface.

Status mapping mirrors the domain `JobStatus` enum so the API can return job
state without per-backend translation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import UUID, uuid4

from tallykeep.domain.enums import JobStatus


@dataclass
class JobInfo:
    """Snapshot of a job's state.

    Domain `Job` (spec module 02) carries more fields (parameters, result,
    timestamps) and is what the API surfaces. JobInfo is the queue-level slice
    used by callers to poll status and fetch results.
    """

    id: UUID
    status: JobStatus
    job_type: str | None = None
    label: str | None = None
    result: Any = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobQueue(ABC):
    @abstractmethod
    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: int | None = None,
        job_type: str | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> UUID:
        """Schedule `func(*args, **kwargs)` and return a job id."""

    @abstractmethod
    def get(self, job_id: UUID) -> JobInfo:
        """Look up a job. Raises KeyError if the job is unknown."""

    @abstractmethod
    def list_recent(
        self,
        *,
        status: JobStatus | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[JobInfo]:
        """Return recent jobs, optionally filtered by status or job_type."""

    @abstractmethod
    def cancel(self, job_id: UUID) -> bool:
        """Cancel a queued or running job. Returns True if cancellation took effect."""

    @abstractmethod
    def close(self) -> None: ...


# --- in-memory ------------------------------------------------------------------


class InMemoryJobQueue(JobQueue):
    """Synchronous: every enqueue runs the function inline before returning.

    Suited to unit tests and to local development paths where backgrounding adds
    only complexity. The job's status reflects the outcome of the call.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: dict[UUID, JobInfo] = {}
        self._closed = False

    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: int | None = None,  # accepted for parity; ignored in-memory
        job_type: str | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> UUID:
        if self._closed:
            raise RuntimeError("InMemoryJobQueue is closed")

        job_id = uuid4()
        info = JobInfo(id=job_id, status=JobStatus.RUNNING, job_type=job_type, label=label)
        info.started_at = datetime.now(UTC)
        with self._lock:
            self._jobs[job_id] = info

        try:
            result = func(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — the queue catches everything
            info.error_message = repr(exc)
            info.status = JobStatus.FAILED
        else:
            info.result = result
            info.status = JobStatus.SUCCESS
        info.finished_at = datetime.now(UTC)
        return job_id

    def get(self, job_id: UUID) -> JobInfo:
        with self._lock:
            info = self._jobs.get(job_id)
        if info is None:
            raise KeyError(job_id)
        return info

    def list_recent(
        self,
        *,
        status: JobStatus | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[JobInfo]:
        with self._lock:
            jobs = list(self._jobs.values())
        if status is not None:
            jobs = [j for j in jobs if j.status == status]
        if job_type is not None:
            jobs = [j for j in jobs if j.job_type == job_type]
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]

    def cancel(self, job_id: UUID) -> bool:
        # In-memory jobs always run inline, so by the time `cancel` is called the
        # job has already terminated. Cancellation is therefore a no-op.
        return False

    def close(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._closed = True


# --- RQ-backed ------------------------------------------------------------------


# Mapping from RQ status strings to our domain JobStatus.
_RQ_STATUS_MAP = {
    "queued": JobStatus.QUEUED,
    "started": JobStatus.RUNNING,
    "deferred": JobStatus.QUEUED,  # waiting on a dependency
    "scheduled": JobStatus.QUEUED,
    "finished": JobStatus.SUCCESS,
    "failed": JobStatus.FAILED,
    "stopped": JobStatus.CANCELLED,
    "canceled": JobStatus.CANCELLED,  # rq spells it without the second 'l'
}


class RedisQueueJobQueue(JobQueue):
    """RQ (Redis Queue) backend.

    Wraps `rq.Queue` so callers see the JobQueue interface and can opt out of RQ
    entirely in tests. Job ids are UUIDs; we tell RQ to use those as job ids so
    no extra mapping table is needed.
    """

    def __init__(self, redis_url: str, queue_name: str = "tallykeep") -> None:
        import redis
        from rq import Queue

        self._redis = redis.Redis.from_url(redis_url, decode_responses=False)
        # Verify connectivity early so test fixtures fail loudly on misconfig.
        self._redis.ping()
        self._queue = Queue(name=queue_name, connection=self._redis)

    def enqueue(
        self,
        func: Callable[..., Any],
        *args: Any,
        timeout: int | None = None,
        job_type: str | None = None,
        label: str | None = None,
        **kwargs: Any,
    ) -> UUID:
        job_id = uuid4()
        meta = {}
        if job_type is not None:
            meta["job_type"] = job_type
        if label is not None:
            meta["label"] = label
        self._queue.enqueue_call(
            func=func,
            args=args,
            kwargs=kwargs,
            job_id=str(job_id),
            timeout=timeout,
            meta=meta if meta else None,
        )
        return job_id

    def get(self, job_id: UUID) -> JobInfo:
        from rq.exceptions import NoSuchJobError
        from rq.job import Job

        try:
            job = Job.fetch(str(job_id), connection=self._redis)
        except NoSuchJobError as exc:
            raise KeyError(job_id) from exc

        rq_status = job.get_status(refresh=True)
        status = _RQ_STATUS_MAP.get(rq_status, JobStatus.QUEUED)

        # rq>=1.16: prefer latest_result() over the deprecated job.result/exc_info.
        latest = job.latest_result() if status in {JobStatus.SUCCESS, JobStatus.FAILED} else None
        result_value: Any = None
        error_message: str | None = None
        if status == JobStatus.SUCCESS and latest is not None:
            result_value = latest.return_value
        elif status == JobStatus.FAILED and latest is not None:
            error_message = latest.exc_string

        meta = job.meta or {}
        info = JobInfo(
            id=job_id,
            status=status,
            job_type=meta.get("job_type"),
            label=meta.get("label"),
            result=result_value,
            error_message=error_message,
            created_at=job.created_at or datetime.now(UTC),
            started_at=job.started_at,
            finished_at=job.ended_at,
        )
        return info

    def list_recent(
        self,
        *,
        status: JobStatus | None = None,
        job_type: str | None = None,
        limit: int = 100,
    ) -> list[JobInfo]:
        from rq.job import Job
        from rq.registry import (
            FailedJobRegistry,
            FinishedJobRegistry,
            StartedJobRegistry,
        )

        job_ids: list[str] = []
        if status is None or status == JobStatus.QUEUED:
            job_ids += self._queue.job_ids
        if status is None or status == JobStatus.RUNNING:
            job_ids += StartedJobRegistry(queue=self._queue).get_job_ids()
        if status is None or status == JobStatus.SUCCESS:
            job_ids += FinishedJobRegistry(queue=self._queue).get_job_ids()
        if status is None or status == JobStatus.FAILED:
            job_ids += FailedJobRegistry(queue=self._queue).get_job_ids()

        jobs_raw = Job.fetch_many(job_ids, connection=self._redis)
        infos: list[JobInfo] = []
        for job in jobs_raw:
            if job is None:
                continue
            rq_status = job.get_status(refresh=False)
            jstatus = _RQ_STATUS_MAP.get(rq_status, JobStatus.QUEUED)
            meta = job.meta or {}
            jtype = meta.get("job_type")
            if job_type is not None and jtype != job_type:
                continue
            infos.append(JobInfo(
                id=UUID(job.id),
                status=jstatus,
                job_type=jtype,
                label=meta.get("label"),
                created_at=job.created_at or datetime.now(UTC),
                started_at=job.started_at,
                finished_at=job.ended_at,
            ))

        infos.sort(key=lambda j: j.created_at, reverse=True)
        return infos[:limit]

    def cancel(self, job_id: UUID) -> bool:
        from rq.exceptions import NoSuchJobError
        from rq.job import Job

        try:
            job = Job.fetch(str(job_id), connection=self._redis)
        except NoSuchJobError:
            return False
        # `cancel()` removes from the queue; `delete()` also clears history. We
        # only cancel — the audit trail in `job` table (M3+) keeps the record.
        try:
            job.cancel()
            return True
        except Exception:  # noqa: BLE001 — already-finished jobs raise here
            return False

    def close(self) -> None:
        self._redis.close()

    # --- diagnostics ---------------------------------------------------------

    def is_healthy(self) -> bool:
        try:
            return bool(self._redis.ping())
        except Exception:  # noqa: BLE001
            return False

    def queue_length(self) -> int:
        return len(self._queue)

    def drain_for_tests(self) -> int:
        """Run every queued job in the current process (test helper).

        Uses `rq.SimpleWorker` in burst mode so we don't need a separate worker
        process. Returns the number of jobs drained.
        """
        from rq import SimpleWorker

        worker = SimpleWorker([self._queue], connection=self._redis)
        worker.work(burst=True, with_scheduler=False)
        return self._queue.count


__all__ = [
    "InMemoryJobQueue",
    "JobInfo",
    "JobQueue",
    "RedisQueueJobQueue",
]
