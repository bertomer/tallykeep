"""UTXO endpoints — spec module 04.

M5.2 implements list / freeze / unfreeze / hygiene. Hygiene currently returns
the empty hygiene_flags list persisted at scan time; the actual flag
computation lands in M5.4.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.repositories import utxo as utxo_repo


router = APIRouter(tags=["utxos"])


class UtxoSummary(BaseModel):
    id: UUID
    descriptor_id: UUID
    address_id: UUID
    txid: str
    vout: int
    value_sats: int
    confirmation_height: int | None
    is_frozen: bool
    is_spent: bool
    hygiene_flags: list[str]


class UtxoListResponse(BaseModel):
    utxos: list[UtxoSummary]


class UtxoHygieneResponse(BaseModel):
    utxo_id: UUID
    hygiene_flags: list[str]
    # M5.4 will populate per-flag explanations and recommendations.


def _to_summary(u) -> UtxoSummary:  # type: ignore[no-untyped-def]
    return UtxoSummary(
        id=u.id,
        descriptor_id=u.descriptor_id,
        address_id=u.address_id,
        txid=u.txid,
        vout=u.vout,
        value_sats=u.value_sats,
        confirmation_height=u.confirmation_height,
        is_frozen=u.is_frozen,
        is_spent=u.is_spent,
        hygiene_flags=[f.value for f in u.hygiene_flags],
    )


@router.get("/utxos", response_model=UtxoListResponse)
async def list_utxos(
    descriptor_id: UUID | None = None,
    holding_id: UUID | None = None,
    min_value_sats: int | None = None,
    frozen: bool | None = None,
    only_unspent: bool = True,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_db_session),
) -> UtxoListResponse:
    utxos = utxo_repo.list_filtered(
        session,
        descriptor_id=descriptor_id,
        holding_id=holding_id,
        min_value_sats=min_value_sats,
        is_frozen=frozen,
        only_unspent=only_unspent,
        limit=limit,
        offset=offset,
    )
    return UtxoListResponse(utxos=[_to_summary(u) for u in utxos])


@router.post("/utxos/{utxo_id}/freeze", response_model=UtxoSummary)
async def freeze_utxo(
    utxo_id: UUID, session: Session = Depends(get_db_session)
) -> UtxoSummary:
    updated = utxo_repo.freeze(session, utxo_id, frozen=True)
    if updated is None:
        raise HTTPException(status_code=404, detail="UTXO not found")
    session.commit()
    return _to_summary(updated)


@router.post("/utxos/{utxo_id}/unfreeze", response_model=UtxoSummary)
async def unfreeze_utxo(
    utxo_id: UUID, session: Session = Depends(get_db_session)
) -> UtxoSummary:
    updated = utxo_repo.freeze(session, utxo_id, frozen=False)
    if updated is None:
        raise HTTPException(status_code=404, detail="UTXO not found")
    session.commit()
    return _to_summary(updated)


@router.get("/utxos/{utxo_id}/hygiene", response_model=UtxoHygieneResponse)
async def utxo_hygiene(
    utxo_id: UUID, session: Session = Depends(get_db_session)
) -> UtxoHygieneResponse:
    utxo = utxo_repo.get(session, utxo_id)
    if utxo is None:
        raise HTTPException(status_code=404, detail="UTXO not found")
    return UtxoHygieneResponse(
        utxo_id=utxo.id,
        hygiene_flags=[f.value for f in utxo.hygiene_flags],
    )
