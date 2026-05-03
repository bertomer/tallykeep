"""UTXO repository.

Persists UTXOs discovered by the chain scanner. Hygiene flags compute lives in
M5.4 — for now, rows are stored with `hygiene_flags=[]`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.descriptor import UTXO
from tallykeep.domain.enums import HygieneFlag
from tallykeep.models import UTXORow


def _row_to_domain(row: UTXORow) -> UTXO:
    flags = [HygieneFlag(f) for f in (row.hygiene_flags or [])]
    return UTXO(
        id=row.id,
        descriptor_id=row.descriptor_id,
        address_id=row.address_id,
        txid=row.txid,
        vout=row.vout,
        value_sats=row.value_sats,
        confirmation_height=row.confirmation_height,
        is_frozen=row.is_frozen,
        is_spent=row.is_spent,
        spent_in_txid=row.spent_in_txid,
        hygiene_flags=flags,
        created_at=row.created_at,
    )


def get(session: Session, utxo_id: UUID) -> UTXO | None:
    row = session.get(UTXORow, utxo_id)
    return _row_to_domain(row) if row is not None else None


def get_by_outpoint(
    session: Session, txid: str, vout: int
) -> UTXO | None:
    """Look up by (txid, vout). Useful to detect re-imports from a re-scan."""
    row = session.execute(
        select(UTXORow)
        .where(UTXORow.txid == txid, UTXORow.vout == vout)
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def upsert_unspent(
    session: Session,
    *,
    utxo_id: UUID,
    descriptor_id: UUID,
    address_id: UUID,
    txid: str,
    vout: int,
    value_sats: int,
    confirmation_height: int | None,
) -> UTXO:
    """Insert a UTXO if (txid, vout) is unknown; otherwise refresh confirmation
    height. We never widen `is_spent=True` back to False — once the chain
    scanner records a UTXO as spent, only an explicit replay of the spending
    tx can mark it unspent again, and that's not a path we exercise here.
    """
    existing = session.execute(
        select(UTXORow).where(UTXORow.txid == txid, UTXORow.vout == vout)
    ).scalar_one_or_none()
    if existing is None:
        row = UTXORow(
            id=utxo_id,
            descriptor_id=descriptor_id,
            address_id=address_id,
            txid=txid,
            vout=vout,
            value_sats=value_sats,
            confirmation_height=confirmation_height,
            is_frozen=False,
            is_spent=False,
            spent_in_txid=None,
            hygiene_flags=[],
        )
        session.add(row)
        return _row_to_domain(row)

    if confirmation_height is not None and existing.confirmation_height is None:
        existing.confirmation_height = confirmation_height
    return _row_to_domain(existing)


def mark_spent(
    session: Session, txid: str, vout: int, spent_in_txid: str
) -> bool:
    """Mark a UTXO as spent. Returns True if found and updated, False otherwise."""
    row = session.execute(
        select(UTXORow).where(UTXORow.txid == txid, UTXORow.vout == vout)
    ).scalar_one_or_none()
    if row is None:
        return False
    row.is_spent = True
    row.spent_in_txid = spent_in_txid
    return True


def list_for_descriptor(
    session: Session,
    descriptor_id: UUID,
    *,
    only_unspent: bool = True,
    limit: int | None = None,
    offset: int = 0,
) -> list[UTXO]:
    stmt = select(UTXORow).where(UTXORow.descriptor_id == descriptor_id)
    if only_unspent:
        stmt = stmt.where(UTXORow.is_spent.is_(False))
    stmt = stmt.order_by(UTXORow.confirmation_height.desc().nullsfirst(), UTXORow.txid, UTXORow.vout)
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def list_filtered(
    session: Session,
    *,
    descriptor_id: UUID | None = None,
    holding_id: UUID | None = None,
    min_value_sats: int | None = None,
    is_frozen: bool | None = None,
    only_unspent: bool = True,
    limit: int = 50,
    offset: int = 0,
) -> list[UTXO]:
    """Cross-descriptor list with the filters spec module 04 documents.

    `holding_id` filters by the descriptors owned by that holding. We resolve
    that to a list of descriptor ids before the query so the index on
    `(descriptor_id, is_spent=false)` stays usable.
    """
    from tallykeep.repositories import descriptor as descriptor_repo

    stmt = select(UTXORow)
    if only_unspent:
        stmt = stmt.where(UTXORow.is_spent.is_(False))
    if descriptor_id is not None:
        stmt = stmt.where(UTXORow.descriptor_id == descriptor_id)
    if holding_id is not None:
        ids = descriptor_repo.descriptor_ids_for_holding(session, holding_id)
        if not ids:
            return []
        stmt = stmt.where(UTXORow.descriptor_id.in_(ids))
    if min_value_sats is not None:
        stmt = stmt.where(UTXORow.value_sats >= min_value_sats)
    if is_frozen is not None:
        stmt = stmt.where(UTXORow.is_frozen.is_(is_frozen))

    stmt = stmt.order_by(UTXORow.confirmation_height.desc().nullsfirst(), UTXORow.txid)
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def freeze(session: Session, utxo_id: UUID, frozen: bool) -> UTXO | None:
    row = session.get(UTXORow, utxo_id)
    if row is None:
        return None
    row.is_frozen = frozen
    return _row_to_domain(row)


def descriptor_balance_sats(session: Session, descriptor_id: UUID) -> int:
    """Sum of unspent UTXO values for a descriptor."""
    from sqlalchemy import func

    stmt = (
        select(func.coalesce(func.sum(UTXORow.value_sats), 0))
        .where(
            UTXORow.descriptor_id == descriptor_id,
            UTXORow.is_spent.is_(False),
        )
    )
    return int(session.execute(stmt).scalar_one())


__all__ = [
    "descriptor_balance_sats",
    "freeze",
    "get",
    "get_by_outpoint",
    "list_filtered",
    "list_for_descriptor",
    "mark_spent",
    "upsert_unspent",
]
