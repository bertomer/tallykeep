"""SweepEngine — spec module 07 / M8.

Subscribes to `custodial_provider.balance_updated` events. For THRESHOLD-
triggered enabled policies whose source holding matches the updated provider's
holding, creates a SweepExecution when the balance exceeds the threshold.

Dry-run executions are immediately marked COMPLETED. Non-dry-run executions are
left in REQUESTED status for the actual withdrawal worker (M8.1+).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.domain.enums import SweepExecutionStatus, SweepTriggerType
from tallykeep.domain.sweep_policy import SweepExecution
from tallykeep.infrastructure.event_bus import Event, EventBus, Subscription
from tallykeep.repositories import custodial_provider as cp_repo
from tallykeep.repositories import sweep_execution as se_repo
from tallykeep.repositories import sweep_policy as sp_repo


logger = logging.getLogger(__name__)


class SweepEngine:
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
            ["custodial_provider.balance_updated"],
            self._on_balance_updated,
        )
        logger.info("SweepEngine: subscribed to custodial_provider.balance_updated")

    def stop(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None
        logger.info("SweepEngine: unsubscribed")

    def _on_balance_updated(self, event: Event) -> None:
        holding_id_raw = event.payload.get("holding_id")
        balance_sats_raw = event.payload.get("balance_sats")

        if holding_id_raw is None or balance_sats_raw is None:
            return

        try:
            holding_id = UUID(str(holding_id_raw))
            balance_sats = int(balance_sats_raw)
        except (TypeError, ValueError):
            logger.warning("SweepEngine: malformed balance_updated payload: %r", event.payload)
            return

        try:
            with self._session_factory() as session:
                self._process_threshold_policies(session, holding_id, balance_sats)
                session.commit()
        except Exception:  # noqa: BLE001
            logger.exception(
                "SweepEngine: error processing balance update for holding %s", holding_id
            )

    def _process_threshold_policies(
        self, session: Session, source_holding_id: UUID, balance_sats: int
    ) -> None:
        policies = sp_repo.list_policies(session, source_holding_id=source_holding_id, enabled=True)

        for policy in policies:
            if policy.trigger_type != SweepTriggerType.THRESHOLD:
                continue

            threshold = policy.trigger_configuration.get("threshold_sats", 0)
            if balance_sats <= threshold:
                continue

            sweep_amount = balance_sats - policy.minimum_balance_sats
            if policy.maximum_per_period_sats is not None:
                sweep_amount = min(sweep_amount, policy.maximum_per_period_sats)

            if sweep_amount <= 0:
                continue

            now = datetime.now(UTC)
            initial_status = (
                SweepExecutionStatus.AWAITING_USER_CONFIRMATION
                if policy.requires_user_confirmation
                else SweepExecutionStatus.REQUESTED
            )

            execution = SweepExecution(
                id=uuid4(),
                sweep_policy_id=policy.id,
                triggered_at=now,
                trigger_source=SweepTriggerType.THRESHOLD,
                pre_balance_sats=balance_sats,
                intended_amount_sats=sweep_amount,
                status=initial_status,
                provider_withdrawal_id=None,
                expected_txid=None,
                confirmed_txid=None,
                error_message=None,
                completed_at=None,
            )
            se_repo.create(session, execution)

            if policy.is_dry_run:
                se_repo.update_status(
                    session,
                    execution.id,
                    status=SweepExecutionStatus.COMPLETED,
                    completed_at=now,
                )
                logger.info(
                    "SweepEngine: dry-run execution %s completed for policy %s",
                    execution.id,
                    policy.id,
                )
            else:
                logger.info(
                    "SweepEngine: created execution %s (status=%s) for policy %s",
                    execution.id,
                    initial_status.value,
                    policy.id,
                )


__all__ = ["SweepEngine"]
