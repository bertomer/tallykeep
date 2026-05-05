"""PaymentRequest + BroadcastAttempt repositories — spec module 03 / 06.

State transitions are deliberate `update_*` calls rather than a generic
patch — every status flip carries with it a small set of related fields
(e.g. signing populates `signed_transaction_hex`; broadcasting populates
`broadcast_txid`), and pairing the field write with the status flip
keeps the audit shape coherent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import PaymentStatus, PaymentType
from tallykeep.domain.payment_request import PaymentRequest
from tallykeep.models import BroadcastAttemptRow, PaymentRequestRow


# --- domain mapping ---------------------------------------------------------


def _row_to_domain(row: PaymentRequestRow) -> PaymentRequest:
    return PaymentRequest(
        id=row.id,
        holding_id=row.holding_id,
        payment_type=PaymentType(row.payment_type),
        amount_sats=row.amount_sats,
        description=row.description,
        status=PaymentStatus(row.status),
        expires_at=row.expires_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        destination_address=row.destination_address,
        bip21_uri=row.bip21_uri,
        psbt_base64=row.psbt_base64,
        signed_transaction_hex=row.signed_transaction_hex,
        broadcast_txid=row.broadcast_txid,
        lightning_invoice=row.lightning_invoice,
        lightning_payment_hash=row.lightning_payment_hash,
        resulting_ledger_entry_id=row.resulting_ledger_entry_id,
    )


# --- queries ----------------------------------------------------------------


def get(session: Session, request_id: UUID) -> PaymentRequest | None:
    row = session.get(PaymentRequestRow, request_id)
    return _row_to_domain(row) if row is not None else None


def get_by_broadcast_txid(
    session: Session, txid: str
) -> PaymentRequest | None:
    """Used by the chain listener when a broadcast tx confirms — look up
    the PaymentRequest that owns that txid so we can flip status to
    CONFIRMED and link `resulting_ledger_entry_id`."""
    row = session.execute(
        select(PaymentRequestRow).where(PaymentRequestRow.broadcast_txid == txid)
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def list_for_holding(
    session: Session,
    holding_id: UUID,
    *,
    status: PaymentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PaymentRequest]:
    stmt = select(PaymentRequestRow).where(
        PaymentRequestRow.holding_id == holding_id
    )
    if status is not None:
        stmt = stmt.where(PaymentRequestRow.status == status.value)
    stmt = stmt.order_by(PaymentRequestRow.created_at.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def list_filtered(
    session: Session,
    *,
    holding_id: UUID | None = None,
    status: PaymentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PaymentRequest]:
    stmt = select(PaymentRequestRow)
    if holding_id is not None:
        stmt = stmt.where(PaymentRequestRow.holding_id == holding_id)
    if status is not None:
        stmt = stmt.where(PaymentRequestRow.status == status.value)
    stmt = stmt.order_by(PaymentRequestRow.created_at.desc())
    stmt = stmt.offset(max(offset, 0)).limit(min(max(limit, 1), 200))
    rows = session.execute(stmt).scalars().all()
    return [_row_to_domain(row) for row in rows]


def has_in_flight_for_holding(session: Session, holding_id: UUID) -> bool:
    """Spec module 06 concurrency rule: only one in-flight PaymentRequest
    per Holding at a time. "In-flight" = status in
    {DRAFT, AWAITING_SIGNATURE, AWAITING_BROADCAST, BROADCAST}."""
    in_flight = (
        PaymentStatus.DRAFT.value,
        PaymentStatus.AWAITING_SIGNATURE.value,
        PaymentStatus.AWAITING_BROADCAST.value,
        PaymentStatus.BROADCAST.value,
    )
    row = session.execute(
        select(PaymentRequestRow.id).where(
            PaymentRequestRow.holding_id == holding_id,
            PaymentRequestRow.status.in_(in_flight),
        ).limit(1)
    ).scalar_one_or_none()
    return row is not None


# --- writes -----------------------------------------------------------------


def insert(session: Session, request: PaymentRequest) -> None:
    """Persist a new PaymentRequest. Caller commits."""
    row = PaymentRequestRow(
        id=request.id,
        holding_id=request.holding_id,
        payment_type=request.payment_type.value,
        amount_sats=request.amount_sats,
        description=request.description,
        status=request.status.value,
        expires_at=request.expires_at,
        destination_address=request.destination_address,
        bip21_uri=request.bip21_uri,
        psbt_base64=request.psbt_base64,
        signed_transaction_hex=request.signed_transaction_hex,
        broadcast_txid=request.broadcast_txid,
        lightning_invoice=request.lightning_invoice,
        lightning_payment_hash=request.lightning_payment_hash,
        resulting_ledger_entry_id=request.resulting_ledger_entry_id,
    )
    session.add(row)


def mark_signed(
    session: Session,
    request_id: UUID,
    *,
    signed_transaction_hex: str,
    psbt_base64: str | None = None,
) -> PaymentRequest | None:
    row = session.get(PaymentRequestRow, request_id)
    if row is None:
        return None
    row.signed_transaction_hex = signed_transaction_hex
    if psbt_base64 is not None:
        row.psbt_base64 = psbt_base64
    row.status = PaymentStatus.AWAITING_BROADCAST.value
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def mark_broadcast(
    session: Session,
    request_id: UUID,
    *,
    broadcast_txid: str,
) -> PaymentRequest | None:
    row = session.get(PaymentRequestRow, request_id)
    if row is None:
        return None
    row.broadcast_txid = broadcast_txid
    row.status = PaymentStatus.BROADCAST.value
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def mark_confirmed(
    session: Session,
    request_id: UUID,
    *,
    resulting_ledger_entry_id: UUID,
) -> PaymentRequest | None:
    row = session.get(PaymentRequestRow, request_id)
    if row is None:
        return None
    row.resulting_ledger_entry_id = resulting_ledger_entry_id
    row.status = PaymentStatus.CONFIRMED.value
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def cancel(
    session: Session, request_id: UUID
) -> PaymentRequest | None:
    """Soft-cancel a request. Spec module 06: only allowed in
    {DRAFT, AWAITING_SIGNATURE, AWAITING_BROADCAST}."""
    row = session.get(PaymentRequestRow, request_id)
    if row is None:
        return None
    if row.status not in (
        PaymentStatus.DRAFT.value,
        PaymentStatus.AWAITING_SIGNATURE.value,
        PaymentStatus.AWAITING_BROADCAST.value,
    ):
        raise ValueError(
            f"Cannot cancel a PaymentRequest with status={row.status!r}"
        )
    row.status = PaymentStatus.CANCELLED.value
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


# --- broadcast attempts -----------------------------------------------------


def insert_broadcast_attempt(
    session: Session,
    *,
    attempt_id: UUID,
    payment_request_id: UUID,
    transaction_hex: str,
    txid: str,
    status: str,
    rejection_reason: str | None = None,
) -> None:
    """Persist one broadcast attempt — `status` is `submitted`/`accepted`/`rejected`."""
    completed = (
        datetime.now(UTC) if status in ("accepted", "rejected") else None
    )
    row = BroadcastAttemptRow(
        id=attempt_id,
        payment_request_id=payment_request_id,
        transaction_hex=transaction_hex,
        txid=txid,
        status=status,
        rejection_reason=rejection_reason,
        completed_at=completed,
    )
    session.add(row)


__all__ = [
    "cancel",
    "get",
    "get_by_broadcast_txid",
    "has_in_flight_for_holding",
    "insert",
    "insert_broadcast_attempt",
    "list_filtered",
    "list_for_holding",
    "mark_broadcast",
    "mark_confirmed",
    "mark_signed",
]
