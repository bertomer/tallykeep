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

        with self._session_scope() as session:
            result = self._processor.process_decoded_transaction(
                session,
                decoded,
                confirmation_height=actual_height,
                block_time=block_time,
            )
            session.commit()

        # Emit events outside the session so a slow Redis publish never holds
        # a transaction open.
        self._emit_tx_events(result)

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
