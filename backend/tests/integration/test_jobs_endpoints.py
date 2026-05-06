"""Integration tests for GET/DELETE /jobs endpoints (M8.1)."""

from __future__ import annotations

import pytest

from tallykeep.domain.enums import JobStatus
from tallykeep.infrastructure.job_queue import InMemoryJobQueue


pytestmark = pytest.mark.integration


def _noop() -> None:
    pass


def _fail() -> None:
    raise RuntimeError("intentional failure")


@pytest.fixture()
def app_with_queue(app_with_db):  # type: ignore[no-untyped-def]
    client, factory = app_with_db
    queue = InMemoryJobQueue()
    client.app.state.job_queue = queue
    return client, queue


class TestListJobs:
    def test_empty_returns_empty_list(self, app_with_queue) -> None:
        client, _ = app_with_queue
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        assert response.json() == []

    def test_enqueued_job_appears_in_list(self, app_with_queue) -> None:
        client, queue = app_with_queue
        queue.enqueue(_noop, job_type="test_type", label="a label")
        response = client.get("/api/v1/jobs")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["status"] == "success"
        assert jobs[0]["job_type"] == "test_type"
        assert jobs[0]["label"] == "a label"

    def test_filter_by_status(self, app_with_queue) -> None:
        client, queue = app_with_queue
        queue.enqueue(_noop)
        queue.enqueue(_fail)
        resp_success = client.get("/api/v1/jobs?status=success")
        resp_failed = client.get("/api/v1/jobs?status=failed")
        assert len(resp_success.json()) == 1
        assert len(resp_failed.json()) == 1

    def test_filter_by_job_type(self, app_with_queue) -> None:
        client, queue = app_with_queue
        queue.enqueue(_noop, job_type="alpha")
        queue.enqueue(_noop, job_type="beta")
        resp = client.get("/api/v1/jobs?job_type=alpha")
        assert len(resp.json()) == 1
        assert resp.json()[0]["job_type"] == "alpha"


class TestGetJob:
    def test_get_existing_job(self, app_with_queue) -> None:
        client, queue = app_with_queue
        job_id = queue.enqueue(_noop, job_type="probe")
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == str(job_id)
        assert body["status"] == "success"

    def test_get_unknown_job_returns_404(self, app_with_queue) -> None:
        client, _ = app_with_queue
        from uuid import uuid4
        response = client.get(f"/api/v1/jobs/{uuid4()}")
        assert response.status_code == 404


class TestCancelJob:
    def test_cancel_existing_job_returns_204(self, app_with_queue) -> None:
        client, queue = app_with_queue
        job_id = queue.enqueue(_noop)
        response = client.delete(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 204

    def test_cancel_unknown_job_returns_404(self, app_with_queue) -> None:
        client, _ = app_with_queue
        from uuid import uuid4
        response = client.delete(f"/api/v1/jobs/{uuid4()}")
        assert response.status_code == 404
