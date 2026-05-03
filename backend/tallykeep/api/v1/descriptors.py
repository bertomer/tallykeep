"""Descriptor endpoints — spec module 04.

M4 implements:
  - GET    /api/v1/descriptors                            (list, with holding_id filter)
  - POST   /api/v1/descriptors                            (attach a new descriptor to an existing holding)
  - GET    /api/v1/descriptors/{id}
  - PATCH  /api/v1/descriptors/{id}                       (rename, change gap_limit)
  - DELETE /api/v1/descriptors/{id}
  - GET    /api/v1/descriptors/{id}/addresses             (paginated)
  - POST   /api/v1/descriptors/{id}/addresses/next-receiving

Stubs (deferred to M5):
  - POST   /api/v1/descriptors/{id}/rescan                (chain scan)
  - GET    /api/v1/descriptors/{id}/utxos
  - GET    /api/v1/descriptors/{id}/balance
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import (
    DescriptorAdapter,
    DescriptorParseError,
    UnsupportedDescriptorError,
)
from tallykeep.adapters.node_adapter import NodeAdapter, NodeError
from tallykeep.api.dependencies import get_db_session, get_node_adapter
from tallykeep.domain.descriptor import Address, Descriptor
from tallykeep.repositories import descriptor as descriptor_repo
from tallykeep.repositories import holding as holding_repo
from tallykeep.schemas.holding import (
    AddressListResponse,
    AddressResponse,
    DescriptorInput,
    DescriptorResponse,
    NextReceivingAddressResponse,
)


router = APIRouter(tags=["descriptors"])
_ADAPTER = DescriptorAdapter()


# --- attach-to-existing-holding input ---------------------------------------


class AttachDescriptorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    holding_id: UUID
    descriptor: DescriptorInput


class DescriptorPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    # Same cap as DescriptorInput.gap_limit (2× the BIP 44 standard of 20).
    gap_limit: int | None = Field(default=None, ge=1, le=40)


# --- helpers -----------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _descriptor_to_response(descriptor: Descriptor) -> DescriptorResponse:
    return DescriptorResponse(
        id=descriptor.id,
        holding_id=descriptor.holding_id,
        name=descriptor.name,
        expression=descriptor.expression,
        change_expression=descriptor.change_expression,
        network=descriptor.network,
        address_type=descriptor.address_type,
        gap_limit=descriptor.gap_limit,
        is_watch_only=descriptor.is_watch_only,
        last_scanned_height=descriptor.last_scanned_height,
        created_at=descriptor.created_at,
    )


def _address_to_response(address: Address) -> AddressResponse:
    return AddressResponse(
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


# --- list / attach -----------------------------------------------------------


@router.get("/descriptors", response_model=list[DescriptorResponse])
async def list_descriptors(
    holding_id: UUID | None = None,
    session: Session = Depends(get_db_session),
) -> list[DescriptorResponse]:
    descriptors = descriptor_repo.list_descriptors(session, holding_id=holding_id)
    return [_descriptor_to_response(d) for d in descriptors]


@router.post(
    "/descriptors",
    response_model=DescriptorResponse,
    status_code=201,
)
async def attach_descriptor(
    body: AttachDescriptorRequest,
    session: Session = Depends(get_db_session),
) -> DescriptorResponse:
    """Attach a new Descriptor + its derived addresses to an existing Holding."""
    # We cannot construct the domain Holding without knowing its
    # descriptor_ids first (dataclass invariant). Read the raw row to check
    # existence + type.
    from tallykeep.models import HoldingRow

    target_row = session.get(HoldingRow, body.holding_id)
    if target_row is None:
        raise HTTPException(status_code=404, detail="Holding not found")
    if target_row.holding_type == "account":
        raise HTTPException(
            status_code=422,
            detail="Account holdings cannot have descriptors",
        )

    spec = body.descriptor
    try:
        parsed = _ADAPTER.parse(spec.expression, spec.network)
    except (DescriptorParseError, UnsupportedDescriptorError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    descriptor = Descriptor(
        id=uuid4(),
        holding_id=body.holding_id,
        name=spec.name,
        expression=spec.expression,
        change_expression=spec.change_expression,
        network=spec.network,
        address_type=parsed.address_type,
        gap_limit=spec.gap_limit,
        is_watch_only=True,
        last_scanned_height=0,
        created_at=_now(),
    )
    try:
        descriptor_repo.insert_descriptor(session, descriptor)
    except descriptor_repo.DescriptorAlreadyExists as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    derived = _ADAPTER.derive_addresses(
        spec.expression, spec.network, count=spec.gap_limit
    )
    addresses = [
        Address(
            id=uuid4(),
            descriptor_id=descriptor.id,
            address=d.address,
            derivation_path=f"m/0/{d.derivation_index}",
            is_change=False,
            derivation_index=d.derivation_index,
            label=None,
            first_seen_height=None,
            is_reused=False,
            created_at=_now(),
        )
        for d in derived
    ]
    descriptor_repo.insert_addresses(session, addresses)
    if spec.change_expression is not None:
        derived_change = _ADAPTER.derive_addresses(
            spec.change_expression, spec.network, count=spec.gap_limit
        )
        change_addresses = [
            Address(
                id=uuid4(),
                descriptor_id=descriptor.id,
                address=d.address,
                derivation_path=f"m/1/{d.derivation_index}",
                is_change=True,
                derivation_index=d.derivation_index,
                label=None,
                first_seen_height=None,
                is_reused=False,
                created_at=_now(),
            )
            for d in derived_change
        ]
        descriptor_repo.insert_addresses(session, change_addresses)

    session.commit()
    return _descriptor_to_response(descriptor)


# --- single descriptor -------------------------------------------------------


@router.get("/descriptors/{descriptor_id}", response_model=DescriptorResponse)
async def get_descriptor(
    descriptor_id: UUID, session: Session = Depends(get_db_session)
) -> DescriptorResponse:
    descriptor = descriptor_repo.get_descriptor(session, descriptor_id)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    return _descriptor_to_response(descriptor)


@router.patch("/descriptors/{descriptor_id}", response_model=DescriptorResponse)
async def patch_descriptor(
    descriptor_id: UUID,
    body: DescriptorPatch,
    session: Session = Depends(get_db_session),
) -> DescriptorResponse:
    if body.model_dump(exclude_unset=True) == {}:
        raise HTTPException(status_code=422, detail="empty update")

    descriptor = descriptor_repo.update_descriptor(
        session, descriptor_id, name=body.name, gap_limit=body.gap_limit
    )
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    session.commit()
    return _descriptor_to_response(descriptor)


@router.delete("/descriptors/{descriptor_id}", status_code=204)
async def delete_descriptor(
    descriptor_id: UUID, session: Session = Depends(get_db_session)
) -> Response:
    """Hard-delete a descriptor.

    Refuses if any addresses still reference it. Address cascade-cleanup is
    M5 territory; for now archive the owning holding instead of deleting the
    descriptor.
    """
    addresses = descriptor_repo.list_addresses_for_descriptor(
        session, descriptor_id, limit=1
    )
    if addresses:
        raise HTTPException(
            status_code=409,
            detail=(
                "Descriptor has derived addresses. Address cleanup lands "
                "in M5; archive the owning holding instead."
            ),
        )
    ok = descriptor_repo.delete_descriptor(session, descriptor_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    session.commit()
    return Response(status_code=204)


# --- addresses ---------------------------------------------------------------


@router.get(
    "/descriptors/{descriptor_id}/addresses",
    response_model=AddressListResponse,
)
async def list_descriptor_addresses(
    descriptor_id: UUID,
    is_change: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> AddressListResponse:
    if descriptor_repo.get_descriptor(session, descriptor_id) is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    addresses = descriptor_repo.list_addresses_for_descriptor(
        session,
        descriptor_id,
        is_change=is_change,
        limit=min(max(limit, 1), 200),
        offset=max(offset, 0),
    )
    return AddressListResponse(
        addresses=[_address_to_response(a) for a in addresses]
    )


@router.post(
    "/descriptors/{descriptor_id}/addresses/next-receiving",
    response_model=NextReceivingAddressResponse,
)
async def next_receiving_address(
    descriptor_id: UUID, session: Session = Depends(get_db_session)
) -> NextReceivingAddressResponse:
    if descriptor_repo.get_descriptor(session, descriptor_id) is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    address = descriptor_repo.next_unused_address(
        session, descriptor_id, is_change=False
    )
    if address is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "No unused address available — increase the descriptor's "
                "gap_limit or wait for the chain scanner (M5) to advance "
                "the next-receiving pointer."
            ),
        )
    return NextReceivingAddressResponse(
        address=address.address,
        derivation_path=address.derivation_path,
        derivation_index=address.derivation_index,
    )


# --- chain-aware endpoints (M5.2) -------------------------------------------


from pydantic import BaseModel as _BaseModel


class RescanResponse(_BaseModel):
    descriptor_id: UUID
    height_at_scan: int
    utxos_discovered: int
    utxos_pre_existing: int
    ledger_entries_created: int


class DescriptorUtxosResponse(_BaseModel):
    descriptor_id: UUID
    utxos: list


class DescriptorBalanceResponse(_BaseModel):
    descriptor_id: UUID
    confirmed_sats: int


@router.post(
    "/descriptors/{descriptor_id}/rescan",
    response_model=RescanResponse,
)
async def rescan_descriptor(
    descriptor_id: UUID,
    session: Session = Depends(get_db_session),
    node: NodeAdapter = Depends(get_node_adapter),
) -> RescanResponse:
    """Run a one-shot scan of bitcoind's UTXO set against this descriptor.

    Persists newly-discovered UTXOs, the OnChainTransactions that produced
    them, and a LedgerEntry per UTXO with `direction=INCOMING`. Re-runs are
    idempotent (UTXOs upsert by (txid, vout); LedgerEntries de-dupe per
    holding by source_reference).

    Synchronous in M5.2 — moved to a job queue in M5.3 once we wire the
    worker process for the live ZMQ listener.
    """
    descriptor = descriptor_repo.get_descriptor(session, descriptor_id)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")

    from tallykeep.services.chain_scan_service import ChainScanService

    service = ChainScanService(node)
    try:
        report = service.initial_scan(session, descriptor)
        session.commit()
    except NodeError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503, detail=f"bitcoind RPC failed: {exc}"
        ) from exc
    return RescanResponse(
        descriptor_id=report.descriptor_id,
        height_at_scan=report.height_at_scan,
        utxos_discovered=report.utxos_discovered,
        utxos_pre_existing=report.utxos_pre_existing,
        ledger_entries_created=report.ledger_entries_created,
    )


@router.get(
    "/descriptors/{descriptor_id}/utxos",
    response_model=DescriptorUtxosResponse,
)
async def list_descriptor_utxos(
    descriptor_id: UUID,
    only_unspent: bool = True,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> DescriptorUtxosResponse:
    if descriptor_repo.get_descriptor(session, descriptor_id) is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    from tallykeep.repositories import utxo as utxo_repo

    utxos = utxo_repo.list_for_descriptor(
        session,
        descriptor_id,
        only_unspent=only_unspent,
        limit=min(max(limit, 1), 200),
        offset=max(offset, 0),
    )
    return DescriptorUtxosResponse(
        descriptor_id=descriptor_id,
        utxos=[
            {
                "id": str(u.id),
                "txid": u.txid,
                "vout": u.vout,
                "value_sats": u.value_sats,
                "confirmation_height": u.confirmation_height,
                "is_frozen": u.is_frozen,
                "is_spent": u.is_spent,
                "hygiene_flags": [f.value for f in u.hygiene_flags],
            }
            for u in utxos
        ],
    )


@router.get(
    "/descriptors/{descriptor_id}/balance",
    response_model=DescriptorBalanceResponse,
)
async def descriptor_balance(
    descriptor_id: UUID,
    session: Session = Depends(get_db_session),
) -> DescriptorBalanceResponse:
    if descriptor_repo.get_descriptor(session, descriptor_id) is None:
        raise HTTPException(status_code=404, detail="Descriptor not found")
    from tallykeep.repositories import utxo as utxo_repo

    return DescriptorBalanceResponse(
        descriptor_id=descriptor_id,
        confirmed_sats=utxo_repo.descriptor_balance_sats(session, descriptor_id),
    )
