"""Security and blueprint analysis endpoints — spec module 04 / 05.

M5.5 implements the security check (declared vs observable) and the
blueprint summary (hygiene-flag rollups + recommendations). UTXO-level
blueprint and the manual-recompute job are minimal pass-throughs.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(prefix="/analysis", tags=["analysis"])


# --- response shapes ---------------------------------------------------------


class DeclaredSecurity(BaseModel):
    custody_model: str | None
    signing_model: str | None
    inheritance_configured: bool


class ObservableSecurityOut(BaseModel):
    inferred_custody_model: str
    inferred_signing_model: str
    inferred_multisig_parameters: tuple[int, int] | None
    inferred_timelock_blocks: int | None
    last_computed_at: str


class DiscrepancyOut(BaseModel):
    kind: str
    severity: str
    message: str
    first_detected_at: str


class HoldingSecurityResponse(BaseModel):
    declared: DeclaredSecurity
    observable: ObservableSecurityOut
    discrepancies: list[DiscrepancyOut]


class HygieneRecommendation(BaseModel):
    flag: str
    severity: str
    message: str


class BlueprintSummary(BaseModel):
    address_reuse_count: int
    dust_utxo_count: int
    round_number_outputs: int
    suspected_consolidations: int


class HoldingBlueprintResponse(BaseModel):
    summary: BlueprintSummary
    recommendations: list[HygieneRecommendation]


# --- endpoints ---------------------------------------------------------------


@router.get(
    "/holding/{holding_id}/security",
    response_model=HoldingSecurityResponse,
)
async def holding_security(
    holding_id: UUID, session: Session = Depends(get_db_session)
) -> HoldingSecurityResponse:
    from tallykeep.services.analysis_service import analyze_holding

    result = analyze_holding(session, holding_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Holding not found")

    return HoldingSecurityResponse(
        declared=DeclaredSecurity(
            custody_model=(
                result.declared_custody_model.value
                if result.declared_custody_model
                else None
            ),
            signing_model=(
                result.declared_signing_model.value
                if result.declared_signing_model
                else None
            ),
            inheritance_configured=result.declared_inheritance_configured,
        ),
        observable=ObservableSecurityOut(
            inferred_custody_model=result.observable.inferred_custody_model.value,
            inferred_signing_model=result.observable.inferred_signing_model.value,
            inferred_multisig_parameters=result.observable.inferred_multisig_parameters,
            inferred_timelock_blocks=result.observable.inferred_timelock_blocks,
            last_computed_at=result.observable.last_computed_at.isoformat(),
        ),
        discrepancies=[
            DiscrepancyOut(
                kind=d.kind.value,
                severity=d.severity.value,
                message=d.message,
                first_detected_at=d.first_detected_at.isoformat(),
            )
            for d in result.discrepancies
        ],
    )


@router.get(
    "/holding/{holding_id}/blueprint",
    response_model=HoldingBlueprintResponse,
)
async def holding_blueprint(
    holding_id: UUID, session: Session = Depends(get_db_session)
) -> HoldingBlueprintResponse:
    """Aggregate hygiene rollups + per-flag recommendations for a Holding.

    Walks every UTXO attached to every Descriptor of the Holding, sums the
    per-flag counts, and emits one recommendation per flag *kind* present
    (we don't repeat the same recommendation for every UTXO). Severity
    follows spec module 05.
    """
    from sqlalchemy import select

    from tallykeep.models import DescriptorRow, HoldingRow, UTXORow

    if session.get(HoldingRow, holding_id) is None:
        raise HTTPException(status_code=404, detail="Holding not found")

    descriptor_ids = session.execute(
        select(DescriptorRow.id).where(DescriptorRow.holding_id == holding_id)
    ).scalars().all()

    counts: dict[str, int] = {
        "address_reused": 0,
        "dust": 0,
        "round_number": 0,
        "suspected_consolidation": 0,
    }
    if descriptor_ids:
        rows = (
            session.execute(
                select(UTXORow).where(UTXORow.descriptor_id.in_(descriptor_ids))
            )
            .scalars()
            .all()
        )
        for row in rows:
            for flag in row.hygiene_flags or []:
                if flag in counts:
                    counts[flag] += 1

    severity_by_flag = {
        "address_reused": "medium",
        "dust": "high",
        "round_number": "low",
        "suspected_consolidation": "medium",
    }
    messages = {
        "address_reused": (
            "One or more addresses on this Holding have been reused. "
            "Derive new addresses for future receipts."
        ),
        "dust": (
            "Some UTXOs on this Holding are below the economic spend "
            "threshold at the current fee rate."
        ),
        "round_number": (
            "Some outputs are round-number values, suggestive of a "
            "fiat-denominated payment that reduces privacy."
        ),
        "suspected_consolidation": (
            "One or more UTXOs are the result of consolidating prior "
            "UTXOs. Those prior UTXOs are now publicly linked together."
        ),
    }

    recommendations: list[HygieneRecommendation] = []
    for flag, count in counts.items():
        if count == 0:
            continue
        recommendations.append(
            HygieneRecommendation(
                flag=flag,
                severity=severity_by_flag[flag],
                message=messages[flag],
            )
        )

    return HoldingBlueprintResponse(
        summary=BlueprintSummary(
            address_reuse_count=counts["address_reused"],
            dust_utxo_count=counts["dust"],
            round_number_outputs=counts["round_number"],
            suspected_consolidations=counts["suspected_consolidation"],
        ),
        recommendations=recommendations,
    )


@router.get("/utxo/{utxo_id}", status_code=501)
async def utxo_blueprint(utxo_id: UUID) -> JSONResponse:
    """Per-UTXO blueprint (richer than the /utxos/{id}/hygiene shape).

    Currently a stub; the per-UTXO hygiene endpoint already covers the
    flag list + recommendations. v2 will add per-flag historic context
    (when did the address first see reuse, what was the fee rate when DUST
    was computed, etc.) — not load-bearing for v1.
    """
    return not_implemented_response(
        milestone="v2", route="GET /api/v1/analysis/utxo/{id}"
    )


@router.post("/recompute", status_code=501)
async def recompute_analysis() -> JSONResponse:
    """Trigger a background recompute job.

    Recomputation is currently fully on-demand (every /security or
    /blueprint request runs fresh), so the explicit recompute endpoint is
    redundant in v1. M9 wires the periodic 24h scheduler.
    """
    return not_implemented_response(
        milestone="M9", route="POST /api/v1/analysis/recompute"
    )
