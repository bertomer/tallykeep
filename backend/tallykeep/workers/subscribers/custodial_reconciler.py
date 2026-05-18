"""CustodialReconciler — ADR-0013 custodial-side linkage subscriber.

Subscribes to treasury.custodial.ledger_entry_added. For each new
deposit or withdrawal entry, attempts to match against pending
sweep_executions by direction, amount tolerance, and time window.

Matching is conservative: false positives (claiming a user-initiated
entry was TK-initiated) are a trust break; false negatives leave an
entry unlinked, which reads the same as a true external action.
Ambiguous matches (two or more candidates) link to neither.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from tallykeep.domain.enums import SweepExecutionStatus
from tallykeep.infrastructure.event_bus import Event, EventBus, Subscription
from tallykeep.models.sweep import SweepExecutionRow, SweepPolicyRow
from tallykeep.repositories import custodial_ledger_entry as cle_repo
from tallykeep.repositories import sweep_execution as se_repo


logger = logging.getLogger(__name__)

# Amount tolerance: 2% of intended, floored at 10 000 sats.
_TOLERANCE_FRACTION = 0.02
_TOLERANCE_FLOOR_SATS = 10_000

# Time windows relative to sweep_execution.triggered_at.
_OUTFLOW_WINDOW = timedelta(hours=4)
_INFLOW_WINDOW = timedelta(hours=12)   # wider: provider deposits lag on-chain confirmation

_OUTFLOW_STATUSES = [
    SweepExecutionStatus.REQUESTED.value,
    SweepExecutionStatus.AWAITING_USER_CONFIRMATION.value,
    SweepExecutionStatus.DISPATCHED.value,
]
_INFLOW_STATUSES = [
    SweepExecutionStatus.DISPATCHED.value,
    SweepExecutionStatus.ONCHAIN_PENDING.value,
]


class CustodialReconciler:
    def __init__(
        self,
        *,
        bus: EventBus,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._bus = bus
        self._session_factory = session_factory
        self._subscription: Subscription | None = None

    def start(self) -> None:
        if self._subscription is not None:
            return
        self._subscription = self._bus.subscribe(
            ["treasury.custodial.ledger_entry_added"],
            self._on_entry_added,
        )
        logger.info("CustodialReconciler: subscribed to treasury.custodial.ledger_entry_added")

    def stop(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None
        logger.info("CustodialReconciler: unsubscribed")

    def _on_entry_added(self, event: Event) -> None:
        entry = event.payload.get("entry", {})
        holding_id_raw = event.payload.get("holding_id")
        entry_id_raw = entry.get("id")
        kind = entry.get("kind")
        amount_sats_raw = entry.get("amount_sats")
        timestamp_raw = entry.get("timestamp")

        if kind not in ("deposit", "withdrawal"):
            return

        if None in (holding_id_raw, entry_id_raw, amount_sats_raw, timestamp_raw):
            logger.warning("CustodialReconciler: malformed payload: %r", event.payload)
            return

        try:
            holding_id = UUID(str(holding_id_raw))
            entry_id = UUID(str(entry_id_raw))
            amount_sats = int(amount_sats_raw)
            entry_ts = datetime.fromisoformat(str(timestamp_raw))
        except (TypeError, ValueError):
            logger.warning("CustodialReconciler: cannot parse payload: %r", event.payload)
            return

        try:
            with self._session_factory() as session:
                if kind == "withdrawal":
                    self._reconcile_outflow(session, holding_id, entry_id, amount_sats, entry_ts)
                else:
                    self._reconcile_inflow(session, holding_id, entry_id, amount_sats, entry_ts)
                session.commit()
        except Exception:  # noqa: BLE001
            logger.exception(
                "CustodialReconciler: error processing entry %s (kind=%s)", entry_id, kind
            )

    def _reconcile_outflow(
        self,
        session: Session,
        holding_id: UUID,
        entry_id: UUID,
        amount_sats: int,
        entry_ts: datetime,
    ) -> None:
        """Match a withdrawal entry against pending outflow sweep_executions.

        An outflow has source_holding_id == this Account's holding_id.
        """
        window_start = entry_ts - _OUTFLOW_WINDOW
        window_end = entry_ts + _OUTFLOW_WINDOW

        rows = session.execute(
            select(SweepExecutionRow)
            .join(SweepPolicyRow, SweepExecutionRow.sweep_policy_id == SweepPolicyRow.id)
            .where(SweepPolicyRow.source_holding_id == holding_id)
            .where(SweepExecutionRow.status.in_(_OUTFLOW_STATUSES))
            .where(SweepExecutionRow.triggered_at >= window_start)
            .where(SweepExecutionRow.triggered_at <= window_end)
        ).scalars().all()

        matched = [r for r in rows if _within_tolerance(amount_sats, r.intended_amount_sats)]

        if len(matched) != 1:
            logger.debug(
                "CustodialReconciler: outflow entry %s — %d candidates, marking unmatched",
                entry_id, len(matched),
            )
            cle_repo.mark_unmatched(session, entry_id)
            return

        execution = matched[0]
        policy = session.get(SweepPolicyRow, execution.sweep_policy_id)

        cle_repo.set_reconciled(
            session,
            entry_id,
            linked_sweep_execution_id=execution.id,
            linked_counterparty_holding_id=policy.destination_holding_id if policy else None,
            linked_chain_ledger_entry_id=None,  # chain side fires separately
        )

        if execution.status != SweepExecutionStatus.DISPATCHED.value:
            se_repo.update_status(
                session,
                execution.id,
                status=SweepExecutionStatus.DISPATCHED,
            )

        logger.info(
            "CustodialReconciler: outflow entry %s linked to sweep_execution %s",
            entry_id, execution.id,
        )

    def _reconcile_inflow(
        self,
        session: Session,
        holding_id: UUID,
        entry_id: UUID,
        amount_sats: int,
        entry_ts: datetime,
    ) -> None:
        """Match a deposit entry against pending inflow sweep_executions.

        An inflow has destination_holding_id == this Account's holding_id.
        Chain-side COMPLETED advancement is left to the chain scanner matcher
        (v1); this subscriber only populates the custodial-side linkage.
        """
        window_start = entry_ts - _INFLOW_WINDOW
        window_end = entry_ts + _INFLOW_WINDOW

        rows = session.execute(
            select(SweepExecutionRow)
            .join(SweepPolicyRow, SweepExecutionRow.sweep_policy_id == SweepPolicyRow.id)
            .where(SweepPolicyRow.destination_holding_id == holding_id)
            .where(SweepExecutionRow.status.in_(_INFLOW_STATUSES))
            .where(SweepExecutionRow.triggered_at >= window_start)
            .where(SweepExecutionRow.triggered_at <= window_end)
        ).scalars().all()

        matched = [r for r in rows if _within_tolerance(amount_sats, r.intended_amount_sats)]

        if len(matched) != 1:
            logger.debug(
                "CustodialReconciler: inflow entry %s — %d candidates, marking unmatched",
                entry_id, len(matched),
            )
            cle_repo.mark_unmatched(session, entry_id)
            return

        execution = matched[0]
        policy = session.get(SweepPolicyRow, execution.sweep_policy_id)

        cle_repo.set_reconciled(
            session,
            entry_id,
            linked_sweep_execution_id=execution.id,
            linked_counterparty_holding_id=policy.source_holding_id if policy else None,
            linked_chain_ledger_entry_id=None,
        )

        logger.info(
            "CustodialReconciler: inflow entry %s linked to sweep_execution %s",
            entry_id, execution.id,
        )


def _within_tolerance(observed: int, intended: int) -> bool:
    tolerance = max(int(intended * _TOLERANCE_FRACTION), _TOLERANCE_FLOOR_SATS)
    return abs(observed - intended) <= tolerance


__all__ = ["CustodialReconciler"]
