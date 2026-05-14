"""ChainListener — bitcoind ZMQ → domain events.

Spec module 01 + 05. The listener:

  1. Subscribes to bitcoind ZMQ on `hashtx` (mempool acceptance / confirmed)
     and `hashblock` (new block tip).
  2. For each `hashtx`, fetches the decoded tx via NodeAdapter and feeds it
     to ChainProcessingService.
  3. For each `hashblock`, walks the block's confirmed txids and re-feeds any
     of them that touch us so confirmation_height gets recorded.
  4. Emits the domain events specified in module 01 / 05:
       chain.tx.mempool                 { txid, affected_descriptor_ids }
       chain.tx.confirmed               { txid, height, affected_descriptor_ids }
       chain.block.new                  { height, block_hash }
       holding.utxo.received            { holding_id, descriptor_id, utxo_id, value_sats }
       holding.utxo.spent               { holding_id, descriptor_id, utxo_id }
       ledger_entry.requires_categorization { ledger_entry_id }

The listener owns its own thread; `start()` returns immediately, `stop()`
shuts it down. This matches the worker.py pattern where each component is
started during boot and joined on signal-handled shutdown.
"""

from __future__ import annotations

import logging
import threading
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.adapters.chain_event_adapter import (
    ChainEventAdapter,
    ChainNotification,
)
from tallykeep.adapters.node_adapter import NodeAdapter, NodeRpcError
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.services.chain_processing_service import (
    ChainProcessingService,
    TxProcessingResult,
)
from tallykeep.services.utxo_hygiene_service import (
    estimate_fee_rate_sat_per_vbyte,
)


logger = logging.getLogger(__name__)


class ChainListener:
    def __init__(
        self,
        *,
        zmq_endpoint: str,
        node: NodeAdapter,
        bus: EventBus,
        session_factory: sessionmaker[Session],
        processor: ChainProcessingService | None = None,
    ) -> None:
        if not zmq_endpoint:
            raise ValueError("zmq_endpoint is required")
        self._adapter = ChainEventAdapter(zmq_endpoint)
        self._node = node
        self._bus = bus
        self._session_factory = session_factory
        self._processor = processor or ChainProcessingService()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Cache the fee rate so the hygiene service doesn't pay an
        # estimatesmartfee RPC on every tx. 60-second TTL is fine — block
        # times set the natural cadence.
        self._fee_rate_cache: tuple[float, float] | None = None
        self._fee_rate_ttl_seconds = 60.0

    # --- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None:
            return
        self._adapter.subscribe()
        self._thread = threading.Thread(
            target=self._run,
            name="tallykeep-chain-listener",
            daemon=True,
        )
        self._thread.start()
        logger.info("ChainListener: started")

    def stop(self, *, timeout: float = 2.0) -> None:
        self._stop.set()
        self._adapter.close()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("ChainListener: stopped")

    # --- main loop ----------------------------------------------------------

    def _run(self) -> None:
        try:
            for notification in self._adapter.iter_messages():
                if self._stop.is_set():
                    break
                try:
                    self._handle(notification)
                except Exception:  # noqa: BLE001 — one bad msg can't kill the loop
                    logger.exception(
                        "ChainListener: failed to handle %s notification",
                        notification.kind,
                    )
        except Exception:  # noqa: BLE001
            logger.exception("ChainListener: read loop exited unexpectedly")

    def _handle(self, notification: ChainNotification) -> None:
        if notification.kind == "hashtx":
            self._handle_tx(notification.hash_hex, confirmation_height=None)
        elif notification.kind == "hashblock":
            self._handle_block(notification.hash_hex)
        else:
            logger.debug(
                "ChainListener: ignoring notification kind=%s", notification.kind
            )

    # --- handlers -----------------------------------------------------------

    def _handle_tx(self, txid: str, *, confirmation_height: int | None) -> None:
        """Fetch the decoded tx and persist its effects.

        Mempool tx: confirmation_height=None and we read from the mempool view.
        Confirmed tx (called from _handle_block): height passed explicitly.
        """
        try:
            decoded = self._node.get_raw_transaction(txid, verbose=True)
        except NodeRpcError as exc:
            # -5 ("No such mempool or blockchain transaction") happens when the
            # mempool tx evicts before we fetch it. This is expected at high
            # mempool churn; log at debug.
            if exc.code == -5:
                logger.debug("ChainListener: tx %s no longer available", txid)
                return
            raise

        # If bitcoind already reports a block hash on this tx, prefer the
        # height it reports (handles the race where hashtx fires after
        # block inclusion but the listener saw it as a mempool event).
        actual_height = confirmation_height
        if actual_height is None and isinstance(decoded.get("blockhash"), str):
            try:
                block = self._node._call("getblockheader", [decoded["blockhash"]])
                actual_height = int(block.get("height"))
            except NodeRpcError:
                actual_height = None

        block_time = None
        if isinstance(decoded.get("blocktime"), int):
            from datetime import UTC, datetime

            block_time = datetime.fromtimestamp(decoded["blocktime"], tz=UTC)

        fee_rate = self._cached_fee_rate()

        with self._session_scope() as session:
            result = self._processor.process_decoded_transaction(
                session,
                decoded,
                confirmation_height=actual_height,
                block_time=block_time,
                fee_rate_sat_per_vbyte=fee_rate,
            )
            payment_confirmation = self._link_payment_request_if_any(
                session, result
            )
            invoice_paid = self._link_invoice_if_any(session, result, decoded)
            sweep_confirmed = self._link_sweep_execution_if_any(session, result)
            session.commit()

        # Emit events outside the session so a slow Redis publish never holds
        # a transaction open.
        self._emit_tx_events(result)
        if payment_confirmation is not None:
            self._bus.publish(
                "banking.payment_request.confirmed",
                payment_confirmation,
            )
        if invoice_paid is not None:
            self._bus.publish("banking.invoice.paid", invoice_paid)
        if sweep_confirmed is not None:
            self._bus.publish("treasury.sweep_execution.completed", sweep_confirmed)

    def _handle_block(self, block_hash: str) -> None:
        """A new block tip arrived. Emit chain.block.new and drive any
        confirmations through `_handle_tx` so per-tx events fire."""
        try:
            block = self._node._call("getblock", [block_hash, 1])
        except NodeRpcError:
            logger.exception("ChainListener: getblock failed for %s", block_hash)
            return

        height = int(block.get("height", 0))
        self._bus.publish(
            "chain.block.new",
            {"height": height, "block_hash": block_hash},
        )

        # Drive confirmations through the per-tx path, but only for tx we
        # already know about — we don't want to load every block tx through
        # getrawtransaction. Mempool acceptance via hashtx will have already
        # taught us about ours; this pass just refreshes confirmation_height.
        from sqlalchemy import select

        from tallykeep.models import OnChainTransactionRow

        block_txids = [str(t) for t in block.get("tx", [])]
        if not block_txids:
            return

        with self._session_scope() as session:
            ours = session.execute(
                select(OnChainTransactionRow.txid).where(
                    OnChainTransactionRow.txid.in_(block_txids)
                )
            ).scalars().all()

        for txid in ours:
            try:
                self._handle_tx(txid, confirmation_height=height)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "ChainListener: failed to confirm tx %s in block %d",
                    txid,
                    height,
                )

    # --- events -------------------------------------------------------------

    def _emit_tx_events(self, result: TxProcessingResult) -> None:
        if (
            not result.discovered_utxo_ids
            and not result.spent_utxo_ids
            and not result.new_ledger_entry_ids
            and result.is_new is False
        ):
            # Nothing actually changed — no point shouting on the bus.
            return

        descriptor_ids = [str(d) for d in result.affected_descriptor_ids]
        holding_ids = [str(h) for h in result.affected_holding_ids]

        if result.confirmation_height is None:
            self._bus.publish(
                "chain.tx.mempool",
                {
                    "txid": result.txid,
                    "affected_descriptor_ids": descriptor_ids,
                    "affected_holding_ids": holding_ids,
                },
            )
        else:
            self._bus.publish(
                "chain.tx.confirmed",
                {
                    "txid": result.txid,
                    "height": result.confirmation_height,
                    "affected_descriptor_ids": descriptor_ids,
                    "affected_holding_ids": holding_ids,
                },
            )

        # Per-utxo events — small payloads so the SSE bridge can route them by
        # holding without re-querying.
        with self._session_scope() as session:
            from sqlalchemy import select

            from tallykeep.models import UTXORow

            for utxo_id in result.discovered_utxo_ids:
                row = session.get(UTXORow, utxo_id)
                if row is None:
                    continue
                holding_id = self._lookup_holding_id(session, row.descriptor_id)
                self._bus.publish(
                    "holding.utxo.received",
                    {
                        "holding_id": str(holding_id) if holding_id else None,
                        "descriptor_id": str(row.descriptor_id),
                        "utxo_id": str(row.id),
                        "value_sats": int(row.value_sats),
                    },
                )

            for utxo_id in result.spent_utxo_ids:
                row = session.get(UTXORow, utxo_id)
                if row is None:
                    continue
                holding_id = self._lookup_holding_id(session, row.descriptor_id)
                self._bus.publish(
                    "holding.utxo.spent",
                    {
                        "holding_id": str(holding_id) if holding_id else None,
                        "descriptor_id": str(row.descriptor_id),
                        "utxo_id": str(row.id),
                    },
                )

        for entry_id in result.new_ledger_entry_ids:
            self._bus.publish(
                "ledger_entry.requires_categorization",
                {"ledger_entry_id": str(entry_id)},
            )

    def _link_payment_request_if_any(
        self, session: Session, result: TxProcessingResult
    ) -> dict | None:
        """Spec module 06 step 7: when a confirmed tx matches a known
        PaymentRequest's `broadcast_txid`, flip status to CONFIRMED and
        link `resulting_ledger_entry_id` to the LedgerEntry created for
        this tx.

        Only fires when the tx confirmed (mempool acceptance doesn't
        promote a PaymentRequest); also requires the listener to have
        produced exactly one new LedgerEntry — outgoing payments
        always touch a single source holding so this is the common
        case.
        """
        if result.confirmation_height is None:
            return None

        from tallykeep.domain.enums import LedgerEntrySource, PaymentStatus
        from tallykeep.repositories import (
            ledger_entry as ledger_repo,
            payment_request as pr_repo,
        )

        if not result.new_ledger_entry_ids:
            # The tx may already have been processed via the mempool
            # path; look up the existing entry by (source, source_ref).
            existing = ledger_repo.get_by_source(
                session,
                LedgerEntrySource.ONCHAIN_TRANSACTION,
                result.txid,
            )
            ledger_entry_id = existing.id if existing is not None else None
        else:
            ledger_entry_id = result.new_ledger_entry_ids[0]

        if ledger_entry_id is None:
            return None

        pr = pr_repo.get_by_broadcast_txid(session, result.txid)
        if pr is None:
            return None
        # Only flip from BROADCAST → CONFIRMED. Anything else (already
        # confirmed, cancelled, etc.) is a no-op.
        if pr.status != PaymentStatus.BROADCAST:
            return None

        updated = pr_repo.mark_confirmed(
            session,
            pr.id,
            resulting_ledger_entry_id=ledger_entry_id,
        )
        if updated is None:  # pragma: no cover
            return None

        # If this PaymentRequest was created by the SweepEngine, complete
        # the linked SweepExecution now.
        if pr.sweep_execution_id is not None:
            from datetime import UTC, datetime as _dt

            from tallykeep.domain.enums import SweepExecutionStatus
            from tallykeep.repositories import sweep_execution as se_repo

            execution = se_repo.get(session, pr.sweep_execution_id)
            if execution is not None and execution.status not in (
                SweepExecutionStatus.COMPLETED,
                SweepExecutionStatus.FAILED,
                SweepExecutionStatus.CANCELLED,
            ):
                se_repo.update_status(
                    session,
                    execution.id,
                    status=SweepExecutionStatus.COMPLETED,
                    confirmed_txid=result.txid,
                    completed_at=_dt.now(UTC),
                )
                logger.info(
                    "ChainListener: sweep execution %s completed via PaymentRequest %s",
                    execution.id, pr.id,
                )

        return {
            "id": str(updated.id),
            "txid": result.txid,
            "height": result.confirmation_height,
            "ledger_entry_id": str(ledger_entry_id),
        }

    def _link_sweep_execution_if_any(
        self, session: Session, result: TxProcessingResult
    ) -> dict | None:
        """When a confirmed tx matches a SweepExecution's expected_txid,
        mark the execution COMPLETED."""
        if result.confirmation_height is None:
            return None

        from datetime import UTC, datetime

        from tallykeep.domain.enums import SweepExecutionStatus
        from tallykeep.repositories import sweep_execution as se_repo

        execution = se_repo.get_by_expected_txid(session, result.txid)
        if execution is None:
            return None
        if execution.status != SweepExecutionStatus.ONCHAIN_PENDING:
            return None

        now = datetime.now(UTC)
        se_repo.update_status(
            session,
            execution.id,
            status=SweepExecutionStatus.COMPLETED,
            confirmed_txid=result.txid,
            completed_at=now,
        )
        logger.info(
            "ChainListener: sweep execution %s completed via txid %s at height %d",
            execution.id, result.txid, result.confirmation_height,
        )
        return {
            "execution_id": str(execution.id),
            "txid": result.txid,
            "height": result.confirmation_height,
        }

    def _link_invoice_if_any(
        self,
        session: Session,
        result: TxProcessingResult,
        decoded: dict,
    ) -> dict | None:
        """Spec module 06 step 2 of the Invoice flow: when an output of the
        observed tx pays an address reserved by an OPEN Invoice, mark the
        Invoice paid (or overpaid) and link the resulting LedgerEntry.

        Mempool acceptance is enough to consider the invoice paid; we
        don't wait for confirmation. The user can see "Paid (unconfirmed)"
        in the UI and the chain listener will refresh confirmation status
        on the next block via the regular UTXO confirmation_height update.
        """
        if not result.discovered_utxo_ids and not result.new_ledger_entry_ids:
            return None

        from tallykeep.domain.enums import LedgerEntrySource
        from tallykeep.repositories import (
            invoice as invoice_repo,
            ledger_entry as ledger_repo,
        )

        # Walk every output looking for one of OUR addresses that's locked
        # by an open invoice.
        vouts = decoded.get("vout", []) or []
        for raw_out in vouts:
            if not isinstance(raw_out, dict):
                continue
            spk = raw_out.get("scriptPubKey") or {}
            address = spk.get("address") if isinstance(spk, dict) else None
            if not isinstance(address, str) or not address:
                continue

            invoice = invoice_repo.get_open_by_address(session, address)
            if invoice is None:
                continue

            ledger_entry = ledger_repo.get_by_source(
                session,
                LedgerEntrySource.ONCHAIN_TRANSACTION,
                result.txid,
            )
            if ledger_entry is None:
                continue

            value_btc = raw_out.get("value")
            if value_btc is None:
                continue
            from tallykeep.services.chain_processing_service import _btc_to_sats

            value_sats = _btc_to_sats(value_btc)
            overpaid = (
                invoice.amount_sats is not None
                and value_sats > invoice.amount_sats
            )
            updated = invoice_repo.mark_paid(
                session,
                invoice.id,
                resulting_ledger_entry_id=ledger_entry.id,
                overpaid=overpaid,
            )
            if updated is None:  # pragma: no cover
                continue
            return {
                "id": str(updated.id),
                "txid": result.txid,
                "ledger_entry_id": str(ledger_entry.id),
                "amount_sats": value_sats,
                "overpaid": overpaid,
            }
        return None

    def _cached_fee_rate(self) -> float:
        """estimatesmartfee response cached for `_fee_rate_ttl_seconds`."""
        import time as _time

        now = _time.time()
        if (
            self._fee_rate_cache is not None
            and now - self._fee_rate_cache[0] < self._fee_rate_ttl_seconds
        ):
            return self._fee_rate_cache[1]
        rate = estimate_fee_rate_sat_per_vbyte(self._node)
        self._fee_rate_cache = (now, rate)
        return rate

    @staticmethod
    def _lookup_holding_id(session: Session, descriptor_id: UUID) -> UUID | None:
        from tallykeep.models import DescriptorRow

        row = session.get(DescriptorRow, descriptor_id)
        return row.holding_id if row is not None else None

    # --- session helper -----------------------------------------------------

    def _session_scope(self) -> Any:
        """Tiny context manager around a session.

        Defined inline (not @contextmanager-decorated module function) so the
        listener owns the lifecycle — important because the worker may run
        many listeners concurrently in v2.
        """
        factory = self._session_factory

        class _Scope:
            def __enter__(self) -> Session:
                self._session = factory()
                return self._session

            def __exit__(self, *exc_info: object) -> None:
                self._session.close()

        return _Scope()


__all__ = ["ChainListener"]
