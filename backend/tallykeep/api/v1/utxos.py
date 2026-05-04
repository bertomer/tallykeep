"""UTXO endpoints — spec module 04.

M5.2 implements list / freeze / unfreeze. M5.4 adds hygiene flag
computation at UTXO detection time and the recommendation generator on
the hygiene endpoint.
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


class HygieneRecommendation(BaseModel):
    flag: str
    severity: str
    message: str


class UtxoHygieneResponse(BaseModel):
    utxo_id: UUID
    hygiene_flags: list[str]
    recommendations: list[HygieneRecommendation]


_FLAG_SEVERITY: dict[str, str] = {
    "address_reused": "medium",
    "dust": "high",
    "round_number": "low",
    "suspected_consolidation": "medium",
}


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
    """Return the persisted hygiene flags plus a per-flag recommendation.

    Recommendations follow spec module 05's templates. The endpoint is
    advisory — callers may show, dismiss, or surface them however they
    like.
    """
    from tallykeep.models import AddressRow, UTXORow

    utxo = utxo_repo.get(session, utxo_id)
    if utxo is None:
        raise HTTPException(status_code=404, detail="UTXO not found")

    flags = [f.value for f in utxo.hygiene_flags]
    recommendations: list[HygieneRecommendation] = []

    # Look up the address text once if any flag needs it for templating.
    if "address_reused" in flags:
        address_row = session.get(AddressRow, utxo.address_id)
        addr_text = address_row.address if address_row is not None else "?"
        # Count distinct txids touching this address — that's the "reuse depth".
        from sqlalchemy import select as sa_select

        n = (
            session.execute(
                sa_select(UTXORow.txid)
                .where(UTXORow.address_id == utxo.address_id)
                .distinct()
            )
            .scalars()
            .all()
        )
        recommendations.append(
            HygieneRecommendation(
                flag="address_reused",
                severity=_FLAG_SEVERITY["address_reused"],
                message=(
                    f"Address {addr_text} has been used in {len(n)} distinct "
                    f"transactions. Derive a new address for future receipts."
                ),
            )
        )

    if "dust" in flags:
        recommendations.append(
            HygieneRecommendation(
                flag="dust",
                severity=_FLAG_SEVERITY["dust"],
                message=(
                    f"UTXO of {utxo.value_sats} sats is below the economic spend "
                    f"threshold at the current fee rate. Consolidating it would "
                    f"cost more than its value."
                ),
            )
        )

    if "round_number" in flags:
        recommendations.append(
            HygieneRecommendation(
                flag="round_number",
                severity=_FLAG_SEVERITY["round_number"],
                message=(
                    f"Output {utxo.vout} of transaction {utxo.txid[:12]}… is a "
                    f"round-number value, which may indicate a fiat-denominated "
                    f"payment and reduce privacy."
                ),
            )
        )

    if "suspected_consolidation" in flags:
        recommendations.append(
            HygieneRecommendation(
                flag="suspected_consolidation",
                severity=_FLAG_SEVERITY["suspected_consolidation"],
                message=(
                    "This UTXO is the result of consolidating several prior "
                    "UTXOs. All those prior UTXOs are now publicly linked to "
                    "your wallet."
                ),
            )
        )

    return UtxoHygieneResponse(
        utxo_id=utxo.id,
        hygiene_flags=flags,
        recommendations=recommendations,
    )
