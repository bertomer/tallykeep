"""CustodialProvider repository — CRUD over the `custodial_provider` table."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from tallykeep.domain.custodial_provider import CustodialProvider, ProviderPermissions
from tallykeep.domain.enums import ProviderKind
from tallykeep.models.custodial_provider import CustodialProviderRow


def _row_to_domain(row: CustodialProviderRow) -> CustodialProvider:
    return CustodialProvider(
        id=row.id,
        holding_id=row.holding_id,
        provider_kind=ProviderKind(row.provider_kind),
        display_name=row.display_name,
        adapter_id=row.adapter_id,
        api_credential_reference=row.api_credential_reference,
        api_secret_reference=row.api_secret_reference,
        api_passphrase_reference=row.api_passphrase_reference,
        permissions=ProviderPermissions(
            can_read=row.can_read,
            can_trade=row.can_trade,
            can_withdraw=row.can_withdraw,
        ),
        whitelist_address=row.whitelist_address,
        whitelist_address_descriptor_id=row.whitelist_address_descriptor_id,
        whitelist_verified=row.whitelist_verified,
        is_active=row.is_active,
        last_polled_at=row.last_polled_at,
        last_error=row.last_error,
        last_known_balance_sats=row.last_known_balance_sats,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def get(session: Session, provider_id: UUID) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    return _row_to_domain(row) if row is not None else None


def get_by_holding_id(session: Session, holding_id: UUID) -> CustodialProvider | None:
    row = session.execute(
        select(CustodialProviderRow).where(
            CustodialProviderRow.holding_id == holding_id
        )
    ).scalar_one_or_none()
    return _row_to_domain(row) if row is not None else None


def list_active(session: Session) -> list[CustodialProvider]:
    rows = (
        session.execute(
            select(CustodialProviderRow).where(CustodialProviderRow.is_active.is_(True))
        )
        .scalars()
        .all()
    )
    return [_row_to_domain(r) for r in rows]


def create(session: Session, provider: CustodialProvider) -> None:
    row = CustodialProviderRow(
        id=provider.id,
        holding_id=provider.holding_id,
        provider_kind=provider.provider_kind.value,
        display_name=provider.display_name,
        adapter_id=provider.adapter_id,
        api_credential_reference=provider.api_credential_reference,
        api_secret_reference=provider.api_secret_reference,
        api_passphrase_reference=provider.api_passphrase_reference,
        can_read=provider.permissions.can_read,
        can_trade=provider.permissions.can_trade,
        can_withdraw=provider.permissions.can_withdraw,
        whitelist_address=provider.whitelist_address,
        whitelist_address_descriptor_id=provider.whitelist_address_descriptor_id,
        whitelist_verified=provider.whitelist_verified,
        is_active=provider.is_active,
        last_polled_at=provider.last_polled_at,
        last_error=provider.last_error,
        last_known_balance_sats=provider.last_known_balance_sats,
    )
    session.add(row)


def update_credentials(
    session: Session,
    provider_id: UUID,
    *,
    api_credential_reference: str,
    api_secret_reference: str,
    api_passphrase_reference: str | None,
) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    if row is None:
        return None
    row.api_credential_reference = api_credential_reference
    row.api_secret_reference = api_secret_reference
    row.api_passphrase_reference = api_passphrase_reference
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def update_balance(
    session: Session,
    provider_id: UUID,
    *,
    balance_sats: int,
    polled_at: datetime,
) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    if row is None:
        return None
    row.last_known_balance_sats = balance_sats
    row.last_polled_at = polled_at
    row.last_error = None
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def update_error(
    session: Session,
    provider_id: UUID,
    *,
    error: str,
    polled_at: datetime,
) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    if row is None:
        return None
    row.last_error = error
    row.last_polled_at = polled_at
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def set_whitelist_verified(
    session: Session, provider_id: UUID, *, verified: bool
) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    if row is None:
        return None
    row.whitelist_verified = verified
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)


def set_active(
    session: Session, provider_id: UUID, *, is_active: bool
) -> CustodialProvider | None:
    row = session.get(CustodialProviderRow, provider_id)
    if row is None:
        return None
    row.is_active = is_active
    row.updated_at = datetime.now(UTC)
    return _row_to_domain(row)
