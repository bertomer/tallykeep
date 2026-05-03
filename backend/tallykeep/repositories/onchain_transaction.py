"""onchain_transaction repository.

Spec module 03: stored once per txid regardless of how many of our Holdings the
tx touches. Inserts are upsert-style — if we re-import the same txid (e.g. on a
re-scan or after a mempool→confirmed transition), the row is updated, not
duplicated.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from tallykeep.domain.ledger_entry import OnChainTransaction
from tallykeep.models import OnChainTransactionRow


def _row_to_domain(row: OnChainTransactionRow) -> OnChainTransaction:
    return OnChainTransaction(
        txid=row.txid,
        raw_hex=row.raw_hex,
        confirmation_height=row.confirmation_height,
        block_time=row.block_time,
        first_seen_at=row.first_seen_at,
        fee_sats=row.fee_sats,
        size_vbytes=row.size_vbytes,
        is_coinjoin_suspected=row.is_coinjoin_suspected,
    )


def get(session: Session, txid: str) -> OnChainTransaction | None:
    row = session.get(OnChainTransactionRow, txid)
    return _row_to_domain(row) if row is not None else None


def upsert(
    session: Session,
    *,
    txid: str,
    raw_hex: str | None = None,
    confirmation_height: int | None = None,
    block_time: datetime | None = None,
    fee_sats: int | None = None,
    size_vbytes: int | None = None,
    is_coinjoin_suspected: bool | None = None,
) -> OnChainTransaction:
    """Insert a new row or update an existing one.

    Only fields explicitly passed (non-None) are written; this lets us layer
    additional information across imports — e.g. an initial mempool import
    leaves `confirmation_height` empty, and a later confirmation import fills
    it in without overwriting `first_seen_at`.
    """
    row = session.get(OnChainTransactionRow, txid)
    if row is None:
        row = OnChainTransactionRow(
            txid=txid,
            raw_hex=raw_hex,
            confirmation_height=confirmation_height,
            block_time=block_time,
            fee_sats=fee_sats,
            size_vbytes=size_vbytes,
            is_coinjoin_suspected=bool(is_coinjoin_suspected) if is_coinjoin_suspected is not None else False,
        )
        session.add(row)
    else:
        if raw_hex is not None:
            row.raw_hex = raw_hex
        if confirmation_height is not None:
            row.confirmation_height = confirmation_height
        if block_time is not None:
            row.block_time = block_time
        if fee_sats is not None:
            row.fee_sats = fee_sats
        if size_vbytes is not None:
            row.size_vbytes = size_vbytes
        if is_coinjoin_suspected is not None:
            row.is_coinjoin_suspected = is_coinjoin_suspected
    return _row_to_domain(row)


__all__ = ["get", "upsert"]
