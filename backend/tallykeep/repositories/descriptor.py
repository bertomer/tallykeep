"""Descriptor + Address repositories — CRUD over the `descriptor` and `address`
tables. Hygiene-flag computation and UTXO bookkeeping land in M5."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tallykeep.domain.descriptor import Address, Descriptor
from tallykeep.domain.enums import AddressType, Network
from tallykeep.models import AddressRow, DescriptorRow


# --- descriptor --------------------------------------------------------------


class DescriptorAlreadyExists(RuntimeError):
    """A descriptor with the same canonical expression is already persisted."""


def _descriptor_row_to_domain(row: DescriptorRow) -> Descriptor:
    return Descriptor(
        id=row.id,
        holding_id=row.holding_id,
        name=row.name,
        expression=row.expression,
        change_expression=row.change_expression,
        network=Network(row.network),
        address_type=AddressType(row.address_type),
        gap_limit=row.gap_limit,
        is_watch_only=row.is_watch_only,
        last_scanned_height=row.last_scanned_height,
        created_at=row.created_at,
    )


def insert_descriptor(session: Session, descriptor: Descriptor) -> None:
    """Persist a Descriptor row. Raises DescriptorAlreadyExists if the canonical
    expression collides with an existing row (uq_descriptor_expression)."""
    row = DescriptorRow(
        id=descriptor.id,
        holding_id=descriptor.holding_id,
        name=descriptor.name,
        expression=descriptor.expression,
        change_expression=descriptor.change_expression,
        network=descriptor.network.value,
        address_type=descriptor.address_type.value,
        gap_limit=descriptor.gap_limit,
        is_watch_only=descriptor.is_watch_only,
        last_scanned_height=descriptor.last_scanned_height,
    )
    session.add(row)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise DescriptorAlreadyExists(
            f"A descriptor with expression {descriptor.expression!r} already exists"
        ) from exc


def get_descriptor(session: Session, descriptor_id: UUID) -> Descriptor | None:
    row = session.get(DescriptorRow, descriptor_id)
    return _descriptor_row_to_domain(row) if row is not None else None


def list_descriptors_for_holding(
    session: Session, holding_id: UUID
) -> list[Descriptor]:
    rows = session.execute(
        select(DescriptorRow)
        .where(DescriptorRow.holding_id == holding_id)
        .order_by(DescriptorRow.created_at)
    ).scalars().all()
    return [_descriptor_row_to_domain(row) for row in rows]


def descriptor_ids_for_holding(
    session: Session, holding_id: UUID
) -> list[UUID]:
    rows = session.execute(
        select(DescriptorRow.id)
        .where(DescriptorRow.holding_id == holding_id)
        .order_by(DescriptorRow.created_at)
    ).all()
    return [row[0] for row in rows]


def list_descriptors(
    session: Session, *, holding_id: UUID | None = None
) -> list[Descriptor]:
    stmt = select(DescriptorRow).order_by(DescriptorRow.created_at)
    if holding_id is not None:
        stmt = stmt.where(DescriptorRow.holding_id == holding_id)
    rows = session.execute(stmt).scalars().all()
    return [_descriptor_row_to_domain(row) for row in rows]


def update_descriptor(
    session: Session,
    descriptor_id: UUID,
    *,
    name: str | None = None,
    gap_limit: int | None = None,
) -> Descriptor | None:
    row = session.get(DescriptorRow, descriptor_id)
    if row is None:
        return None
    if name is not None:
        row.name = name
    if gap_limit is not None:
        row.gap_limit = gap_limit
    return _descriptor_row_to_domain(row)


def delete_descriptor(session: Session, descriptor_id: UUID) -> bool:
    """Hard-delete the descriptor row. Caller must check no UTXOs reference it.

    For M4 we accept any caller; M5 will gate this on UTXO presence. The
    foreign-key constraint from `address` will refuse the delete if addresses
    still reference it, so the worst-case failure mode is a noisy IntegrityError
    rather than data loss.
    """
    row = session.get(DescriptorRow, descriptor_id)
    if row is None:
        return False
    session.delete(row)
    return True


# --- address ----------------------------------------------------------------


def _address_row_to_domain(row: AddressRow) -> Address:
    return Address(
        id=row.id,
        descriptor_id=row.descriptor_id,
        address=row.address,
        derivation_path=row.derivation_path,
        is_change=row.is_change,
        derivation_index=row.derivation_index,
        label=row.label,
        first_seen_height=row.first_seen_height,
        is_reused=row.is_reused,
        created_at=row.created_at,
    )


def insert_address(session: Session, address: Address) -> None:
    row = AddressRow(
        id=address.id,
        descriptor_id=address.descriptor_id,
        address=address.address,
        derivation_path=address.derivation_path,
        is_change=address.is_change,
        derivation_index=address.derivation_index,
        label=address.label,
        first_seen_height=address.first_seen_height,
        is_reused=address.is_reused,
    )
    session.add(row)


def insert_addresses(session: Session, addresses: list[Address]) -> None:
    if not addresses:
        return
    session.add_all(
        [
            AddressRow(
                id=a.id,
                descriptor_id=a.descriptor_id,
                address=a.address,
                derivation_path=a.derivation_path,
                is_change=a.is_change,
                derivation_index=a.derivation_index,
                label=a.label,
                first_seen_height=a.first_seen_height,
                is_reused=a.is_reused,
            )
            for a in addresses
        ]
    )


def list_addresses_for_descriptor(
    session: Session,
    descriptor_id: UUID,
    *,
    is_change: bool | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Address]:
    stmt = select(AddressRow).where(AddressRow.descriptor_id == descriptor_id)
    if is_change is not None:
        stmt = stmt.where(AddressRow.is_change.is_(is_change))
    stmt = stmt.order_by(AddressRow.is_change, AddressRow.derivation_index)
    if offset:
        stmt = stmt.offset(offset)
    if limit:
        stmt = stmt.limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [_address_row_to_domain(row) for row in rows]


def update_address_label(
    session: Session, address_id: UUID, label: str | None
) -> Address | None:
    row = session.get(AddressRow, address_id)
    if row is None:
        return None
    row.label = label
    return _address_row_to_domain(row)


def next_unused_address(
    session: Session, descriptor_id: UUID, *, is_change: bool = False
) -> Address | None:
    """Return the lowest-index Address that's neither been seen on-chain
    nor reserved by an open Invoice.

    "Unused" means: no on-chain tx has touched it yet
    (`first_seen_height IS NULL`) AND no OPEN Invoice currently holds
    it via its `receiving_address_id`. The Invoice reservation is the
    M6.4 mechanism — without it, two consecutive Invoice creations
    against the same descriptor would hand out the same address.
    """
    from tallykeep.models import InvoiceRow

    reserved_subq = (
        select(InvoiceRow.receiving_address_id)
        .where(
            InvoiceRow.receiving_address_id.is_not(None),
            InvoiceRow.status == "open",
        )
    )
    stmt = (
        select(AddressRow)
        .where(
            AddressRow.descriptor_id == descriptor_id,
            AddressRow.is_change.is_(is_change),
            AddressRow.first_seen_height.is_(None),
            AddressRow.id.not_in(reserved_subq),
        )
        .order_by(AddressRow.derivation_index)
        .limit(1)
    )
    row = session.execute(stmt).scalar_one_or_none()
    return _address_row_to_domain(row) if row is not None else None


__all__ = [
    "DescriptorAlreadyExists",
    "delete_descriptor",
    "descriptor_ids_for_holding",
    "get_descriptor",
    "insert_address",
    "insert_addresses",
    "insert_descriptor",
    "list_addresses_for_descriptor",
    "list_descriptors",
    "list_descriptors_for_holding",
    "next_unused_address",
    "update_address_label",
    "update_descriptor",
]
