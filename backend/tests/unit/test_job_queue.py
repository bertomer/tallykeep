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


class TestMetadata:
    def test_job_type_and_label_stored(self, queue: InMemoryJobQueue) -> None:
        job_id = queue.enqueue(_add, 1, 2, job_type="test_job", label="my label")
        info = queue.get(job_id)
        assert info.job_type == "test_job"
        assert info.label == "my label"

    def test_missing_metadata_defaults_to_none(self, queue: InMemoryJobQueue) -> None:
        job_id = queue.enqueue(_add, 1, 2)
        info = queue.get(job_id)
        assert info.job_type is None
        assert info.label is None


class TestListRecent:
    def test_returns_all_jobs(self, queue: InMemoryJobQueue) -> None:
        queue.enqueue(_add, 1, 2)
        queue.enqueue(_add, 3, 4)
        assert len(queue.list_recent()) == 2

    def test_filter_by_status(self, queue: InMemoryJobQueue) -> None:
        queue.enqueue(_add, 1, 2)
        queue.enqueue(_explode)
        successes = queue.list_recent(status=JobStatus.SUCCESS)
        failures = queue.list_recent(status=JobStatus.FAILED)
        assert len(successes) == 1
        assert len(failures) == 1

    def test_filter_by_job_type(self, queue: InMemoryJobQueue) -> None:
        queue.enqueue(_add, 1, 2, job_type="alpha")
        queue.enqueue(_add, 3, 4, job_type="beta")
        alpha = queue.list_recent(job_type="alpha")
        assert len(alpha) == 1
        assert alpha[0].job_type == "alpha"

    def test_limit(self, queue: InMemoryJobQueue) -> None:
        for _ in range(5):
            queue.enqueue(_add, 1, 1)
        assert len(queue.list_recent(limit=3)) == 3

    def test_ordered_most_recent_first(self, queue: InMemoryJobQueue) -> None:
        id1 = queue.enqueue(_add, 1, 1)
        id2 = queue.enqueue(_add, 2, 2)
        jobs = queue.list_recent()
        assert jobs[0].id == id2
        assert jobs[1].id == id1
