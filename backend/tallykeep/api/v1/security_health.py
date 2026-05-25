"""Security health endpoints (ADR-0019).

GET  /api/v1/security_health/items?state=open|history
POST /api/v1/security_health/items/{id}/resolve
POST /api/v1/security_health/items/{id}/revive
POST /api/v1/security_health/fix_metadata/{holding_id}
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import (
    DescriptorAdapter,
    DescriptorParseError,
    UnsupportedDescriptorError,
)
from tallykeep.api.dependencies import get_db_session, get_event_bus
from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.repositories import security_health as security_health_repo
from tallykeep.services import security_health_service
from tallykeep.services.security_health_service import (
    InvalidStateTransition,
    ReviveNotAllowed,
    SecurityHealthServiceError,
)


router = APIRouter(prefix="/security_health", tags=["security_health"])

_ADAPTER = DescriptorAdapter()
_FINGERPRINT_RE = re.compile(r'\[([0-9a-fA-F]{8})[/\]]')

_VALID_RESOLVE_STATES = {"resolved_by_fix", "dismissed_intentional", "acknowledged"}


# --- response shape ----------------------------------------------------------


class SecurityHealthItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_type: str
    holding_id: str | None
    state: str
    severity: str
    created_at: str
    resolved_at: str | None
    dismissal_reason: str | None
    raw_context: dict[str, Any]


def _item_out(item) -> SecurityHealthItemOut:  # type: ignore[no-untyped-def]
    return SecurityHealthItemOut(
        id=str(item.id),
        item_type=item.item_type,
        holding_id=str(item.holding_id) if item.holding_id else None,
        state=item.state,
        severity=item.severity,
        created_at=item.created_at.isoformat(),
        resolved_at=item.resolved_at.isoformat() if item.resolved_at else None,
        dismissal_reason=item.dismissal_reason,
        raw_context=item.raw_context,
    )


# --- request bodies ----------------------------------------------------------


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str
    dismissal_reason: str | None = Field(default=None, max_length=500)


class FixMetadataReexportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descriptor_expression: str = Field(min_length=10)
    network: str = Field(default="mainnet")


class FixMetadataManualRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    master_fingerprint: str = Field(
        min_length=8, max_length=8, pattern=r"^[0-9a-fA-F]{8}$"
    )
    derivation_path: str = Field(
        default="m/84'/0'/0'",
        pattern=r"^m(/\d+'?)*$",
    )
    network: str = Field(default="mainnet")


class FixMetadataResponse(BaseModel):
    success: bool
    matched_addresses: int
    error: str | None = None


# --- endpoints ---------------------------------------------------------------


@router.get("/items", response_model=list[SecurityHealthItemOut])
async def list_items(
    state: str = "open",
    session: Session = Depends(get_db_session),
) -> list[SecurityHealthItemOut]:
    if state not in ("open", "history"):
        raise HTTPException(status_code=422, detail="state must be 'open' or 'history'")
    if state == "open":
        items = security_health_repo.list_open(session, include_application_level=True)
    else:
        items = security_health_repo.list_history(session)
    return [_item_out(i) for i in items]


@router.post("/items/{item_id}/resolve", response_model=SecurityHealthItemOut)
async def resolve_item(
    item_id: UUID,
    body: ResolveRequest,
    session: Session = Depends(get_db_session),
    bus: EventBus | None = Depends(get_event_bus),
) -> SecurityHealthItemOut:
    if body.state not in _VALID_RESOLVE_STATES:
        raise HTTPException(
            status_code=422,
            detail=f"state must be one of {sorted(_VALID_RESOLVE_STATES)}",
        )
    try:
        item = security_health_service.resolve_item(
            session,
            item_id,
            new_state=body.state,
            dismissal_reason=body.dismissal_reason,
            bus=bus,
        )
    except SecurityHealthServiceError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=422, detail=msg) from exc
    return _item_out(item)


@router.post("/items/{item_id}/revive", response_model=SecurityHealthItemOut)
async def revive_item(
    item_id: UUID,
    session: Session = Depends(get_db_session),
    bus: EventBus | None = Depends(get_event_bus),
) -> SecurityHealthItemOut:
    try:
        item = security_health_service.revive_item(session, item_id, bus=bus)
    except ReviveNotAllowed as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "revive_not_allowed_on_system_verified", "message": str(exc)},
        ) from exc
    except SecurityHealthServiceError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg) from exc
        raise HTTPException(status_code=422, detail=msg) from exc
    return _item_out(item)


@router.post(
    "/fix_metadata/{holding_id}/reexport",
    response_model=FixMetadataResponse,
)
async def fix_metadata_reexport(
    holding_id: UUID,
    body: FixMetadataReexportRequest,
    session: Session = Depends(get_db_session),
    bus: EventBus | None = Depends(get_event_bus),
) -> FixMetadataResponse:
    """Path A: accept a re-exported descriptor, verify addresses, update descriptor."""
    return _apply_fix_metadata(
        session,
        holding_id=holding_id,
        descriptor_expression=body.descriptor_expression,
        network=body.network,
        bus=bus,
    )


@router.post(
    "/fix_metadata/{holding_id}/manual",
    response_model=FixMetadataResponse,
)
async def fix_metadata_manual(
    holding_id: UUID,
    body: FixMetadataManualRequest,
    session: Session = Depends(get_db_session),
    bus: EventBus | None = Depends(get_event_bus),
) -> FixMetadataResponse:
    """Path B: manual fingerprint + derivation path entry; reconstruct expression."""
    # We need the existing descriptor expression to graft the origin metadata onto it.
    from tallykeep.repositories import descriptor as descriptor_repo

    descriptors = descriptor_repo.list_descriptors_for_holding(session, holding_id)
    if not descriptors:
        raise HTTPException(status_code=404, detail="No descriptor found for this Holding")

    # Graft the origin bracket onto the existing descriptor.
    existing_expr = descriptors[0].expression
    network = body.network

    # The existing expression may already have or lack origin brackets.
    # We replace any key without origin with the supplied one.
    fingerprint = body.master_fingerprint.lower()
    deriv_path = body.derivation_path  # e.g. m/84'/0'/0'

    # Strip "m/" from derivation_path for the bracket format.
    path_suffix = deriv_path[2:] if deriv_path.startswith("m/") else deriv_path

    new_expression = _graft_origin(existing_expr, fingerprint, path_suffix)

    return _apply_fix_metadata(
        session,
        holding_id=holding_id,
        descriptor_expression=new_expression,
        network=network,
        bus=bus,
    )


# --- helpers -----------------------------------------------------------------


def _graft_origin(expression: str, fingerprint: str, path: str) -> str:
    """Insert [fingerprint/path] origin into a descriptor that lacks it.

    Replaces the key string (xpub.../path) with ([fingerprint/path]xpub.../path).
    Handles both bare xpub and already-bracketed expressions (no-op on the latter).
    """
    # If already has a fingerprint bracket, return as-is.
    if _FINGERPRINT_RE.search(expression):
        return expression
    # Find the xpub/tpub in the expression and insert the origin bracket before it.
    return re.sub(
        r'(xpub[A-Za-z0-9]+|zpub[A-Za-z0-9]+|tpub[A-Za-z0-9]+)',
        lambda m: f"[{fingerprint}/{path}]{m.group(0)}",
        expression,
        count=1,
    )


def _apply_fix_metadata(
    session: Session,
    *,
    holding_id: UUID,
    descriptor_expression: str,
    network: str,
    bus: "EventBus | None",
) -> FixMetadataResponse:
    """Shared logic for both fix-metadata paths."""
    from tallykeep.repositories import descriptor as descriptor_repo
    from tallykeep.models.descriptor import AddressRow, DescriptorRow
    import sqlalchemy as sa

    # 1. Validate the new descriptor has origin metadata.
    if not _FINGERPRINT_RE.search(descriptor_expression):
        return FixMetadataResponse(
            success=False,
            matched_addresses=0,
            error="The provided descriptor does not contain key-origin metadata (e.g. [fingerprint/path]). Re-export with full origin from your hardware wallet.",
        )

    # 2. Parse the new descriptor.
    try:
        parsed = _ADAPTER.parse(descriptor_expression, network, allow_multisig=True)
    except (DescriptorParseError, UnsupportedDescriptorError) as exc:
        return FixMetadataResponse(
            success=False,
            matched_addresses=0,
            error=f"Descriptor parse error: {exc}",
        )

    # 3. Fetch the stored addresses for this Holding (first descriptor).
    descriptors = descriptor_repo.list_descriptors_for_holding(session, holding_id)
    if not descriptors:
        return FixMetadataResponse(
            success=False,
            matched_addresses=0,
            error="No descriptor found for this Holding.",
        )
    descriptor = descriptors[0]

    stored_address_rows = (
        session.query(AddressRow)
        .filter(AddressRow.descriptor_id == descriptor.id, AddressRow.is_change.is_(False))
        .order_by(AddressRow.derivation_index)
        .limit(20)
        .all()
    )
    if not stored_address_rows:
        return FixMetadataResponse(
            success=False,
            matched_addresses=0,
            error="No watched addresses found — cannot verify the descriptor.",
        )
    stored_addresses = {r.address for r in stored_address_rows}
    check_count = len(stored_address_rows)

    # 4. Derive the first N addresses from the new descriptor.
    try:
        derived = _ADAPTER.derive_addresses(
            descriptor_expression, network, count=check_count, allow_multisig=True
        )
    except Exception as exc:  # noqa: BLE001
        return FixMetadataResponse(
            success=False,
            matched_addresses=0,
            error=f"Address derivation failed: {exc}",
        )

    derived_addresses = {d.address for d in derived}
    matched = len(stored_addresses & derived_addresses)

    if matched < min(check_count, 1):
        return FixMetadataResponse(
            success=False,
            matched_addresses=matched,
            error="Address mismatch: the provided descriptor does not match the addresses TallyKeep is watching. Check that you exported from the correct wallet.",
        )

    # 5. Update the descriptor expression in place.
    desc_row = session.get(DescriptorRow, descriptor.id)
    if desc_row is not None:
        desc_row.expression = descriptor_expression
        session.flush()

    # 6. Update holding subtype_data to mark signing_metadata_present = True.
    from tallykeep.models.holding import HoldingRow
    holding_row = session.get(HoldingRow, holding_id)
    if holding_row is not None:
        data = dict(holding_row.subtype_data or {})
        data["signing_metadata_present"] = True
        holding_row.subtype_data = data
        session.flush()

    # 7. Resolve any open missing_signing_metadata items for this Holding.
    security_health_service.resolve_missing_metadata_items_for_holding(
        session, holding_id, bus=bus
    )

    return FixMetadataResponse(success=True, matched_addresses=matched)
