"""ChainScanService — turns bitcoind's UTXO state into our domain rows.

Spec module 05 / "Initial scan (one-time, on Descriptor import)":

  1. BDK derives addresses up to gap_limit on both branches (already done by
     the holding-creation flow — addresses live in our `address` table).
  2. Ask bitcoind for UTXOs touching those addresses via `scantxoutset`.
  3. Persist UTXOs and the corresponding OnChainTransaction + LedgerEntry.

The initial scan is a *snapshot* — we record what's currently unspent and
attribute the credit to a LedgerEntry with `direction=INCOMING`. Outgoing /
internal-transfer detection requires walking inputs against our existing UTXO
records, which the live ChainListener (M5.3) does as transactions arrive.

Re-running the scan on the same descriptor is safe: UTXOs are upserted by
(txid, vout) and LedgerEntries are de-duplicated by (source, source_reference)
*scoped to the descriptor's holding*. A single tx can credit multiple
holdings (a coinjoin participant view, for instance) and we still want one
LedgerEntry per holding, not one global entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from tallykeep.adapters.node_adapter import NodeAdapter, ScanUtxo
from tallykeep.domain.descriptor import Descriptor
from tallykeep.domain.enums import (
    Direction,
    LedgerEntrySource,
)
from tallykeep.domain.ledger_entry import (
    LedgerEntry,
    LedgerEntryHoldingLink,
)
from tallykeep.models import AddressRow
from tallykeep.repositories import (
    descriptor as descriptor_repo,
    ledger_entry as ledger_repo,
    onchain_transaction as onchain_repo,
    utxo as utxo_repo,
)


@dataclass
class ScanReport:
    """What changed during a scan run."""

    descriptor_id: UUID
    utxos_discovered: int
    utxos_pre_existing: int
    ledger_entries_created: int
    height_at_scan: int


class ChainScanService:
    def __init__(self, node: NodeAdapter) -> None:
        self._node = node

    def initial_scan(
        self, session: Session, descriptor: Descriptor
    ) -> ScanReport:
        """Run scantxoutset for `descriptor` and persist the result.

        Caller manages the session: this method only adds within the passed
        session, never commits. The endpoint or job runner that owns the
        session decides when to commit / rollback.

        We scan the external and change branches separately because bitcoind's
        scantxoutset does NOT populate the `address` field for descriptor
        scans — only `scriptPubKey` and `desc`. We match each unspent back to
        an `address` row via (is_change, derivation_index), pulling the index
        out of bitcoind's per-derivation `desc` annotation
        (`wpkh([fp/branch/index]pubkey)#chk`).
        """
        from sqlalchemy import select as sa_select

        address_rows = list(
            session.execute(
                sa_select(AddressRow).where(
                    AddressRow.descriptor_id == descriptor.id
                )
            ).scalars()
        )
        address_index: dict[tuple[bool, int], AddressRow] = {
            (row.is_change, row.derivation_index): row for row in address_rows
        }

        branches: list[tuple[bool, str]] = [(False, descriptor.expression)]
        if descriptor.change_expression is not None:
            branches.append((True, descriptor.change_expression))

        utxos_discovered = 0
        utxos_pre_existing = 0
        ledger_entries_created = 0
        height_at_scan = 0

        for is_change, expression in branches:
            scan_result = self._node.scan_descriptors([expression])
            height_at_scan = max(height_at_scan, scan_result.height_at_scan)

            for unspent in scan_result.utxos:
                index = _parse_derivation_index(unspent.descriptor)
                if index is None:
                    continue
                address_row = address_index.get((is_change, index))
                if address_row is None:
                    # Past our gap limit. v2 will add a manual-address
                    # registration path — see CONTEXT.md "Deferred to v2".
                    continue

                existing = utxo_repo.get_by_outpoint(
                    session, unspent.txid, unspent.vout
                )
                if existing is None:
                    new_utxo_id = uuid4()
                    utxo_repo.upsert_unspent(
                        session,
                        utxo_id=new_utxo_id,
                        descriptor_id=descriptor.id,
                        address_id=address_row.id,
                        txid=unspent.txid,
                        vout=unspent.vout,
                        value_sats=unspent.amount_sats,
                        confirmation_height=unspent.height or None,
                    )
                    utxos_discovered += 1

                    onchain_repo.upsert(
                        session,
                        txid=unspent.txid,
                        confirmation_height=unspent.height or None,
                    )

                    self._compute_and_apply_hygiene(
                        session,
                        descriptor=descriptor,
                        utxo_id=new_utxo_id,
                    )

                    self._maybe_create_ledger_entry(
                        session,
                        descriptor=descriptor,
                        txid=unspent.txid,
                        value_sats=unspent.amount_sats,
                    )
                    ledger_entries_created += 1
                else:
                    utxos_pre_existing += 1

        # Update last_scanned_height on the descriptor.
        from tallykeep.models import DescriptorRow

        descriptor_row = session.get(DescriptorRow, descriptor.id)
        if (
            descriptor_row is not None
            and height_at_scan > descriptor_row.last_scanned_height
        ):
            descriptor_row.last_scanned_height = height_at_scan

        return ScanReport(
            descriptor_id=descriptor.id,
            utxos_discovered=utxos_discovered,
            utxos_pre_existing=utxos_pre_existing,
            ledger_entries_created=ledger_entries_created,
            height_at_scan=height_at_scan,
        )

    # --- helpers --------------------------------------------------------------

    def _compute_and_apply_hygiene(
        self,
        session: Session,
        *,
        descriptor: Descriptor,
        utxo_id: UUID,
    ) -> None:
        """Compute and persist hygiene flags for a freshly-imported UTXO.

        The initial scan path doesn't have the decoded tx in hand (we only
        used `scantxoutset`), so SUSPECTED_CONSOLIDATION and ROUND_NUMBER's
        per-output context are skipped — those flag families need the full
        transaction shape, which the live listener path does have. We
        still get ADDRESS_REUSED + DUST here, which are the two with the
        highest user-actionable value.

        Fee rate uses the configured `NodeAdapter`'s estimate_smart_fee
        (with a fallback when bitcoind has no estimate, e.g. on regtest).
        """
        from tallykeep.models import UTXORow as _UTXORow
        from tallykeep.services.utxo_hygiene_service import (
            HygieneContext,
            apply_flags_and_propagate_reuse,
            estimate_fee_rate_sat_per_vbyte,
        )

        # We flush so the upsert is queryable by the ADDRESS_REUSED scan
        # which reads sibling UTXO rows at the same address.
        session.flush()
        new_row = session.get(_UTXORow, utxo_id)
        if new_row is None:  # pragma: no cover — upsert just ran
            return

        fee_rate = estimate_fee_rate_sat_per_vbyte(self._node)
        ctx = HygieneContext(
            decoded_tx=None,  # initial scan: tx-shape-derived flags skipped
            address_type=descriptor.address_type,
            fee_rate_sat_per_vbyte=fee_rate,
        )
        apply_flags_and_propagate_reuse(session, utxo=new_row, context=ctx)

    def _maybe_create_ledger_entry(
        self,
        session: Session,
        *,
        descriptor: Descriptor,
        txid: str,
        value_sats: int,
    ) -> None:
        """Create one LedgerEntry per discovered UTXO, scoped to this holding.

        The initial scan is a snapshot — every newly-discovered UTXO produces
        an INCOMING entry. The categorizer (M5.6) and the live listener
        (M5.3) refine the direction/category later when more tx context is
        available.

        Dedupe key: (source=onchain_transaction, source_reference=txid,
        link to descriptor.holding_id). If we already have an entry with the
        same source-reference linked to this holding, we don't add another.
        """
        existing = ledger_repo.get_by_source(
            session, LedgerEntrySource.ONCHAIN_TRANSACTION, txid
        )
        if existing is not None:
            from tallykeep.models import LedgerEntryHoldingLinkRow
            from sqlalchemy import select as sa_select

            already_linked = session.execute(
                sa_select(LedgerEntryHoldingLinkRow).where(
                    LedgerEntryHoldingLinkRow.ledger_entry_id == existing.id,
                    LedgerEntryHoldingLinkRow.holding_id == descriptor.holding_id,
                )
            ).scalar_one_or_none()
            if already_linked is not None:
                return  # already linked to this holding from a prior scan

        entry_id = existing.id if existing is not None else uuid4()
        if existing is None:
            entry = LedgerEntry(
                id=entry_id,
                direction=Direction.INCOMING,
                net_amount_sats=value_sats,
                fee_sats=None,
                timestamp=datetime.now(UTC),
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
                        holding_id=descriptor.holding_id,
                        holding_amount_sats=value_sats,
                    )
                ],
            )
        else:
            # Existing entry, just add the link to this holding.
            from tallykeep.models import LedgerEntryHoldingLinkRow

            session.add(
                LedgerEntryHoldingLinkRow(
                    ledger_entry_id=entry_id,
                    holding_id=descriptor.holding_id,
                    holding_amount_sats=value_sats,
                )
            )


_DESC_INDEX_PATTERN = __import__("re").compile(r"\[[^\]]*?/(\d+)\][0-9a-fA-F]+")


def _parse_derivation_index(desc: str) -> int | None:
    """Extract the leaf index from a per-derivation descriptor.

    bitcoind's scantxoutset reports per-UTXO descriptors like:
        wpkh([6834a63c/0/0]03c82ffa...)#eu5jwm9f
        wpkh([6834a63c/0/15]02ab...)#abcdwxyz

    The bracketed origin is `[fingerprint/branch/index]` (or longer when the
    descriptor has hardened-path components). We pull the trailing integer
    just before the closing bracket — that's the leaf index our `address`
    table is keyed on.

    Returns None when the descriptor doesn't look like a per-leaf form (e.g.
    the wildcard `/0/*` form for a top-level descriptor — which we don't
    expect from scantxoutset's per-UTXO output).
    """
    match = _DESC_INDEX_PATTERN.search(desc)
    if match is None:
        return None
    return int(match.group(1))


__all__ = ["ChainScanService", "ScanReport"]
