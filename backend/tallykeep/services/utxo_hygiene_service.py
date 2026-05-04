"""UTXO hygiene flag computation — spec module 05.

Each flag is computed at UTXO detection time. The spec also calls out
recomputation of `DUST` on fee-rate changes; that's a v2 scheduler concern
(documented in CONTEXT.md), so v1 captures fee-rate-at-detection and stops
there.

The four flags:

  - ADDRESS_REUSED:
      An address has received funds in more than one independent tx batch.
      Independent = not the same single transaction. Two outputs to the
      same address from one tx is not reuse; two outputs from two
      different txs is.

  - DUST:
      `value_sats < 3 * fee_rate_sat_per_vbyte * typical_input_size_vbytes`.
      The factor of 3 keeps the threshold conservative — a UTXO is only
      "dust" when consolidating it would cost more than 3x its value. The
      typical input size depends on `AddressType`.

  - ROUND_NUMBER:
      Output value is a multiple of 100k sats (0.001 BTC) or 1M sats
      (0.01 BTC). Fiat-denominated detection requires a price oracle,
      which v1 doesn't ship; documented as a v2 enhancement.

  - SUSPECTED_CONSOLIDATION:
      The producing tx has at least 5 inputs and at most 2 outputs, and
      most inputs (> 50%) are watched by us. Consolidation links many
      prior UTXOs together for the chain analyst, so the resulting UTXO
      is flagged.

The service is a stateless façade — caller passes the DB session and the
context (decoded tx, fee rate, address row). We don't import the chain
processor or the listener here; this lets either pre-existing pathway
(initial scan, live listener) plug in by calling the same function.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.adapters.node_adapter import NodeAdapter, NodeError
from tallykeep.domain.enums import AddressType, HygieneFlag
from tallykeep.models import AddressRow, UTXORow


logger = logging.getLogger(__name__)


# Per-address-type estimated vsize of one spending input. Spec module 05.
_TYPICAL_INPUT_VBYTES: dict[AddressType, float] = {
    AddressType.LEGACY: 148.0,
    AddressType.NESTED_SEGWIT: 91.0,   # midpoint of common P2SH-P2WPKH
    AddressType.NATIVE_SEGWIT: 68.0,
    AddressType.TAPROOT: 57.5,
}

# v1 fallback fee rate when bitcoind's estimatesmartfee returns nothing
# usable (regtest is the typical case). Conservative enough that small UTXOs
# get flagged DUST even on a quiet network.
_FALLBACK_FEE_RATE_SAT_PER_VBYTE = 10.0

# Default DUST safety multiplier — a UTXO is dust when spending it would cost
# >= 1/3 of its value. The spec uses 3*; we mirror.
_DUST_FACTOR = 3.0


@dataclass(frozen=True)
class HygieneContext:
    """All the per-tx data the hygiene checks need.

    `decoded_tx` is the bitcoind getrawtransaction(verbose=true) shape, or
    None when re-running flag computation against an already-persisted
    UTXO and the original tx isn't being passed in (we still get
    ADDRESS_REUSED + DUST in that case, since they don't depend on tx
    structure).
    """

    decoded_tx: dict[str, Any] | None = None
    address_type: AddressType = AddressType.NATIVE_SEGWIT
    fee_rate_sat_per_vbyte: float = _FALLBACK_FEE_RATE_SAT_PER_VBYTE


def estimate_fee_rate_sat_per_vbyte(node: NodeAdapter | None) -> float:
    """Best-effort fee-rate estimate.

    bitcoind's `estimatesmartfee target=6` returns a `feerate` field in
    BTC/kvB when the node has enough history; on regtest or a freshly
    started node it returns errors. Convert to sat/vB and fall back to
    `_FALLBACK_FEE_RATE_SAT_PER_VBYTE` on any failure.
    """
    if node is None:
        return _FALLBACK_FEE_RATE_SAT_PER_VBYTE
    try:
        result = node.estimate_smart_fee(6)
    except NodeError:
        return _FALLBACK_FEE_RATE_SAT_PER_VBYTE
    feerate_btc_per_kvb = result.get("feerate")
    if feerate_btc_per_kvb is None or float(feerate_btc_per_kvb) <= 0:
        return _FALLBACK_FEE_RATE_SAT_PER_VBYTE
    # 1 BTC/kvB = 100_000 sat/vB.
    return float(feerate_btc_per_kvb) * 100_000


def compute_flags(
    session: Session,
    *,
    utxo: UTXORow,
    context: HygieneContext,
) -> list[HygieneFlag]:
    """Return the hygiene flags applicable to `utxo`.

    Reads sibling UTXOs at the same address (ADDRESS_REUSED) and the
    decoded tx from `context` (ROUND_NUMBER, SUSPECTED_CONSOLIDATION). The
    function does not write — callers are responsible for `utxo.hygiene_flags = ...`
    and any address-row updates.
    """
    flags: list[HygieneFlag] = []

    if _is_address_reused(session, utxo):
        flags.append(HygieneFlag.ADDRESS_REUSED)

    if _is_dust(utxo, context):
        flags.append(HygieneFlag.DUST)

    if context.decoded_tx is not None:
        if _is_round_number(int(utxo.value_sats)):
            flags.append(HygieneFlag.ROUND_NUMBER)
        if _is_suspected_consolidation(session, context.decoded_tx):
            flags.append(HygieneFlag.SUSPECTED_CONSOLIDATION)

    return flags


def apply_flags_and_propagate_reuse(
    session: Session,
    *,
    utxo: UTXORow,
    context: HygieneContext,
) -> list[HygieneFlag]:
    """One-shot helper used by the scan / listener pathways.

    1. Computes flags for the new UTXO and writes them to `utxo.hygiene_flags`.
    2. If ADDRESS_REUSED applies, retro-flags any prior unspent UTXOs at
       the same address (they were not "reused" the moment they landed
       but are now), and sets `address.is_reused = True`.

    Returns the list of flags applied to the new UTXO.
    """
    flags = compute_flags(session, utxo=utxo, context=context)
    utxo.hygiene_flags = [f.value for f in flags]

    if HygieneFlag.ADDRESS_REUSED in flags:
        _propagate_address_reuse(session, utxo)

    return flags


# --- internals ------------------------------------------------------------


def _is_address_reused(session: Session, utxo: UTXORow) -> bool:
    """True iff the address has received funds in another tx besides this one.

    "Independent transaction batch" per spec means a different txid. Two
    outputs to the same address inside one tx don't count.
    """
    distinct_txids = session.execute(
        select(UTXORow.txid)
        .where(UTXORow.address_id == utxo.address_id)
        .distinct()
    ).scalars().all()
    other_txids = {t for t in distinct_txids if t != utxo.txid}
    return len(other_txids) >= 1


def _is_dust(utxo: UTXORow, context: HygieneContext) -> bool:
    typical_vbytes = _TYPICAL_INPUT_VBYTES.get(
        context.address_type, _TYPICAL_INPUT_VBYTES[AddressType.NATIVE_SEGWIT]
    )
    threshold_sats = _DUST_FACTOR * context.fee_rate_sat_per_vbyte * typical_vbytes
    return float(utxo.value_sats) < threshold_sats


def _is_round_number(value_sats: int) -> bool:
    """Heuristic match for round-number sat values.

    True for any positive multiple of 100_000 sats (0.001 BTC) — that's
    suggestive of a fiat-denominated payment at common round-number BTC
    prices. Multiples of 1_000_000 are a strict subset and trip this same
    rule.

    We deliberately don't flag values < 100_000 (sub-mBTC) to avoid
    flagging dust-adjacent everyday spending.
    """
    return value_sats >= 100_000 and (value_sats % 100_000 == 0)


def _is_suspected_consolidation(session: Session, decoded_tx: dict[str, Any]) -> bool:
    """Spec: ≥5 inputs, ≤2 outputs, majority of inputs from our addresses."""
    vin = decoded_tx.get("vin", []) or []
    vout = decoded_tx.get("vout", []) or []
    if len(vin) < 5 or len(vout) > 2:
        return False

    # Count how many inputs were watched by us. We can decide from the
    # prevout outpoint by checking our utxo table (rows are kept after
    # spend; only `is_spent` toggles, so the lookup still finds them).
    ours = 0
    for raw_input in vin:
        if not isinstance(raw_input, dict):
            continue
        prev_txid = raw_input.get("txid")
        prev_vout = raw_input.get("vout")
        if prev_txid is None or prev_vout is None:
            continue  # coinbase
        row = session.execute(
            select(UTXORow).where(
                UTXORow.txid == str(prev_txid),
                UTXORow.vout == int(prev_vout),
            )
        ).scalar_one_or_none()
        if row is not None:
            ours += 1

    return ours > len(vin) / 2


def _propagate_address_reuse(session: Session, new_utxo: UTXORow) -> None:
    """Retro-flag every prior UTXO at the same address with ADDRESS_REUSED.

    Also sets the corresponding `address.is_reused = True`. Any UTXO that
    already has the flag is left alone (idempotent).
    """
    sibling_rows = session.execute(
        select(UTXORow).where(
            UTXORow.address_id == new_utxo.address_id,
            UTXORow.id != new_utxo.id,
        )
    ).scalars().all()
    for row in sibling_rows:
        existing = list(row.hygiene_flags or [])
        if HygieneFlag.ADDRESS_REUSED.value not in existing:
            # Reassign so SQLAlchemy detects the JSONB change. In-place
            # mutation of a JSONB list isn't picked up by the dirty
            # tracker.
            existing.append(HygieneFlag.ADDRESS_REUSED.value)
            row.hygiene_flags = existing

    address_row = session.get(AddressRow, new_utxo.address_id)
    if address_row is not None and not address_row.is_reused:
        address_row.is_reused = True


__all__ = [
    "HygieneContext",
    "apply_flags_and_propagate_reuse",
    "compute_flags",
    "estimate_fee_rate_sat_per_vbyte",
]
