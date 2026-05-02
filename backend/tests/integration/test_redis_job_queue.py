"""RedisQueueJobQueue integration tests against real Redis + RQ.

Each test uses a fresh, randomly-named queue so concurrent test runs do not see
each other's jobs. We drain queued jobs in-process via SimpleWorker (burst mode)
rather than spawning a separate worker container.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator
from uuid import uuid4

import pytest

from tallykeep.domain.enums import JobStatus
from tallykeep.infrastructure.job_queue import RedisQueueJobQueue
from tests.integration.jobs_helpers import add, echo_kwargs, explode


pytestmark = pytest.mark.integration


@pytest.fixture()
def queue(redis_url: str) -> Iterator[RedisQueueJobQueue]:
    name = f"test_{secrets.token_hex(4)}"
    q = RedisQueueJobQueue(redis_url, queue_name=name)
    try:
        yield q
    finally:
        # Best-effort cleanup of any lingering RQ keys for this queue.
        q._queue.delete(delete_jobs=True)
        q.close()


# --- enqueue + drain ------------------------------------------------------------


def test_enqueue_then_drain_runs_job_and_records_result(
    queue: RedisQueueJobQueue,
) -> None:
    job_id = queue.enqueue(add, 2, 3)

    # Right after enqueue the job is queued — not yet running.
    info = queue.get(job_id)
    assert info.status == JobStatus.QUEUED

    queue.drain_for_tests()

    info = queue.get(job_id)
    assert info.status == JobStatus.SUCCESS
    assert info.result == 5
    assert info.started_at is not None
    assert info.finished_at is not None


def test_failing_job_records_failure(queue: RedisQueueJobQueue) -> None:
    job_id = queue.enqueue(explode)
    queue.drain_for_tests()

    info = queue.get(job_id)
    assert info.status == JobStatus.FAILED
    assert info.error_message is not None
    assert "intentional failure" in info.error_message


def test_kwargs_pass_through_pickling(queue: RedisQueueJobQueue) -> None:
    job_id = queue.enqueue(echo_kwargs, a=1, b="two", c=[3, 4])
    queue.drain_for_tests()
    info = queue.get(job_id)
    assert info.status == JobStatus.SUCCESS
    assert info.result == {"a": 1, "b": "two", "c": [3, 4]}


# --- lookup -------------------------------------------------------------------


def test_get_unknown_job_raises_keyerror(queue: RedisQueueJobQueue) -> None:
    with pytest.raises(KeyError):
        queue.get(uuid4())


# --- cancel -------------------------------------------------------------------


def test_cancel_queued_job_succeeds(queue: RedisQueueJobQueue) -> None:
    job_id = queue.enqueue(add, 1, 2)
    assert queue.cancel(job_id) is True

    # Cancelled jobs surface as CANCELLED through our status mapping.
    info = queue.get(job_id)
    assert info.status == JobStatus.CANCELLED


def test_cancel_unknown_job_returns_false(
    queue: RedisQueueJobQueue,
) -> None:
    assert queue.cancel(uuid4()) is False


# --- diagnostics -------------------------------------------------------------


def test_is_healthy_returns_true_when_connected(
    queue: RedisQueueJobQueue,
) -> None:
    assert queue.is_healthy() is True


def test_queue_length_reflects_pending_jobs(queue: RedisQueueJobQueue) -> None:
    assert queue.queue_length() == 0
    queue.enqueue(add, 1, 1)
    queue.enqueue(add, 2, 2)
    assert queue.queue_length() == 2
    queue.drain_for_tests()
    assert queue.queue_length() == 0
