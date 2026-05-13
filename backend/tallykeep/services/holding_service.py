"""Holding service — orchestration over the holding, descriptor, and address
repositories. The domain dataclass enforces invariants at construction; this
service ties together the multi-row writes and the BDK adapter for descriptor
import."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import (
    DescriptorAdapter,
    DescriptorParseError,
    UnsupportedDescriptorError,
)
from tallykeep.domain.descriptor import Address, Descriptor
from tallykeep.domain.enums import (
    CustodyModel,
    HoldingType,
    Network,
    Purpose,
    SigningModel,
)
from tallykeep.domain.holding import Holding, SecurityClaim
from tallykeep.repositories import descriptor as descriptor_repo
from tallykeep.repositories import holding as holding_repo
from tallykeep.schemas.holding import DescriptorInput


_BIP44_PATH_BY_ADDRESS_TYPE: dict[str, str] = {
    "legacy": "m/44'/0'/0'",
    "nested_segwit": "m/49'/0'/0'",
    "native_segwit": "m/84'/0'/0'",
    "taproot": "m/86'/0'/0'",
}


class HoldingServiceError(ValueError):
    """Wraps domain / adapter errors so the API layer has a single thing to catch."""


def _now() -> datetime:
    return datetime.now(UTC)


def _import_descriptor(
    session: Session,
    *,
    holding_id: UUID,
    spec: DescriptorInput,
    adapter: DescriptorAdapter,
    allow_multisig: bool = False,
) -> tuple[Descriptor, list[Address]]:
    """Validate, persist, and pre-derive addresses for one descriptor.

    Returns the persisted Descriptor + the gap_limit-many addresses on the
    external chain (and on change if a change_expression is supplied).
    """
    try:
        parsed_external = adapter.parse(
            spec.expression, spec.network, allow_multisig=allow_multisig
        )
    except (DescriptorParseError, UnsupportedDescriptorError) as exc:
        raise HoldingServiceError(f"external descriptor: {exc}") from exc

    if spec.change_expression is not None:
        try:
            parsed_change = adapter.parse(
                spec.change_expression, spec.network, allow_multisig=allow_multisig
            )
        except (DescriptorParseError, UnsupportedDescriptorError) as exc:
            raise HoldingServiceError(f"change descriptor: {exc}") from exc
        if parsed_change.address_type != parsed_external.address_type:
            raise HoldingServiceError(
                "external and change descriptors must have the same address type"
            )

    descriptor = Descriptor(
        id=uuid4(),
        holding_id=holding_id,
        name=spec.name,
        expression=spec.expression,
        change_expression=spec.change_expression,
        network=spec.network,
        address_type=parsed_external.address_type,
        gap_limit=spec.gap_limit,
        is_watch_only=True,
        last_scanned_height=0,
        created_at=_now(),
    )
    descriptor_repo.insert_descriptor(session, descriptor)

    derivation_root = _BIP44_PATH_BY_ADDRESS_TYPE.get(
        parsed_external.address_type.value, "m/0"
    )

    addresses: list[Address] = []
    derived_external = adapter.derive_addresses(
        spec.expression, spec.network, count=spec.gap_limit, allow_multisig=allow_multisig
    )
    for d in derived_external:
        addresses.append(
            Address(
                id=uuid4(),
                descriptor_id=descriptor.id,
                address=d.address,
                derivation_path=f"{derivation_root}/0/{d.derivation_index}",
                is_change=False,
                derivation_index=d.derivation_index,
                label=None,
                first_seen_height=None,
                is_reused=False,
                created_at=_now(),
            )
        )

    if spec.change_expression is not None:
        derived_change = adapter.derive_addresses(
            spec.change_expression, spec.network, count=spec.gap_limit,
            allow_multisig=allow_multisig,
        )
        for d in derived_change:
            addresses.append(
                Address(
                    id=uuid4(),
                    descriptor_id=descriptor.id,
                    address=d.address,
                    derivation_path=f"{derivation_root}/1/{d.derivation_index}",
                    is_change=True,
                    derivation_index=d.derivation_index,
                    label=None,
                    first_seen_height=None,
                    is_reused=False,
                    created_at=_now(),
                )
            )

    descriptor_repo.insert_addresses(session, addresses)
    return descriptor, addresses


def _build_security_claim(claim: dict | None, defaults: SecurityClaim) -> SecurityClaim:
    """For the per-type creation helpers — accept either an explicit claim or
    fall back to type-appropriate defaults."""
    if claim is None:
        return defaults
    return SecurityClaim(
        custody_model=CustodyModel(claim["custody_model"]),
        signing_model=SigningModel(claim["signing_model"]),
        geographic_distribution=claim.get("geographic_distribution", False),
        inheritance_configured=claim.get("inheritance_configured", False),
        notes=claim.get("notes"),
    )


# --- per-type creation -------------------------------------------------------


def _create_holding_with_descriptors(
    session: Session,
    *,
    holding_type: HoldingType,
    name: str,
    description: str | None,
    purpose: Purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    descriptors: list[DescriptorInput],
    adapter: DescriptorAdapter,
    subtype_data: dict,
    extra_holding_kwargs: dict | None = None,
    allow_multisig: bool = False,
) -> Holding:
    """Shared lifecycle for Purse / Strongbox / Vault creation.

    Order matters: the holding row must land (and flush) BEFORE any descriptor
    row, because `descriptor.holding_id` is a foreign key into `holding`.
    """
    holding_id = uuid4()

    # 1. Persist the holding row from explicit fields (bypasses the domain
    #    `Holding(...)` invariant that requires non-empty descriptor_ids,
    #    which can only be true after step 2).
    holding_repo.insert_row(
        session,
        holding_id=holding_id,
        holding_type=holding_type,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        subtype_data=subtype_data,
    )
    session.flush()  # so descriptor.holding_id FK references can resolve

    # 2. Insert each descriptor + its derived addresses.
    descriptor_ids: list[UUID] = []
    for spec in descriptors:
        descriptor, _ = _import_descriptor(
            session, holding_id=holding_id, spec=spec, adapter=adapter,
            allow_multisig=allow_multisig,
        )
        descriptor_ids.append(descriptor.id)

    # 3. Build the canonical domain Holding for the response. __post_init__
    #    runs the full set of invariants now that descriptor_ids is populated.
    extra = extra_holding_kwargs or {}
    return Holding(
        id=holding_id,
        holding_type=holding_type,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        is_archived=False,
        created_at=_now(),
        updated_at=_now(),
        descriptor_ids=descriptor_ids,
        **extra,
    )


def create_purse(
    session: Session,
    *,
    name: str,
    description: str | None,
    purpose: Purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    descriptors: list[DescriptorInput],
    adapter: DescriptorAdapter,
    seed_origin,  # PurseSeedOrigin
) -> Holding:
    return _create_holding_with_descriptors(
        session,
        holding_type=HoldingType.PURSE,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        descriptors=descriptors,
        adapter=adapter,
        subtype_data={"seed_origin": seed_origin.value},
        extra_holding_kwargs={"seed_origin": seed_origin},
    )


def create_strongbox(
    session: Session,
    *,
    name: str,
    description: str | None,
    purpose: Purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    descriptors: list[DescriptorInput],
    adapter: DescriptorAdapter,
    signing_device_label: str | None,
) -> Holding:
    subtype_data: dict = {}
    if signing_device_label is not None:
        subtype_data["signing_device_label"] = signing_device_label
    return _create_holding_with_descriptors(
        session,
        holding_type=HoldingType.STRONGBOX,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        descriptors=descriptors,
        adapter=adapter,
        subtype_data=subtype_data,
        extra_holding_kwargs={"signing_device_label": signing_device_label},
    )


def create_vault(
    session: Session,
    *,
    name: str,
    description: str | None,
    purpose: Purpose,
    declared_security: SecurityClaim,
    display_color: str,
    display_order: int,
    descriptors: list[DescriptorInput],
    adapter: DescriptorAdapter,
    required_signers: int | None,
    total_signers: int | None,
    timelock_blocks: int | None,
    recovery_setup_notes: str | None,
) -> Holding:
    for spec in descriptors:
        try:
            parsed = adapter.parse(spec.expression, spec.network, allow_multisig=True)
        except (DescriptorParseError, UnsupportedDescriptorError) as exc:
            raise HoldingServiceError(str(exc)) from exc
        if not parsed.is_multisig:
            raise HoldingServiceError(
                "Vault holdings require multisig descriptors. "
                f"Descriptor '{spec.name}' is a single-key descriptor and is not accepted here."
            )

    subtype_data: dict = {}
    if required_signers is not None:
        subtype_data["required_signers"] = required_signers
    if total_signers is not None:
        subtype_data["total_signers"] = total_signers
    if timelock_blocks is not None:
        subtype_data["timelock_blocks"] = timelock_blocks
    if recovery_setup_notes is not None:
        subtype_data["recovery_setup_notes"] = recovery_setup_notes
    return _create_holding_with_descriptors(
        session,
        holding_type=HoldingType.VAULT,
        name=name,
        description=description,
        purpose=purpose,
        declared_security=declared_security,
        display_color=display_color,
        display_order=display_order,
        descriptors=descriptors,
        adapter=adapter,
        subtype_data=subtype_data,
        allow_multisig=True,
        extra_holding_kwargs={
            "required_signers": required_signers,
            "total_signers": total_signers,
            "timelock_blocks": timelock_blocks,
            "recovery_setup_notes": recovery_setup_notes,
        },
    )


# --- list / get / update -----------------------------------------------------


def get_holding(session: Session, holding_id: UUID) -> Holding | None:
    from sqlalchemy import select as _sa_select
    from tallykeep.models.custodial_provider import CustodialProviderRow

    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, holding_id)
    custodial_provider_id: UUID | None = session.execute(
        _sa_select(CustodialProviderRow.id).where(
            CustodialProviderRow.holding_id == holding_id
        )
    ).scalar_one_or_none()
    return holding_repo.get(
        session,
        holding_id,
        descriptor_ids=descriptor_ids,
        custodial_provider_id=custodial_provider_id,
    )


def list_holdings(
    session: Session,
    *,
    holding_type: HoldingType | None = None,
    purpose: Purpose | None = None,
    include_archived: bool = False,
) -> list[Holding]:
    rows = holding_repo.list_holdings(
        session,
        holding_type=holding_type,
        purpose=purpose,
        include_archived=include_archived,
    )
    holdings: list[Holding] = []
    for row in rows:
        descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, row.id)
        holdings.append(
            holding_repo.to_domain(row, descriptor_ids=descriptor_ids)
        )
    return holdings


def update_holding(
    session: Session,
    holding_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    purpose: Purpose | None = None,
    declared_security: SecurityClaim | None = None,
    display_color: str | None = None,
    display_order: int | None = None,
) -> Holding | None:
    row = holding_repo.update_basics(
        session,
        holding_id,
        name=name,
        description=description,
        purpose=purpose,
        display_color=display_color,
        display_order=display_order,
        declared_security=declared_security,
    )
    if row is None:
        return None
    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, row.id)
    return holding_repo.to_domain(row, descriptor_ids=descriptor_ids)


def archive_holding(session: Session, holding_id: UUID) -> bool:
    return holding_repo.archive(session, holding_id)


def change_holding_type(
    session: Session,
    holding_id: UUID,
    new_type: HoldingType,
    reason: str | None,
) -> Holding | None:
    """Type change. Domain invariants apply *after* the swap, so we re-construct
    the domain object once the row is updated to ensure the new type is
    compatible with the existing descriptor count and declared security.
    """
    if new_type == HoldingType.ACCOUNT:
        # Account requires a CustodialProvider; M4 doesn't manage those, so
        # changing TO Account is rejected here. Changing FROM Account is
        # similarly rejected (you can't strip a CustodialProvider in M4).
        raise HoldingServiceError(
            "Changing to Account is not supported in M4 (lands with M8)."
        )

    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, holding_id)
    if not descriptor_ids and new_type in (
        HoldingType.PURSE,
        HoldingType.STRONGBOX,
        HoldingType.VAULT,
    ):
        raise HoldingServiceError(
            f"Cannot change type to {new_type.value}: at least one descriptor "
            "must be attached first."
        )

    row = holding_repo.change_type(session, holding_id, new_type, reason)
    if row is None:
        return None

    # Re-construct the domain object so the new type's invariants are checked.
    return holding_repo.to_domain(row, descriptor_ids=descriptor_ids)


__all__ = [
    "HoldingServiceError",
    "archive_holding",
    "change_holding_type",
    "create_purse",
    "create_strongbox",
    "create_vault",
    "get_holding",
    "list_holdings",
    "update_holding",
]
