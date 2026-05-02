"""Job endpoints — spec module 04. Stubs land in M5/M8 (jobs become real once
listeners and pollers begin enqueueing them)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["jobs"])


@router.get("/jobs", status_code=501)
async def list_jobs(
    status: str | None = None, job_type: str | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/jobs"
    )


@router.get("/jobs/{job_id}", status_code=501)
async def get_job(job_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/jobs/{id}"
    )


@router.delete("/jobs/{job_id}", status_code=501)
async def cancel_job(job_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="DELETE /api/v1/jobs/{id}"
    )
