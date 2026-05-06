"""Job endpoints — spec module 04 / M8.1."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from tallykeep.api.dependencies import get_job_queue
from tallykeep.domain.enums import JobStatus
from tallykeep.infrastructure.job_queue import JobQueue


router = APIRouter(tags=["jobs"])


class JobOut(BaseModel):
    id: UUID
    status: JobStatus
    job_type: str | None = None
    label: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


def _to_out(info) -> JobOut:  # type: ignore[no-untyped-def]
    return JobOut(
        id=info.id,
        status=info.status,
        job_type=info.job_type,
        label=info.label,
        error_message=info.error_message,
        created_at=info.created_at,
        started_at=info.started_at,
        finished_at=info.finished_at,
    )


@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(
    status: JobStatus | None = None,
    job_type: str | None = None,
    queue: JobQueue = Depends(get_job_queue),
) -> list[JobOut]:
    return [_to_out(j) for j in queue.list_recent(status=status, job_type=job_type)]


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: UUID,
    queue: JobQueue = Depends(get_job_queue),
) -> JobOut:
    try:
        return _to_out(queue.get(job_id))
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(
    job_id: UUID,
    queue: JobQueue = Depends(get_job_queue),
) -> Response:
    try:
        queue.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")
    queue.cancel(job_id)
    return Response(status_code=204)
