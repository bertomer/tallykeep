"""Holding repository — CRUD over the `holding` table.

Subtype-specific fields (signing_device_label for Strongbox, multisig metadata
for Vault) live in the JSONB `subtype_data` column on the row, but the domain
dataclass exposes them as proper fields. This module is the translation layer.
"""

from __future__ import annotations

from dataclasses import MISSING as _UNSET
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from tallykeep.domain.enums import (
    CustodyModel,
    HoldingType,
    Purpose,
    PurseMode,
    SigningModel,
)
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.models import (
    AddressRow,
    BroadcastAttemptRow,
    CustodialLedgerEntryRow,
    CustodialProviderRow,
    DescriptorRow,
    HoldingRow,
    HoldingTypeChangeLogRow,
    InvoiceRow,
    LedgerEntryHoldingLinkRow,
    LedgerEntryRow,
    PaymentRequestRow,
    SweepExecutionRow,
    SweepPolicyRow,
    UTXORow,
)


def _row_to_domain(
    row: HoldingRow, descriptor_ids: list[UUID], custodial_provider_id: UUID | None
) -> Holding:
    subtype = dict(row.subtype_data or {})
    return Holding(
        id=row.id,
        holding_type=HoldingType(row.holding_type),
        name=row.name,
        description=row.description,
        purpose=Purpose(row.purpose),
        declared_security=SecurityClaim(
            custody_model=CustodyModel(row.declared_custody_model),
            signing_model=SigningModel(row.declared_signing_model),
            geographic_distribution=row.declared_geographic_distribution,
            inheritance_configured=row.declared_inheritance_configured,
            notes=row.declared_security_notes,
        ),
        display_color=row.display_color,
        display_order=row.display_order,
        created_at=row.created_at,
        updated_at=row.updated_at,
        custodial_provider_id=custodial_provider_id,
        descriptor_ids=list(descriptor_ids),
        purse_mode=(
            PurseMode(subtype["purse_mode"])
            if subtype.get("purse_mode") else None
        ),
        signing_device_label=subtype.get("signing_device_label"),
        vendor=subtype.get("vendor"),
        signing_metadata_present=subtype.get("signing_metadata_present"),
        required_signers=subtype.get("required_signers"),
        total_signers=subtype.get("total_signers"),
        timelock_kind=subtype.get("timelock_kind"),
        timelock_value=subtype.get("timelock_value"),
        recovery_setup_notes=subtype.get("recovery_setup_notes"),
    )


def _build_subtype_data(holding: Holding) -> dict[str, Any]:
    """Pull subtype-specific fields off the domain object into a dict for JSONB."""
    payload: dict[str, Any] = {}
    if holding.holding_type == HoldingType.STRONGBOX:
        if holding.signing_device_label is not None:
            payload["signing_device_label"] = holding.signing_device_label
        if holding.vendor is not None:
            payload["vendor"] = holding.vendor
        if holding.signing_metadata_present is not None:
            payload["signing_metadata_present"] = holding.signing_metadata_present
    elif holding.holding_type == HoldingType.VAULT:
        if holding.required_signers is not None:
            payload["required_signers"] = holding.required_signers
        if holding.total_signers is not None:
            payload["total_signers"] = holding.total_signers
        if holding.timelock_kind is not None:
            payload["timelock_kind"] = holding.timelock_kind
        if holding.timelock_value is not None:
            payload["timelock_value"] = holding.timelock_value
        if holding.recovery_setup_notes is not None:
            payload["recovery_setup_notes"] = holding.recovery_setup_notes
    return payload


def insert(session: Session, holding: Holding) -> None:
    """Persist a new Holding. Caller is responsible for committing the session.

    Descriptor / CustodialProvider rows are managed by their own repositories
    and FK back to this row; this insert only touches the `holding` table.
    """
    row = HoldingRow(
        id=holding.id,
        holding_type=holding.holding_type.value,
        name=holding.name,
        description=holding.description,
        purpose=holding.purpose.value,
        declared_custody_model=holding.declared_security.custody_model.value,
        declared_signing_model=holding.declared_security.signing_model.value,
        declared_geographic_distribution=holding.declared_security.geographic_distribution,
        declared_inheritance_configured=holding.declared_security.inheritance_configured,
        declared_security_notes=holding.declared_security.notes,
        subtype_data=_build_subtype_data(holding),
        display_color=holding.display_color,
        display_order=holding.display_order,
    )
    session.add(row)


def insert_row(
    session: Session,
    *,
    holding_id: UUID,
    holding_type: HoldingType,
    name: str,
    description: str | None,
    purpose: Purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    subtype_data: dict[str, Any],
) -> None:
    """Persist a holding row from explicit fields.

    Domain `Holding` requires a populated `descriptor_ids` list for non-Account
    types, but the row itself doesn't carry those — descriptor_ids are derived
    via FK lookup. The service layer uses this entry point so it can write the
    holding row first, then attach descriptors that reference it.
    """
    row = HoldingRow(
        id=holding_id,
        holding_type=holding_type.value,
        name=name,
        description=description,
        purpose=purpose.value,
        declared_custody_model=declared_security.custody_model.value,
        declared_signing_model=declared_security.signing_model.value,
        declared_geographic_distribution=declared_security.geographic_distribution,
        declared_inheritance_configured=declared_security.inheritance_configured,
        declared_security_notes=declared_security.notes,
        subtype_data=subtype_data,
        display_color=display_color,
        display_order=display_order,
    )
    session.add(row)


def get(
    session: Session,
    holding_id: UUID,
    *,
    descriptor_ids: list[UUID] | None = None,
    custodial_provider_id: UUID | None = None,
) -> Holding | None:
    """Fetch a single Holding by id, or None if not found."""
    row = session.get(HoldingRow, holding_id)
    if row is None:
        return None
    return _row_to_domain(
        row,
        descriptor_ids=descriptor_ids or [],
        custodial_provider_id=custodial_provider_id,
    )


def list_holdings(
    session: Session,
    *,
    holding_type: HoldingType | None = None,
    purpose: Purpose | None = None,
) -> list[HoldingRow]:
    """Return raw rows; the service layer attaches descriptors/providers per row.

    We intentionally return rows (not domain objects) so the caller can do a
    single batched lookup of related descriptors/providers across the result set
    rather than N+1 queries inside this method.
    """
    stmt = select(HoldingRow)
    if holding_type is not None:
        stmt = stmt.where(HoldingRow.holding_type == holding_type.value)
    if purpose is not None:
        stmt = stmt.where(HoldingRow.purpose == purpose.value)
    stmt = stmt.order_by(HoldingRow.display_order, HoldingRow.created_at)
    return list(session.execute(stmt).scalars().all())


def update_basics(
    session: Session,
    holding_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    purpose: Purpose | None = None,
    display_color: str | None = None,
    display_order: int | None = None,
    declared_security: SecurityClaim | None = None,
    signing_device_label: Any = _UNSET,
) -> HoldingRow | None:
    """Apply a partial update — caller must commit. Returns the row or None.

    ``signing_device_label`` uses the ``_UNSET`` sentinel to distinguish
    "not provided" (no change) from ``None`` (clear the label).
    """
    row = session.get(HoldingRow, holding_id)
    if row is None:
        return None
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if purpose is not None:
        row.purpose = purpose.value
    if display_color is not None:
        row.display_color = display_color
    if display_order is not None:
        row.display_order = display_order
    if declared_security is not None:
        row.declared_custody_model = declared_security.custody_model.value
        row.declared_signing_model = declared_security.signing_model.value
        row.declared_geographic_distribution = declared_security.geographic_distribution
        row.declared_inheritance_configured = declared_security.inheritance_configured
        row.declared_security_notes = declared_security.notes
    if signing_device_label is not _UNSET:
        if row.holding_type != HoldingType.STRONGBOX.value:
            raise ValueError("signing_device_label is only valid for Strongbox holdings")
        new_data = dict(row.subtype_data or {})
        if signing_device_label is None:
            new_data.pop("signing_device_label", None)
        else:
            new_data["signing_device_label"] = signing_device_label
        row.subtype_data = new_data
    row.updated_at = datetime.now(UTC)
    return row


def delete_cascade(session: Session, holding_id: UUID) -> bool:
    """Hard-delete a Holding and all its related rows in FK-safe order.

    Returns True if the holding existed and was deleted, False if not found.

    For Account holdings, the caller must clean up secrets BEFORE calling this.
    The CustodialProvider row is deleted here; the CASCADE on its FK to
    custodial_ledger_entry handles the CLE rows.

    The linked_counterparty_holding_id FK on custodial_ledger_entry is
    ON DELETE SET NULL (per ADR-0017); the DB handles that automatically when
    the holding row is deleted in the final step.
    """
    row = session.get(HoldingRow, holding_id)
    if row is None:
        return False

    # 1. Audit log
    session.execute(
        delete(HoldingTypeChangeLogRow).where(
            HoldingTypeChangeLogRow.holding_id == holding_id
        )
    )

    # 2. Sweep policies + executions.
    #    Before deleting sweep_executions, NULL out CLE references (RESTRICT FK).
    policy_subq = (
        select(SweepPolicyRow.id)
        .where(
            sa.or_(
                SweepPolicyRow.source_holding_id == holding_id,
                SweepPolicyRow.destination_holding_id == holding_id,
            )
        )
        .scalar_subquery()
    )
    session.execute(
        sa.update(CustodialLedgerEntryRow)
        .where(
            CustodialLedgerEntryRow.linked_sweep_execution_id.in_(
                select(SweepExecutionRow.id).where(
                    SweepExecutionRow.sweep_policy_id.in_(policy_subq)
                )
            )
        )
        .values(linked_sweep_execution_id=None)
    )
    session.execute(
        delete(SweepExecutionRow).where(
            SweepExecutionRow.sweep_policy_id.in_(policy_subq)
        )
    )
    session.execute(
        delete(SweepPolicyRow).where(
            sa.or_(
                SweepPolicyRow.source_holding_id == holding_id,
                SweepPolicyRow.destination_holding_id == holding_id,
            )
        )
    )

    # 3. Chain-side: UTXOs → addresses → descriptors (no-op for Account).
    desc_subq = (
        select(DescriptorRow.id)
        .where(DescriptorRow.holding_id == holding_id)
        .scalar_subquery()
    )
    session.execute(delete(UTXORow).where(UTXORow.descriptor_id.in_(desc_subq)))
    session.execute(delete(AddressRow).where(AddressRow.descriptor_id.in_(desc_subq)))
    session.execute(
        delete(DescriptorRow).where(DescriptorRow.holding_id == holding_id)
    )

    # 4. Broadcast attempts → payment requests → invoices.
    pr_subq = (
        select(PaymentRequestRow.id)
        .where(PaymentRequestRow.holding_id == holding_id)
        .scalar_subquery()
    )
    session.execute(
        delete(BroadcastAttemptRow).where(
            BroadcastAttemptRow.payment_request_id.in_(pr_subq)
        )
    )
    session.execute(
        delete(PaymentRequestRow).where(PaymentRequestRow.holding_id == holding_id)
    )
    session.execute(
        delete(InvoiceRow).where(InvoiceRow.holding_id == holding_id)
    )

    # 5. LedgerEntry holding links → orphaned LedgerEntries.
    #    Before deleting orphaned entries, NULL out any CLE back-references
    #    that carry a RESTRICT FK to ledger_entry.
    candidate_ids = session.execute(
        select(LedgerEntryHoldingLinkRow.ledger_entry_id).where(
            LedgerEntryHoldingLinkRow.holding_id == holding_id
        )
    ).scalars().all()

    if candidate_ids:
        session.execute(
            sa.update(CustodialLedgerEntryRow)
            .where(
                CustodialLedgerEntryRow.linked_chain_ledger_entry_id.in_(candidate_ids)
            )
            .values(linked_chain_ledger_entry_id=None)
        )
        # NULL out payment_request.resulting_ledger_entry_id for about-to-be-deleted entries
        session.execute(
            sa.update(PaymentRequestRow)
            .where(PaymentRequestRow.resulting_ledger_entry_id.in_(candidate_ids))
            .values(resulting_ledger_entry_id=None)
        )

    session.execute(
        delete(LedgerEntryHoldingLinkRow).where(
            LedgerEntryHoldingLinkRow.holding_id == holding_id
        )
    )

    if candidate_ids:
        # Delete entries that now have no remaining links.
        still_linked_subq = (
            select(LedgerEntryHoldingLinkRow.ledger_entry_id)
            .where(
                LedgerEntryHoldingLinkRow.ledger_entry_id.in_(candidate_ids)
            )
        )
        session.execute(
            delete(LedgerEntryRow)
            .where(LedgerEntryRow.id.in_(candidate_ids))
            .where(~LedgerEntryRow.id.in_(still_linked_subq))
        )

    # 6. CustodialProvider (CASCADE deletes CustodialLedgerEntry rows for Account).
    #    No-op for non-Account holdings (no CP row exists).
    session.execute(
        delete(CustodialProviderRow).where(
            CustodialProviderRow.holding_id == holding_id
        )
    )

    # 7. Holding row itself.
    #    linked_counterparty_holding_id FK is ON DELETE SET NULL — DB handles it.
    session.delete(row)
    return True


def change_type(
    session: Session,
    holding_id: UUID,
    new_type: HoldingType,
    reason: str | None,
) -> HoldingRow | None:
    """Mutate the type and write a holding_type_change_log row.

    Spec module 02: type change is mutable but requires deliberate confirmation
    and is recorded in an audit log. The service layer enforces additional
    invariants (e.g. compatible descriptors, custody/signing model alignment)
    before calling this; the repository only does the mechanical write.
    """
    from uuid import uuid4

    row = session.get(HoldingRow, holding_id)
    if row is None:
        return None
    log = HoldingTypeChangeLogRow(
        id=uuid4(),
        holding_id=holding_id,
        previous_type=row.holding_type,
        new_type=new_type.value,
        reason=reason,
    )
    session.add(log)
    row.holding_type = new_type.value
    row.updated_at = datetime.now(UTC)
    return row


def to_domain(
    row: HoldingRow,
    *,
    descriptor_ids: list[UUID] | None = None,
    custodial_provider_id: UUID | None = None,
) -> Holding:
    """Public translator — used by the service layer after a list query."""
    return _row_to_domain(
        row,
        descriptor_ids=descriptor_ids or [],
        custodial_provider_id=custodial_provider_id,
    )


__all__ = [
    "change_type",
    "delete_cascade",
    "get",
    "insert",
    "list_holdings",
    "to_domain",
    "update_basics",
]
