"""InMemoryJobQueue unit tests.

The Redis-backed implementation is exercised in the integration suite. The
in-memory backend runs jobs synchronously on enqueue, so its tests are about
status transitions and result/error propagation rather than queueing semantics.
"""

from __future__ import annotations

import pytest

from tallykeep.domain.enums import JobStatus
from tallykeep.infrastructure.job_queue import InMemoryJobQueue, JobInfo


pytestmark = pytest.mark.unit


def _add(a: int, b: int) -> int:
    return a + b


def _explode() -> None:
    raise RuntimeError("intentional")


@pytest.fixture()
def queue() -> InMemoryJobQueue:
    return InMemoryJobQueue()


class TestEnqueue:
    def test_returns_job_id(self, queue: InMemoryJobQueue) -> None:
        job_id = queue.enqueue(_add, 1, 2)
        assert job_id is not None
        info = queue.get(job_id)
        assert isinstance(info, JobInfo)

    def test_job_runs_synchronously_and_records_result(
        self, queue: InMemoryJobQueue
    ) -> None:
        job_id = queue.enqueue(_add, 2, 3)
        info = queue.get(job_id)
        assert info.status == JobStatus.SUCCESS
        assert info.result == 5
        assert info.error_message is None

    def test_failing_job_records_error(self, queue: InMemoryJobQueue) -> None:
        job_id = queue.enqueue(_explode)
        info = queue.get(job_id)
        assert info.status == JobStatus.FAILED
        assert info.error_message is not None
        assert "intentional" in info.error_message

    def test_started_at_and_finished_at_are_set(
        self, queue: InMemoryJobQueue
    ) -> None:
        job_id = queue.enqueue(_add, 1, 1)
        info = queue.get(job_id)
        assert info.started_at is not None
        assert info.finished_at is not None
        assert info.finished_at >= info.started_at

    def test_kwargs_passed_through(self, queue: InMemoryJobQueue) -> None:
        def kw_func(a: int, *, b: int) -> int:
            return a * b

        job_id = queue.enqueue(kw_func, 4, b=5)
        assert queue.get(job_id).result == 20

    def test_enqueue_after_close_rejected(
        self, queue: InMemoryJobQueue
    ) -> None:
        queue.close()
        with pytest.raises(RuntimeError, match="closed"):
            queue.enqueue(_add, 1, 1)


class TestGet:
    def test_unknown_job_raises_keyerror(self, queue: InMemoryJobQueue) -> None:
        from uuid import uuid4

        with pytest.raises(KeyError):
            queue.get(uuid4())


class TestCancel:
    def test_cancel_inline_job_is_a_noop(self, queue: InMemoryJobQueue) -> None:
        # Inline jobs always finish before `cancel` runs; the call returns False.
        job_id = queue.enqueue(_add, 1, 2)
        assert queue.cancel(job_id) is False
        assert queue.get(job_id).status == JobStatus.SUCCESS
