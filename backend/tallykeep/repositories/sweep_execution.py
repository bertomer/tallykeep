"""SweepExecution repository — CRUD over the `sweep_execution` table."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import SweepExecutionStatus, SweepTriggerType
from tallykeep.domain.sweep_policy import SweepExecution
from tallykeep.models.sweep import SweepExecutionRow


def _row_to_domain(row: SweepExecutionRow) -> SweepExecution:
    return SweepExecution(
        id=row.id,
        sweep_policy_id=row.sweep_policy_id,
        triggered_at=row.triggered_at,
        trigger_source=SweepTriggerType(row.trigger_source),
        pre_balance_sats=row.pre_balance_sats,
        intended_amount_sats=row.intended_amount_sats,
        status=SweepExecutionStatus(row.status),
        provider_withdrawal_id=row.provider_withdrawal_id,
        expected_txid=row.expected_txid,
        confirmed_txid=row.confirmed_txid,
        error_message=row.error_message,
        completed_at=row.completed_at,
    )


def get(session: Session, execution_id: UUID) -> SweepExecution | None:
    row = session.get(SweepExecutionRow, execution_id)
    return _row_to_domain(row) if row is not None else None


def get_by_expected_txid(session: Session, txid: str) -> SweepExecution | None:
    from sqlalchemy import select
    row = session.execute(
        select(SweepExecutionRow).where(SweepExecutionRow.expected_txid == txid)
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def list_executions(
    session: Session,
    *,
    sweep_policy_id: UUID | None = None,
    status: SweepExecutionStatus | None = None,
    limit: int = 50,
) -> list[SweepExecution]:
    stmt = select(SweepExecutionRow)
    if sweep_policy_id is not None:
        stmt = stmt.where(SweepExecutionRow.sweep_policy_id == sweep_policy_id)
    if status is not None:
        stmt = stmt.where(SweepExecutionRow.status == status.value)
    stmt = stmt.order_by(SweepExecutionRow.triggered_at.desc()).limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(r) for r in rows]


def create(session: Session, execution: SweepExecution) -> None:
    row = SweepExecutionRow(
        id=execution.id,
        sweep_policy_id=execution.sweep_policy_id,
        triggered_at=execution.triggered_at,
        trigger_source=execution.trigger_source.value,
        pre_balance_sats=execution.pre_balance_sats,
        intended_amount_sats=execution.intended_amount_sats,
        status=execution.status.value,
        provider_withdrawal_id=execution.provider_withdrawal_id,
        expected_txid=execution.expected_txid,
        confirmed_txid=execution.confirmed_txid,
        error_message=execution.error_message,
        completed_at=execution.completed_at,
    )
    session.add(row)


def update_status(
    session: Session,
    execution_id: UUID,
    *,
    status: SweepExecutionStatus,
    provider_withdrawal_id: str | None = None,
    expected_txid: str | None = None,
    confirmed_txid: str | None = None,
    error_message: str | None = None,
    completed_at: datetime | None = None,
) -> SweepExecution | None:
    row = session.get(SweepExecutionRow, execution_id)
    if row is None:
        return None
    row.status = status.value
    if provider_withdrawal_id is not None:
        row.provider_withdrawal_id = provider_withdrawal_id
    if expected_txid is not None:
        row.expected_txid = expected_txid
    if confirmed_txid is not None:
        row.confirmed_txid = confirmed_txid
    if error_message is not None:
        row.error_message = error_message
    if completed_at is not None:
        row.completed_at = completed_at
    return _row_to_domain(row)
