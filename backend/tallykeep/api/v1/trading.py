"""Trading endpoints — sweep policies + executions. Spec module 04 / 07 / M8."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.api.v1._stubs import not_implemented_response
from tallykeep.domain.enums import SweepExecutionStatus
from tallykeep.schemas.trading import (
    SafetyWarningOut,
    SweepExecutionOut,
    SweepPolicyCreate,
    SweepPolicyOut,
    SweepPolicyPatch,
)
from tallykeep.services import trading_service
from tallykeep.services.trading_service import (
    ExecutionNotFound,
    PolicyHasUnacknowledgedWarnings,
    PolicyNotFound,
    TradingServiceError,
    WrongExecutionStatus,
)


router = APIRouter(tags=["trading"])


def _policy_to_out(p) -> SweepPolicyOut:  # type: ignore[no-untyped-def]
    return SweepPolicyOut(
        id=p.id,
        name=p.name,
        source_holding_id=p.source_holding_id,
        destination_holding_id=p.destination_holding_id,
        is_enabled=p.is_enabled,
        trigger_type=p.trigger_type,
        trigger_configuration=p.trigger_configuration,
        minimum_balance_sats=p.minimum_balance_sats,
        maximum_per_period_sats=p.maximum_per_period_sats,
        requires_user_confirmation=p.requires_user_confirmation,
        is_dry_run=p.is_dry_run,
        safety_warnings=[
            SafetyWarningOut(
                kind=w.kind,
                severity=w.severity,
                message=w.message,
                user_acknowledged=w.user_acknowledged,
            )
            for w in p.safety_warnings
        ],
        last_executed_at=p.last_executed_at,
        last_result_summary=p.last_result_summary,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _execution_to_out(e) -> SweepExecutionOut:  # type: ignore[no-untyped-def]
    return SweepExecutionOut(
        id=e.id,
        sweep_policy_id=e.sweep_policy_id,
        triggered_at=e.triggered_at,
        trigger_source=e.trigger_source,
        pre_balance_sats=e.pre_balance_sats,
        intended_amount_sats=e.intended_amount_sats,
        status=e.status,
        provider_withdrawal_id=e.provider_withdrawal_id,
        expected_txid=e.expected_txid,
        confirmed_txid=e.confirmed_txid,
        error_message=e.error_message,
        completed_at=e.completed_at,
    )


# --- Sweep policies -------------------------------------------------------------


@router.get("/sweep-policies", response_model=list[SweepPolicyOut])
async def list_sweep_policies(
    source_holding_id: UUID | None = None,
    enabled: bool | None = None,
    session: Session = Depends(get_db_session),
) -> list[SweepPolicyOut]:
    policies = trading_service.list_sweep_policies(
        session, source_holding_id=source_holding_id, enabled=enabled
    )
    return [_policy_to_out(p) for p in policies]


@router.post("/sweep-policies", response_model=SweepPolicyOut, status_code=201)
async def create_sweep_policy(
    body: SweepPolicyCreate, session: Session = Depends(get_db_session)
) -> SweepPolicyOut:
    try:
        policy = trading_service.create_sweep_policy(
            session,
            name=body.name,
            source_holding_id=body.source_holding_id,
            destination_holding_id=body.destination_holding_id,
            trigger_type=body.trigger_type,
            trigger_configuration=body.trigger_configuration,
            minimum_balance_sats=body.minimum_balance_sats,
            maximum_per_period_sats=body.maximum_per_period_sats,
            requires_user_confirmation=body.requires_user_confirmation,
            is_dry_run=body.is_dry_run,
        )
        session.commit()
    except TradingServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.post("/sweep-policies/pause-all")
async def pause_all_sweep_policies(
    session: Session = Depends(get_db_session),
) -> dict:  # type: ignore[type-arg]
    count = trading_service.pause_all_policies(session)
    session.commit()
    return {"paused": count}


@router.post("/sweep-policies/resume-all")
async def resume_all_sweep_policies(
    session: Session = Depends(get_db_session),
) -> dict:  # type: ignore[type-arg]
    count = trading_service.resume_all_policies(session)
    session.commit()
    return {"resumed": count}


@router.get("/sweep-policies/{policy_id}", response_model=SweepPolicyOut)
async def get_sweep_policy(
    policy_id: UUID, session: Session = Depends(get_db_session)
) -> SweepPolicyOut:
    try:
        policy = trading_service.get_sweep_policy(session, policy_id)
    except PolicyNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.patch("/sweep-policies/{policy_id}", response_model=SweepPolicyOut)
async def patch_sweep_policy(
    policy_id: UUID,
    body: SweepPolicyPatch,
    session: Session = Depends(get_db_session),
) -> SweepPolicyOut:
    try:
        policy = trading_service.update_sweep_policy(
            session,
            policy_id,
            name=body.name,
            trigger_type=body.trigger_type,
            trigger_configuration=body.trigger_configuration,
            minimum_balance_sats=body.minimum_balance_sats,
            maximum_per_period_sats=body.maximum_per_period_sats,
            requires_user_confirmation=body.requires_user_confirmation,
            is_dry_run=body.is_dry_run,
        )
        session.commit()
    except PolicyNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TradingServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.delete("/sweep-policies/{policy_id}", status_code=204)
async def delete_sweep_policy(
    policy_id: UUID, session: Session = Depends(get_db_session)
) -> Response:
    try:
        trading_service.delete_sweep_policy(session, policy_id)
        session.commit()
    except PolicyNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TradingServiceError as exc:
        session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Response(status_code=204)


@router.post(
    "/sweep-policies/{policy_id}/acknowledge-warnings",
    response_model=SweepPolicyOut,
)
async def acknowledge_sweep_warnings(
    policy_id: UUID, session: Session = Depends(get_db_session)
) -> SweepPolicyOut:
    try:
        policy = trading_service.acknowledge_warnings(session, policy_id)
        session.commit()
    except PolicyNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.post("/sweep-policies/{policy_id}/enable", response_model=SweepPolicyOut)
async def enable_sweep_policy(
    policy_id: UUID, session: Session = Depends(get_db_session)
) -> SweepPolicyOut:
    try:
        policy = trading_service.enable_sweep_policy(session, policy_id)
        session.commit()
    except PolicyNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PolicyHasUnacknowledgedWarnings as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.post("/sweep-policies/{policy_id}/disable", response_model=SweepPolicyOut)
async def disable_sweep_policy(
    policy_id: UUID, session: Session = Depends(get_db_session)
) -> SweepPolicyOut:
    try:
        policy = trading_service.disable_sweep_policy(session, policy_id)
        session.commit()
    except PolicyNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _policy_to_out(policy)


@router.post("/sweep-policies/{policy_id}/execute-now", status_code=501)
async def execute_sweep_policy_now(policy_id: UUID):  # type: ignore[no-untyped-def]
    # Manual execution endpoint lands in M8.1 (requires SweepEngine worker to be
    # running and able to process the execution). Wired in post-M8 milestone.
    return not_implemented_response(
        milestone="M8.1", route="POST /api/v1/sweep-policies/{id}/execute-now"
    )


@router.get(
    "/sweep-policies/{policy_id}/executions",
    response_model=list[SweepExecutionOut],
)
async def list_sweep_policy_executions(
    policy_id: UUID,
    limit: int = 50,
    session: Session = Depends(get_db_session),
) -> list[SweepExecutionOut]:
    try:
        trading_service.get_sweep_policy(session, policy_id)
    except PolicyNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    executions = trading_service.list_sweep_executions(
        session, sweep_policy_id=policy_id, limit=limit
    )
    return [_execution_to_out(e) for e in executions]


# --- Sweep executions -----------------------------------------------------------


@router.get("/sweep-executions", response_model=list[SweepExecutionOut])
async def list_sweep_executions(
    sweep_policy_id: UUID | None = None,
    status: SweepExecutionStatus | None = None,
    limit: int = 50,
    session: Session = Depends(get_db_session),
) -> list[SweepExecutionOut]:
    executions = trading_service.list_sweep_executions(
        session, sweep_policy_id=sweep_policy_id, status=status, limit=limit
    )
    return [_execution_to_out(e) for e in executions]


@router.get("/sweep-executions/{execution_id}", response_model=SweepExecutionOut)
async def get_sweep_execution(
    execution_id: UUID, session: Session = Depends(get_db_session)
) -> SweepExecutionOut:
    try:
        execution = trading_service.get_sweep_execution(session, execution_id)
    except ExecutionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _execution_to_out(execution)


@router.post(
    "/sweep-executions/{execution_id}/confirm", response_model=SweepExecutionOut
)
async def confirm_sweep_execution(
    execution_id: UUID, session: Session = Depends(get_db_session)
) -> SweepExecutionOut:
    try:
        execution = trading_service.confirm_sweep_execution(session, execution_id)
        session.commit()
    except ExecutionNotFound as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except WrongExecutionStatus as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _execution_to_out(execution)
