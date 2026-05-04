"""ChainProcessingService — turn one bitcoind transaction into domain effects.

Spec module 05 (Incremental scan): for each tx the ChainListener observes via
ZMQ, we need to:

  1. Persist or refresh the `onchain_transaction` row.
  2. Mark every input that consumes one of our UTXOs as `is_spent=True`.
  3. Discover every output that pays one of our addresses, persist a UTXO row,
     and (if new) create a LedgerEntry per touched holding.
  4. Determine `direction`: INCOMING / OUTGOING / INTERNAL based on which side
     of the transaction the user owns.

This service is callable from:
  - the ChainListener (M5.3) for live tx (mempool + confirmed)
  - tests, by handing it a hand-built decoded-tx dict
  - future re-import / reconciliation flows

It deliberately does *not* talk to the event bus directly — emitting events is
the listener's responsibility, since the listener decides the topic
(`chain.tx.mempool` vs `chain.tx.confirmed`) based on confirmation state. The
service returns a `TxProcessingResult` describing what changed; the listener
turns that into events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import Direction, LedgerEntrySource
from tallykeep.domain.ledger_entry import (
    LedgerEntry,
    LedgerEntryHoldingLink,
)
from tallykeep.models import (
    AddressRow,
    DescriptorRow,
    LedgerEntryHoldingLinkRow,
    LedgerEntryRow,
    UTXORow,
)
from tallykeep.repositories import (
    ledger_entry as ledger_repo,
    onchain_transaction as onchain_repo,
)


@dataclass(frozen=True)
class _DiscoveredOutput:
    """One vout that pays one of our watched addresses."""

    vout: int
    value_sats: int
    address: str
    address_id: UUID
    descriptor_id: UUID
    holding_id: UUID


@dataclass
class TxProcessingResult:
    """What happened when the service handled one decoded transaction."""

    txid: str
    confirmation_height: int | None
    is_new: bool                    # the onchain_transaction row was just created
    spent_utxo_ids: list[UUID] = field(default_factory=list)
    discovered_utxo_ids: list[UUID] = field(default_factory=list)
    new_ledger_entry_ids: list[UUID] = field(default_factory=list)
    affected_holding_ids: list[UUID] = field(default_factory=list)
    affected_descriptor_ids: list[UUID] = field(default_factory=list)
    direction: Direction | None = None
    net_amount_sats: int = 0


class ChainProcessingService:
    """Stateless processor — all state lives in the SQLAlchemy session.

    A single instance is safe to share across worker threads provided each
    thread brings its own session.
    """

    def process_decoded_transaction(
        self,
        session: Session,
        decoded: dict[str, object],
        *,
        confirmation_height: int | None,
        block_time: datetime | None = None,
    ) -> TxProcessingResult:
        """Apply effects of one tx (decoded as bitcoind's getrawtransaction returns).

        `decoded` shape (the relevant subset):
          {
            "txid": str,
            "hex": str,                      # raw serialized tx
            "vin":  [{"txid": str, "vout": int}, ...],
            "vout": [
              {"value": float, "n": int,
               "scriptPubKey": {"address": str, ...}},
              ...
            ],
          }

        Caller passes `confirmation_height=None` for mempool tx and the block
        height (int >= 0) for confirmed tx. Coinbase inputs (no prevout) are
        ignored when matching against our UTXO records.
        """
        txid = str(decoded["txid"])
        raw_hex = str(decoded.get("hex", "")) or None

        # 1) Probe whether the tx touches us at all before persisting anything.
        #    The chain listener fires for every mempool / confirmed tx — most
        #    don't concern us (coinbase miners, other people's payments). We
        #    short-circuit those without leaving a row in onchain_transaction.
        spent_input_value_sats, spent_utxo_ids, spent_descriptor_ids, spent_holding_ids = (
            self._mark_inputs_spent(session, decoded.get("vin", []), spending_txid=txid)
        )
        discovered = self._discover_outputs(session, decoded.get("vout", []))

        if not spent_utxo_ids and not discovered:
            # No watched address either side. The session may already hold
            # `_mark_inputs_spent`-flushed updates for UTXOs we've spent — but
            # if `spent_utxo_ids` is empty, none of those updates landed, so
            # rolling back nothing is safe. Return a no-op result.
            return TxProcessingResult(
                txid=txid,
                confirmation_height=confirmation_height,
                is_new=False,
            )

        # 2) We touch this tx — persist / refresh the onchain_transaction row.
        existing_tx = onchain_repo.get(session, txid)
        is_new_tx = existing_tx is None

        onchain_repo.upsert(
            session,
            txid=txid,
            raw_hex=raw_hex,
            confirmation_height=confirmation_height,
            block_time=block_time,
        )

        discovered_utxo_ids: list[UUID] = []
        new_ledger_entry_ids: list[UUID] = []
        affected_holdings: set[UUID] = set(spent_holding_ids)
        affected_descriptors: set[UUID] = set(spent_descriptor_ids)
        received_value_per_holding: dict[UUID, int] = {}

        for found in discovered:
            affected_holdings.add(found.holding_id)
            affected_descriptors.add(found.descriptor_id)
            received_value_per_holding[found.holding_id] = (
                received_value_per_holding.get(found.holding_id, 0) + found.value_sats
            )

            existing_utxo_row = session.execute(
                select(UTXORow).where(
                    UTXORow.txid == txid, UTXORow.vout == found.vout
                )
            ).scalar_one_or_none()
            if existing_utxo_row is None:
                utxo_id = uuid4()
                session.add(
                    UTXORow(
                        id=utxo_id,
                        descriptor_id=found.descriptor_id,
                        address_id=found.address_id,
                        txid=txid,
                        vout=found.vout,
                        value_sats=found.value_sats,
                        confirmation_height=confirmation_height,
                        is_frozen=False,
                        is_spent=False,
                        spent_in_txid=None,
                        hygiene_flags=[],
                    )
                )
                discovered_utxo_ids.append(utxo_id)
            else:
                # Already known — just refresh confirmation height if we just
                # confirmed a previously-unconfirmed UTXO.
                if (
                    confirmation_height is not None
                    and existing_utxo_row.confirmation_height is None
                ):
                    existing_utxo_row.confirmation_height = confirmation_height

        # 4) Compute direction + net amount, then create one ledger entry per
        #    touched holding when not already linked to this tx.
        direction = self._infer_direction(
            spent_value=spent_input_value_sats,
            received_per_holding=received_value_per_holding,
            num_holdings_touched_by_inputs=len(spent_holding_ids),
            num_holdings_touched_by_outputs=len(received_value_per_holding),
        )

        net_amount_sats = sum(received_value_per_holding.values()) - spent_input_value_sats
        timestamp = block_time or datetime.now(UTC)

        # We create one LedgerEntry per holding the tx touches, with a per-holding
        # net-amount that reflects only that holding's slice of the activity.
        for holding_id in affected_holdings:
            if self._already_linked(session, txid, holding_id):
                continue
            holding_received = received_value_per_holding.get(holding_id, 0)
            holding_spent = self._holding_input_value(
                session, decoded.get("vin", []), holding_id
            )
            holding_net = holding_received - holding_spent

            # Skip pure no-ops (shouldn't happen, but guards against degenerate
            # input lists where a UTXO got marked spent out of band).
            if holding_received == 0 and holding_spent == 0:
                continue

            entry_id = uuid4()
            entry = LedgerEntry(
                id=entry_id,
                direction=direction,
                net_amount_sats=holding_net,
                fee_sats=None,
                timestamp=timestamp,
                source=LedgerEntrySource.ONCHAIN_TRANSACTION,
                source_reference=txid,
                category=None,
                counterparty_label=None,
                note=None,
                suggested_category=None,
                categorized_at=None,
                created_at=datetime.now(UTC),
            )
            ledger_repo.insert(
                session,
                entry,
                holding_links=[
                    LedgerEntryHoldingLink(
                        ledger_entry_id=entry_id,
                        holding_id=holding_id,
                        holding_amount_sats=holding_net,
                    )
                ],
            )
            new_ledger_entry_ids.append(entry_id)

        return TxProcessingResult(
            txid=txid,
            confirmation_height=confirmation_height,
            is_new=is_new_tx,
            spent_utxo_ids=spent_utxo_ids,
            discovered_utxo_ids=discovered_utxo_ids,
            new_ledger_entry_ids=new_ledger_entry_ids,
            affected_holding_ids=sorted(affected_holdings, key=str),
            affected_descriptor_ids=sorted(affected_descriptors, key=str),
            direction=direction,
            net_amount_sats=net_amount_sats,
        )

    # --- internals ----------------------------------------------------------

    def _mark_inputs_spent(
        self,
        session: Session,
        vin: list[object],
        *,
        spending_txid: str,
    ) -> tuple[int, list[UUID], set[UUID], set[UUID]]:
        """Mark every previously-known UTXO that this tx consumes.

        Returns: (total_value_consumed_from_us, spent_utxo_ids, descriptor_ids,
        holding_ids).
        """
        spent_value = 0
        spent_ids: list[UUID] = []
        descriptors: set[UUID] = set()
        holdings: set[UUID] = set()

        for raw_input in vin:
            if not isinstance(raw_input, dict):
                continue
            prev_txid = raw_input.get("txid")
            prev_vout = raw_input.get("vout")
            if prev_txid is None or prev_vout is None:
                # Coinbase tx — has no `txid`/`vout`, just `coinbase`.
                continue
            row = session.execute(
                select(UTXORow).where(
                    UTXORow.txid == str(prev_txid),
                    UTXORow.vout == int(prev_vout),
                )
            ).scalar_one_or_none()
            if row is None:
                continue
            if not row.is_spent:
                row.is_spent = True
                row.spent_in_txid = spending_txid
            spent_value += int(row.value_sats)
            spent_ids.append(row.id)
            descriptors.add(row.descriptor_id)
            descriptor_row = session.get(DescriptorRow, row.descriptor_id)
            if descriptor_row is not None:
                holdings.add(descriptor_row.holding_id)

        return spent_value, spent_ids, descriptors, holdings

    def _discover_outputs(
        self, session: Session, vout: list[object]
    ) -> list[_DiscoveredOutput]:
        """For each tx output, look up our `address` row by string match.

        Returns one _DiscoveredOutput per output that pays a watched address.
        Outputs to addresses we don't watch are silently skipped — those exist
        even on transactions we care about (changes back to a counterparty,
        OP_RETURN data carriers, etc.).
        """
        if not vout:
            return []

        # Build a (address_string -> [(value_sats, vout_index)]) view of the tx.
        per_address: dict[str, list[tuple[int, int]]] = {}
        for output in vout:
            if not isinstance(output, dict):
                continue
            value_btc = output.get("value")
            if value_btc is None:
                continue
            n = int(output.get("n", 0))
            spk = output.get("scriptPubKey") or {}
            if not isinstance(spk, dict):
                continue
            address = spk.get("address")
            if not isinstance(address, str) or not address:
                # Multi-address legacy outputs use `addresses: [...]`. We don't
                # see those in v1 (P2WPKH single-recipient only), but be safe.
                continue
            value_sats = _btc_to_sats(value_btc)
            per_address.setdefault(address, []).append((value_sats, n))

        if not per_address:
            return []

        rows = session.execute(
            select(AddressRow).where(AddressRow.address.in_(list(per_address.keys())))
        ).scalars().all()

        # Resolve the descriptor.holding_id for each address row in one round-trip.
        descriptor_ids = {row.descriptor_id for row in rows}
        descriptor_holdings: dict[UUID, UUID] = {}
        if descriptor_ids:
            for d_row in session.execute(
                select(DescriptorRow).where(
                    DescriptorRow.id.in_(list(descriptor_ids))
                )
            ).scalars():
                descriptor_holdings[d_row.id] = d_row.holding_id

        discovered: list[_DiscoveredOutput] = []
        for row in rows:
            for value_sats, vout_index in per_address.get(row.address, []):
                holding_id = descriptor_holdings.get(row.descriptor_id)
                if holding_id is None:
                    continue
                discovered.append(
                    _DiscoveredOutput(
                        vout=vout_index,
                        value_sats=value_sats,
                        address=row.address,
                        address_id=row.id,
                        descriptor_id=row.descriptor_id,
                        holding_id=holding_id,
                    )
                )
        return discovered

    def _infer_direction(
        self,
        *,
        spent_value: int,
        received_per_holding: dict[UUID, int],
        num_holdings_touched_by_inputs: int,
        num_holdings_touched_by_outputs: int,
    ) -> Direction:
        """Spec module 05:
            INCOMING if net effect on user's Holdings is positive
            OUTGOING if negative
            INTERNAL if both inputs and outputs are entirely user-owned
        """
        received_total = sum(received_per_holding.values())
        if (
            spent_value > 0
            and received_total > 0
            and num_holdings_touched_by_inputs > 0
            and num_holdings_touched_by_outputs > 0
        ):
            return Direction.INTERNAL
        if received_total >= spent_value:
            return Direction.INCOMING
        return Direction.OUTGOING

    def _already_linked(
        self, session: Session, txid: str, holding_id: UUID
    ) -> bool:
        """True when an entry for this (txid, holding) already exists.

        We dedupe by `(source, source_reference)` plus the holding-link row so a
        mempool entry that later confirms doesn't double up.
        """
        row = session.execute(
            select(LedgerEntryHoldingLinkRow)
            .join(
                LedgerEntryRow,
                LedgerEntryRow.id == LedgerEntryHoldingLinkRow.ledger_entry_id,
            )
            .where(
                LedgerEntryRow.source == LedgerEntrySource.ONCHAIN_TRANSACTION.value,
                LedgerEntryRow.source_reference == txid,
                LedgerEntryHoldingLinkRow.holding_id == holding_id,
            )
        ).scalar_one_or_none()
        return row is not None

    def _holding_input_value(
        self, session: Session, vin: list[object], holding_id: UUID
    ) -> int:
        """Sum of input values from this tx that come from `holding_id`'s UTXOs.

        Re-reads UTXO rows post-spend; this is fine because mark_inputs_spent
        has already flushed them as is_spent=True but `value_sats` doesn't
        change.
        """
        total = 0
        for raw_input in vin:
            if not isinstance(raw_input, dict):
                continue
            prev_txid = raw_input.get("txid")
            prev_vout = raw_input.get("vout")
            if prev_txid is None or prev_vout is None:
                continue
            row = session.execute(
                select(UTXORow).where(
                    UTXORow.txid == str(prev_txid),
                    UTXORow.vout == int(prev_vout),
                )
            ).scalar_one_or_none()
            if row is None:
                continue
            descriptor_row = session.get(DescriptorRow, row.descriptor_id)
            if descriptor_row is None:
                continue
            if descriptor_row.holding_id == holding_id:
                total += int(row.value_sats)
        return total


def _btc_to_sats(btc: object) -> int:
    """Same algorithm as NodeAdapter._btc_to_sats — duplicated to avoid an
    import cycle (the chain processor must not pull in the RPC adapter)."""
    text = f"{float(btc):.8f}"  # type: ignore[arg-type]
    integer, _, fractional = text.partition(".")
    fractional = (fractional + "00000000")[:8]
    sign = -1 if integer.startswith("-") else 1
    return sign * (abs(int(integer)) * 100_000_000 + int(fractional))


__all__ = ["ChainProcessingService", "TxProcessingResult"]
