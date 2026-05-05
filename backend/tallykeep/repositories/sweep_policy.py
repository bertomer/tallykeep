"""SweepPolicy repository — CRUD over the `sweep_policy` table."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from tallykeep.domain.enums import SafetyWarningKind, SafetyWarningSeverity, SweepTriggerType
from tallykeep.domain.sweep_policy import SafetyWarning, SweepPolicy
from tallykeep.models.sweep import SweepPolicyRow


def _warnings_to_json(warnings: list[SafetyWarning]) -> list[dict[str, Any]]:
    return [
        {
            "kind": w.kind.value,
            "severity": w.severity.value,
            "message": w.message,
            "user_acknowledged": w.user_acknowledged,
        }
        for w in warnings
    ]


def _json_to_warnings(data: list[dict[str, Any]] | None) -> list[SafetyWarning]:
    if not data:
        return []
    return [
        SafetyWarning(
            kind=SafetyWarningKind(w["kind"]),
            severity=SafetyWarningSeverity(w["severity"]),
            message=w["message"],
            user_acknowledged=w.get("user_acknowledged", False),
        )
        for w in data
    ]


def _row_to_domain(row: SweepPolicyRow) -> SweepPolicy:
    return SweepPolicy(
        id=row.id,
        name=row.name,
        source_holding_id=row.source_holding_id,
        destination_holding_id=row.destination_holding_id,
        is_enabled=row.is_enabled,
        trigger_type=SweepTriggerType(row.trigger_type),
        trigger_configuration=dict(row.trigger_configuration or {}),
        minimum_balance_sats=row.minimum_balance_sats,
        maximum_per_period_sats=row.maximum_per_period_sats,
        requires_user_confirmation=row.requires_user_confirmation,
        is_dry_run=row.is_dry_run,
        safety_warnings=_json_to_warnings(row.safety_warnings),
        last_executed_at=row.last_executed_at,
        last_result_summary=row.last_result_summary,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get(session: Session, policy_id: UUID) -> SweepPolicy | None:
    row = session.get(SweepPolicyRow, policy_id)
    return _row_to_domain(row) if row is not None else None


def list_policies(
    session: Session,
    *,
    source_holding_id: UUID | None = None,
    enabled: bool | None = None,
) -> list[SweepPolicy]:
    stmt = select(SweepPolicyRow)
    if source_holding_id is not None:
        stmt = stmt.where(SweepPolicyRow.source_holding_id == source_holding_id)
    if enabled is not None:
        stmt = stmt.where(SweepPolicyRow.is_enabled.is_(enabled))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(r) for r in rows]


def create(session: Session, policy: SweepPolicy) -> None:
    row = SweepPolicyRow(
        id=policy.id,
        name=policy.name,
        source_holding_id=policy.source_holding_id,
        destination_holding_id=policy.destination_holding_id,
        is_enabled=policy.is_enabled,
        trigger_type=policy.trigger_type.value,
        trigger_configuration=policy.trigger_configuration,
        minimum_balance_sats=policy.minimum_balance_sats,
        maximum_per_period_sats=policy.maximum_per_period_sats,
        requires_user_confirmation=policy.requires_user_confirmation,
        is_dry_run=policy.is_dry_run,
        safety_warnings=_warnings_to_json(policy.safety_warnings),
    )
    session.add(row)


def update_policy(
    session: Session,
    policy_id: UUID,
    *,
    name: str | None = None,
    trigger_type: SweepTriggerType | None = None,
    trigger_configuration: dict[str, Any] | None = None,
    minimum_balance_sats: int | None = None,
    maximum_per_period_sats: int | None = None,
    requires_user_confirmation: bool | None = None,
    is_dry_run: bool | None = None,
    safety_warnings: list[SafetyWarning] | None = None,
) -> SweepPolicy | None:
    row = session.get(SweepPolicyRow, policy_id)
    if row is None:
        return None
    if name is not None:
        row.name = name
    if trigger_type is not None:
        row.trigger_type = trigger_type.value
    if trigger_configuration is not None:
        row.trigger_configuration = trigger_configuration
    if minimum_balance_sats is not None:
        row.minimum_balance_sats = minimum_balance_sats
    if maximum_per_period_sats is not None:
        row.maximum_per_period_sats = maximum_per_period_sats
    if requires_user_confirmation is not None:
        row.requires_user_confirmation = requires_user_confirmation
    if is_dry_run is not None:
        row.is_dry_run = is_dry_run
    if safety_warnings is not None:
        row.safety_warnings = _warnings_to_json(safety_warnings)
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def set_enabled(session: Session, policy_id: UUID, *, enabled: bool) -> SweepPolicy | None:
    row = session.get(SweepPolicyRow, policy_id)
    if row is None:
        return None
    row.is_enabled = enabled
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def delete(session: Session, policy_id: UUID) -> bool:
    row = session.get(SweepPolicyRow, policy_id)
    if row is None:
        return False
    session.delete(row)
    return True


def acknowledge_all_warnings(session: Session, policy_id: UUID) -> SweepPolicy | None:
    row = session.get(SweepPolicyRow, policy_id)
    if row is None:
        return None
    warnings = _json_to_warnings(row.safety_warnings)
    for w in warnings:
        w.user_acknowledged = True
    row.safety_warnings = _warnings_to_json(warnings)
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def pause_all(session: Session) -> int:
    result = session.execute(
        update(SweepPolicyRow)
        .where(SweepPolicyRow.is_enabled.is_(True))
        .values(is_enabled=False, updated_at=datetime.now(UTC))
    )
    return result.rowcount  # type: ignore[return-value]


def resume_all(session: Session) -> int:
    result = session.execute(
        update(SweepPolicyRow)
        .where(SweepPolicyRow.is_enabled.is_(False))
        .values(is_enabled=True, updated_at=datetime.now(UTC))
    )
    return result.rowcount  # type: ignore[return-value]
