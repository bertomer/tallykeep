"""Declared-vs-observable security analysis — spec module 02 / 05.

For any non-Account Holding the analyzer derives an `ObservableSecurity`
view by parsing each attached descriptor. v1's coverage:

  - `inferred_custody_model`:
      - `wpkh(...)`, `pkh(...)`, `tr(...)` with one key  → SELF_SINGLE
      - `wsh(multi(...))`, `sh(multi(...))`, `tr(multi_a(...))` → SELF_MULTISIG
  - `inferred_multisig_parameters`: extracted from the `multi(k, ...)`
    fragment when present.
  - `inferred_timelock_blocks`: extracted from `older(N)` / `after(N)`
    miniscript fragments when present.
  - `inferred_signing_model`: requires runtime telemetry we don't ship in
    v1 (signing-pattern heuristics on transaction timing). Always
    `UNKNOWN` for now and treated as "no information" by the discrepancy
    detector — never as a contradiction.

Discrepancies follow the spec table verbatim. Each discrepancy carries a
templated message so the API can surface a human-readable explanation
without round-tripping the kind enum.

The analyzer is a pure function on declared + descriptors. Persistence
(if any) is a caller concern — we lean on /security being recomputed on
demand per spec ("derived view, recomputed on demand").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from tallykeep.domain.descriptor import Descriptor
from tallykeep.domain.enums import (
    CustodyModel,
    DiscrepancyKind,
    DiscrepancySeverity,
    HoldingType,
    SigningModel,
)
from tallykeep.domain.holding import Holding
from tallykeep.repositories import (
    descriptor as descriptor_repo,
    holding as holding_repo,
)


# --- typed result containers --------------------------------------------------


@dataclass(frozen=True)
class ObservableSecurity:
    """The on-chain-observable view of a Holding's security."""

    holding_id: UUID
    inferred_custody_model: CustodyModel
    inferred_signing_model: SigningModel
    inferred_multisig_parameters: tuple[int, int] | None
    inferred_timelock_blocks: int | None
    last_computed_at: datetime


@dataclass(frozen=True)
class Discrepancy:
    kind: DiscrepancyKind
    severity: DiscrepancySeverity
    message: str
    first_detected_at: datetime


@dataclass(frozen=True)
class SecurityAnalysisResult:
    holding_id: UUID
    declared_custody_model: CustodyModel | None
    declared_signing_model: SigningModel | None
    declared_inheritance_configured: bool
    observable: ObservableSecurity
    discrepancies: list[Discrepancy] = field(default_factory=list)


# --- descriptor parsing -------------------------------------------------------


_MULTI_PATTERN = re.compile(r"\b(multi|multi_a|sortedmulti|sortedmulti_a)\(\s*(\d+)\s*,([^)]*)\)")
_TIMELOCK_PATTERN = re.compile(r"\b(older|after)\(\s*(\d+)\s*\)")


@dataclass(frozen=True)
class _ParsedDescriptor:
    is_multisig: bool
    multisig_required: int | None
    multisig_total: int | None
    timelock_blocks: int | None


def _parse_descriptor(expression: str) -> _ParsedDescriptor:
    """Surface-level parse of a descriptor expression.

    We don't pull in BDK here because BDK's `Descriptor` parser doesn't
    expose multi-arity / timelock fragments in a stable shape across
    bdkpython versions. The regex is sufficient for the v1 inference
    surface and is straightforward to reason about.
    """
    multi_match = _MULTI_PATTERN.search(expression)
    is_multisig = multi_match is not None
    required = total = None
    if multi_match is not None:
        required = int(multi_match.group(2))
        # The keys list — count comma-separated entries, ignoring trailing whitespace.
        keys_blob = multi_match.group(3)
        total = sum(1 for part in keys_blob.split(",") if part.strip())

    timelock_match = _TIMELOCK_PATTERN.search(expression)
    timelock_blocks = int(timelock_match.group(2)) if timelock_match else None

    return _ParsedDescriptor(
        is_multisig=is_multisig,
        multisig_required=required,
        multisig_total=total,
        timelock_blocks=timelock_blocks,
    )


# --- inference ----------------------------------------------------------------


def _infer_observable(
    holding_id: UUID, descriptors: list[Descriptor]
) -> ObservableSecurity:
    """Combine all attached descriptors into one observable view.

    A Holding can have multiple Descriptors. v1's policy: if ANY descriptor
    is multisig, the holding is observable as multisig. Multisig
    parameters and timelocks come from the first multisig / timelocked
    descriptor (rare to have heterogeneous multisig configurations in v1;
    that's a v2 concern documented later).
    """
    parsed = [_parse_descriptor(d.expression) for d in descriptors]

    multisig_parsed = next((p for p in parsed if p.is_multisig), None)
    if multisig_parsed is not None:
        custody = CustodyModel.SELF_MULTISIG
        params: tuple[int, int] | None = None
        if multisig_parsed.multisig_required is not None and multisig_parsed.multisig_total is not None:
            params = (
                multisig_parsed.multisig_required,
                multisig_parsed.multisig_total,
            )
    else:
        custody = CustodyModel.SELF_SINGLE
        params = None

    timelock_parsed = next(
        (p for p in parsed if p.timelock_blocks is not None), None
    )
    timelock = timelock_parsed.timelock_blocks if timelock_parsed else None

    return ObservableSecurity(
        holding_id=holding_id,
        inferred_custody_model=custody,
        # Spec: leave UNKNOWN when we can't tell. v1 has no signing-pattern
        # heuristic, so always UNKNOWN.
        inferred_signing_model=SigningModel.UNKNOWN,
        inferred_multisig_parameters=params,
        inferred_timelock_blocks=timelock,
        last_computed_at=datetime.now(UTC),
    )


# --- discrepancy detection ----------------------------------------------------


_TEMPLATES: dict[DiscrepancyKind, tuple[DiscrepancySeverity, str]] = {
    DiscrepancyKind.CLAIMED_MULTISIG_BUT_SINGLE_KEY: (
        DiscrepancySeverity.HIGH,
        "This Holding is declared as multisig, but its descriptors are all "
        "single-key. The on-chain security is weaker than declared.",
    ),
    DiscrepancyKind.CLAIMED_SINGLE_BUT_OBSERVABLE_MULTISIG: (
        DiscrepancySeverity.INFORMATIONAL,
        "This Holding is declared as single-key, but its descriptor is "
        "multisig. Stronger than declared — the security check is "
        "informational, not a problem.",
    ),
    DiscrepancyKind.CLAIMED_OFFLINE_BUT_PATTERN_SUGGESTS_HOT: (
        DiscrepancySeverity.MEDIUM,
        "This Holding is declared with hardware-offline signing, but recent "
        "signing patterns suggest hot software signing.",
    ),
    DiscrepancyKind.CLAIMED_VAULT_NO_TIMELOCK_NO_MULTISIG: (
        DiscrepancySeverity.MEDIUM,
        "This Holding is declared as a Vault, but its descriptor has no "
        "timelock and no multisig protection. A Vault is normally expected "
        "to have at least one of those.",
    ),
    DiscrepancyKind.CLAIMED_INHERITANCE_NO_RECOVERY_PATH: (
        DiscrepancySeverity.LOW,
        "Inheritance is declared as configured for this Holding, but no "
        "observable recovery path (timelock to a recovery key, multi-key "
        "recovery branch, etc.) is detectable on-chain.",
    ),
}


def _detect_discrepancies(
    holding: Holding,
    declared_custody: CustodyModel | None,
    declared_signing: SigningModel | None,
    declared_inheritance_configured: bool,
    observable: ObservableSecurity,
) -> list[Discrepancy]:
    """Return the list of Discrepancy records for this holding's deltas."""
    out: list[Discrepancy] = []
    now = datetime.now(UTC)

    # 1) declared multisig vs observable single-key
    if (
        declared_custody == CustodyModel.SELF_MULTISIG
        and observable.inferred_custody_model == CustodyModel.SELF_SINGLE
    ):
        sev, msg = _TEMPLATES[DiscrepancyKind.CLAIMED_MULTISIG_BUT_SINGLE_KEY]
        out.append(
            Discrepancy(
                kind=DiscrepancyKind.CLAIMED_MULTISIG_BUT_SINGLE_KEY,
                severity=sev,
                message=msg,
                first_detected_at=now,
            )
        )

    # 2) declared single vs observable multisig (informational — the user understated)
    if (
        declared_custody == CustodyModel.SELF_SINGLE
        and observable.inferred_custody_model == CustodyModel.SELF_MULTISIG
    ):
        sev, msg = _TEMPLATES[DiscrepancyKind.CLAIMED_SINGLE_BUT_OBSERVABLE_MULTISIG]
        out.append(
            Discrepancy(
                kind=DiscrepancyKind.CLAIMED_SINGLE_BUT_OBSERVABLE_MULTISIG,
                severity=sev,
                message=msg,
                first_detected_at=now,
            )
        )

    # 3) hardware-offline declared but pattern suggests hot — v1 has no
    #    signing-pattern telemetry, so this discrepancy never fires in v1
    #    (kept here documented; populated when M9+ adds the heuristic).

    # 4) Vault declared but no timelock and no multisig
    if (
        holding.holding_type == HoldingType.VAULT
        and observable.inferred_timelock_blocks is None
        and observable.inferred_custody_model != CustodyModel.SELF_MULTISIG
    ):
        sev, msg = _TEMPLATES[DiscrepancyKind.CLAIMED_VAULT_NO_TIMELOCK_NO_MULTISIG]
        out.append(
            Discrepancy(
                kind=DiscrepancyKind.CLAIMED_VAULT_NO_TIMELOCK_NO_MULTISIG,
                severity=sev,
                message=msg,
                first_detected_at=now,
            )
        )

    # 5) inheritance declared but no observable recovery path
    if (
        declared_inheritance_configured
        and observable.inferred_timelock_blocks is None
        and observable.inferred_custody_model != CustodyModel.SELF_MULTISIG
    ):
        sev, msg = _TEMPLATES[DiscrepancyKind.CLAIMED_INHERITANCE_NO_RECOVERY_PATH]
        out.append(
            Discrepancy(
                kind=DiscrepancyKind.CLAIMED_INHERITANCE_NO_RECOVERY_PATH,
                severity=sev,
                message=msg,
                first_detected_at=now,
            )
        )

    return out


# --- top-level entry point ----------------------------------------------------


def analyze_holding(
    session: Session, holding_id: UUID
) -> SecurityAnalysisResult | None:
    """Run the full declared-vs-observable analysis for `holding_id`.

    Returns None if the holding doesn't exist. Account holdings (no
    descriptors) get an empty discrepancy list with `inferred_custody_model
    = THIRD_PARTY` — observable on a custodial holding is "we don't see
    on-chain history at all."
    """
    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(
        session, holding_id
    )
    holding = holding_repo.get(
        session, holding_id, descriptor_ids=descriptor_ids
    )
    if holding is None:
        return None

    declared_custody = holding.declared_security.custody_model
    declared_signing = holding.declared_security.signing_model
    declared_inheritance_configured = (
        holding.declared_security.inheritance_configured
    )

    descriptors: list[Descriptor] = (
        descriptor_repo.list_descriptors_for_holding(session, holding_id)
        if holding.holding_type != HoldingType.ACCOUNT
        else []
    )

    if holding.holding_type == HoldingType.ACCOUNT:
        observable = ObservableSecurity(
            holding_id=holding_id,
            inferred_custody_model=CustodyModel.THIRD_PARTY,
            inferred_signing_model=SigningModel.NOT_APPLICABLE,
            inferred_multisig_parameters=None,
            inferred_timelock_blocks=None,
            last_computed_at=datetime.now(UTC),
        )
        return SecurityAnalysisResult(
            holding_id=holding_id,
            declared_custody_model=declared_custody,
            declared_signing_model=declared_signing,
            declared_inheritance_configured=declared_inheritance_configured,
            observable=observable,
            discrepancies=[],
        )

    observable = _infer_observable(holding_id, descriptors)
    discrepancies = _detect_discrepancies(
        holding,
        declared_custody=declared_custody,
        declared_signing=declared_signing,
        declared_inheritance_configured=declared_inheritance_configured,
        observable=observable,
    )

    return SecurityAnalysisResult(
        holding_id=holding_id,
        declared_custody_model=declared_custody,
        declared_signing_model=declared_signing,
        declared_inheritance_configured=declared_inheritance_configured,
        observable=observable,
        discrepancies=discrepancies,
    )


__all__ = [
    "Discrepancy",
    "ObservableSecurity",
    "SecurityAnalysisResult",
    "analyze_holding",
]
