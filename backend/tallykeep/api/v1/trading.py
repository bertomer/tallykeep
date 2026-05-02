"""Trading endpoints — sweep policies + executions. Spec module 04 / 07. M8."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["trading"])


# --- Sweep policies -------------------------------------------------------------


@router.get("/sweep-policies", status_code=501)
async def list_sweep_policies(
    source_holding_id: UUID | None = None, enabled: bool | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/sweep-policies"
    )


@router.post("/sweep-policies", status_code=501)
async def create_sweep_policy() -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies"
    )


@router.post("/sweep-policies/pause-all", status_code=501)
async def pause_all_sweep_policies() -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies/pause-all"
    )


@router.post("/sweep-policies/resume-all", status_code=501)
async def resume_all_sweep_policies() -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies/resume-all"
    )


@router.get("/sweep-policies/{policy_id}", status_code=501)
async def get_sweep_policy(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/sweep-policies/{id}"
    )


@router.patch("/sweep-policies/{policy_id}", status_code=501)
async def patch_sweep_policy(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="PATCH /api/v1/sweep-policies/{id}"
    )


@router.delete("/sweep-policies/{policy_id}", status_code=501)
async def delete_sweep_policy(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="DELETE /api/v1/sweep-policies/{id}"
    )


@router.post(
    "/sweep-policies/{policy_id}/acknowledge-warnings", status_code=501
)
async def acknowledge_sweep_warnings(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8",
        route="POST /api/v1/sweep-policies/{id}/acknowledge-warnings",
    )


@router.post("/sweep-policies/{policy_id}/enable", status_code=501)
async def enable_sweep_policy(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies/{id}/enable"
    )


@router.post("/sweep-policies/{policy_id}/disable", status_code=501)
async def disable_sweep_policy(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies/{id}/disable"
    )


@router.post("/sweep-policies/{policy_id}/execute-now", status_code=501)
async def execute_sweep_policy_now(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-policies/{id}/execute-now"
    )


@router.get("/sweep-policies/{policy_id}/executions", status_code=501)
async def list_sweep_policy_executions(policy_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/sweep-policies/{id}/executions"
    )


# --- Sweep executions -----------------------------------------------------------


@router.get("/sweep-executions", status_code=501)
async def list_sweep_executions(
    sweep_policy_id: UUID | None = None, status: str | None = None
) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/sweep-executions"
    )


@router.get("/sweep-executions/{execution_id}", status_code=501)
async def get_sweep_execution(execution_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="GET /api/v1/sweep-executions/{id}"
    )


@router.post("/sweep-executions/{execution_id}/confirm", status_code=501)
async def confirm_sweep_execution(execution_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M8", route="POST /api/v1/sweep-executions/{id}/confirm"
    )
