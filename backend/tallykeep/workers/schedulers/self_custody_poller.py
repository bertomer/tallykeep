"""SelfCustodyPoller — spec module 07 / M9.

Runs on a fixed interval; for every enabled threshold SweepPolicy whose
source holding is NOT an Account (i.e. a self-custody Purse, Strongbox, or
Vault) it:

  1. Sums the current UTXO balance of the source holding.
  2. When balance > threshold, creates a SweepExecution + an auto-signed
     PaymentRequest (PSBT built immediately so the user can sign it).
  3. Dry-run policies skip the PaymentRequest and immediately COMPLETE.

The PaymentRequest.sweep_execution_id links the two records so the
ChainListener can mark the SweepExecution COMPLETED once the tx confirms.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.adapters.descriptor_adapter import DescriptorAdapter
from tallykeep.adapters.node_adapter import NodeAdapter
from tallykeep.domain.enums import (
    HoldingType,
    SweepExecutionStatus,
    SweepTriggerType,
)
from tallykeep.domain.sweep_policy import SweepExecution
from tallykeep.repositories import custodial_provider as cp_repo
from tallykeep.repositories import descriptor as descriptor_repo
from tallykeep.repositories import sweep_execution as se_repo
from tallykeep.repositories import sweep_policy as sp_repo
from tallykeep.repositories import utxo as utxo_repo
from tallykeep.services import holding_service


logger = logging.getLogger(__name__)


class SelfCustodyPoller:
    """Background thread that checks self-custody holding balances and triggers sweeps."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        node: NodeAdapter,
        bus,  # type: ignore[no-untyped-def]  EventBus
        interval_seconds: int = 900,
    ) -> None:
        self._session_factory = session_factory
        self._node = node
        self._bus = bus
        self._interval = interval_seconds
        self._descriptor_adapter = DescriptorAdapter()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="SelfCustodyPoller", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def _run(self) -> None:
        logger.info("SelfCustodyPoller: started (interval=%ds)", self._interval)
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception:  # noqa: BLE001
                logger.exception("SelfCustodyPoller: poll_once failed")
            self._stop_event.wait(timeout=self._interval)
        logger.info("SelfCustodyPoller: stopped")

    def _poll_once(self) -> None:
        with self._session_factory() as session:
            policies = sp_repo.list_policies(session, enabled=True)

        for policy in policies:
            if policy.trigger_type != SweepTriggerType.THRESHOLD:
                continue

            with self._session_factory() as session:
                source = holding_service.get_holding(session, policy.source_holding_id)

            if source is None or source.holding_type == HoldingType.ACCOUNT:
                continue  # Account holdings handled by CustodialPoller

            # Sum UTXO balance for all descriptors of the source holding.
            with self._session_factory() as session:
                descriptors = descriptor_repo.list_descriptors_for_holding(
                    session, policy.source_holding_id
                )
                balance_sats = sum(
                    utxo_repo.descriptor_balance_sats(session, d.id)
                    for d in descriptors
                )

            threshold = policy.trigger_configuration.get("threshold_sats", 0)
            if balance_sats <= threshold:
                continue

            sweep_amount = balance_sats - policy.minimum_balance_sats
            if policy.maximum_per_period_sats is not None:
                sweep_amount = min(sweep_amount, policy.maximum_per_period_sats)

            if sweep_amount <= 0:
                continue

            logger.info(
                "SelfCustodyPoller: threshold met for policy %s "
                "(balance=%d, sweep=%d sats)",
                policy.id, balance_sats, sweep_amount,
            )
            self._trigger_sweep(policy, balance_sats, sweep_amount)

    def _trigger_sweep(self, policy, balance_sats: int, sweep_amount: int) -> None:  # type: ignore[no-untyped-def]
        from tallykeep.services import banking_service

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

        with self._session_factory() as session:
            se_repo.create(session, execution)

            if policy.is_dry_run:
                se_repo.update_status(
                    session, execution.id,
                    status=SweepExecutionStatus.COMPLETED,
                    completed_at=now,
                )
                session.commit()
                logger.info("SelfCustodyPoller: dry-run execution %s completed", execution.id)
                return

            # Resolve destination address.
            dest_descriptors = descriptor_repo.list_descriptors_for_holding(
                session, policy.destination_holding_id
            )
            if not dest_descriptors:
                se_repo.update_status(
                    session, execution.id,
                    status=SweepExecutionStatus.FAILED,
                    error_message="Destination holding has no descriptors",
                    completed_at=now,
                )
                session.commit()
                logger.warning(
                    "SelfCustodyPoller: no descriptors on destination for policy %s",
                    policy.id,
                )
                return

            address_row = descriptor_repo.next_unused_address(
                session, dest_descriptors[0].id, is_change=False
            )
            if address_row is None:
                se_repo.update_status(
                    session, execution.id,
                    status=SweepExecutionStatus.FAILED,
                    error_message="No unused receive address on destination holding",
                    completed_at=now,
                )
                session.commit()
                logger.warning(
                    "SelfCustodyPoller: no unused address on destination for policy %s",
                    policy.id,
                )
                return

            try:
                build_result = banking_service.build_payment_request(
                    session,
                    holding_id=policy.source_holding_id,
                    destination_address=address_row.address,
                    amount_sats=sweep_amount,
                    fee_strategy="normal",
                    fee_sat_per_vbyte=None,
                    description=f"Auto-sweep for policy {policy.id}",
                    descriptor_adapter=self._descriptor_adapter,
                    node=self._node,
                )
            except Exception as exc:  # noqa: BLE001
                se_repo.update_status(
                    session, execution.id,
                    status=SweepExecutionStatus.FAILED,
                    error_message=f"PaymentRequest build failed: {exc}",
                    completed_at=now,
                )
                session.commit()
                logger.warning(
                    "SelfCustodyPoller: PaymentRequest build failed for policy %s: %s",
                    policy.id, exc,
                )
                return

            # Link execution → PaymentRequest.
            pr_row = session.get(
                __import__(
                    "tallykeep.models.payment_request",
                    fromlist=["PaymentRequestRow"],
                ).PaymentRequestRow,
                build_result.payment_request.id,
            )
            if pr_row is not None:
                pr_row.sweep_execution_id = execution.id

            session.commit()
            logger.info(
                "SelfCustodyPoller: created execution %s + PaymentRequest %s for policy %s",
                execution.id, build_result.payment_request.id, policy.id,
            )

        self._bus.publish(
            "trading.sweep_execution.payment_request_created",
            {
                "execution_id": str(execution.id),
                "payment_request_id": str(build_result.payment_request.id),
                "sweep_policy_id": str(policy.id),
            },
        )


__all__ = ["SelfCustodyPoller"]
