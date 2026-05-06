"""Address endpoints — spec module 04 / M9."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.repositories import descriptor as descriptor_repo


router = APIRouter(tags=["addresses"])


class AddressPatch(BaseModel):
    label: str | None = None


class AddressOut(BaseModel):
    id: UUID
    address: str
    derivation_path: str | None
    derivation_index: int | None
    is_change: bool
    label: str | None
    first_seen_height: int | None


@router.patch("/addresses/{address_id}", response_model=AddressOut)
async def patch_address(
    address_id: UUID,
    body: AddressPatch,
    session: Session = Depends(get_db_session),
) -> AddressOut:
    updated = descriptor_repo.update_address_label(session, address_id, body.label)
    if updated is None:
        raise HTTPException(status_code=404, detail="Address not found")
    session.commit()
    return AddressOut(
        id=updated.id,
        address=updated.address,
        derivation_path=updated.derivation_path,
        derivation_index=updated.derivation_index,
        is_change=updated.is_change,
        label=updated.label,
        first_seen_height=updated.first_seen_height,
    )
