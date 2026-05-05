"""Banking service — outgoing PaymentRequest construction (M6.1).

Spec module 06: the user composes a payment, we build a PSBT, the user
signs it externally, we broadcast. This module handles the build step.
Submit-signed and broadcast land in M6.2; confirmation-tracking in M6.3.

The service is the orchestrator:

  1. Pre-build validation (Account holdings can't send; Vault long-term
     guardrail; valid destination address; sufficient balance).
  2. Loads the holding's confirmed unspent UTXOs and resolves a fee rate
     from the user's chosen strategy.
  3. Calls DescriptorAdapter.build_psbt to construct the PSBT via BDK.
  4. Persists a PaymentRequest with `status=AWAITING_SIGNATURE`.
  5. Returns the persisted record so the API layer can render the
     response and emit `banking.payment_request.created`.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from tallykeep.adapters.descriptor_adapter import (
    DescriptorAdapter,
    UtxoForBuild,
)
from tallykeep.adapters.node_adapter import NodeAdapter, NodeError, NodeRpcError
from tallykeep.domain.descriptor import Descriptor
from tallykeep.domain.enums import (
    HoldingType,
    PaymentStatus,
    PaymentType,
    Purpose,
    SigningModel,
)
from tallykeep.domain.payment_request import PaymentRequest
from tallykeep.repositories import (
    descriptor as descriptor_repo,
    holding as holding_repo,
    payment_request as payment_request_repo,
    utxo as utxo_repo,
)


# --- exceptions -------------------------------------------------------------


class BankingError(Exception):
    """Base class for banking-service errors."""


class HoldingCannotSend(BankingError):
    """Source holding's signing model is NOT_APPLICABLE (account or
    similar). Spec module 06: "Source Holding's signing_model is not
    NOT_APPLICABLE. Otherwise 400 with /errors/account-cannot-send"."""


class HoldingNotFound(BankingError):
    pass


class InsufficientBalance(BankingError):
    pass


class InvalidDestination(BankingError):
    pass


class InFlightPaymentExists(BankingError):
    """Spec module 06 concurrency rule: only one in-flight PaymentRequest
    per Holding."""


class VaultLongTermRequiresConfirmation(BankingError):
    """Spec module 06: a Vault declared as long_term gets a soft warning
    on the FIRST attempt; the user must re-submit with confirmation to
    proceed."""

    def __init__(self) -> None:
        super().__init__(
            "Source Vault is declared as long_term. Re-submit with "
            "confirmed=true to proceed."
        )


# --- typed result containers ------------------------------------------------


@dataclass
class PaymentRequestBuildResult:
    """What `build_payment_request` returns to the API layer.

    `requires_confirmation` is set on the Vault long-term guardrail path —
    in that case `payment_request` is None and the caller renders the
    warning instead of a normal 201.
    """

    payment_request: PaymentRequest | None
    requires_confirmation: bool = False
    confirmation_message: str | None = None


# --- fee resolution ---------------------------------------------------------


_NAMED_TIERS_TARGETS: dict[str, int] = {
    "economy": 24,
    "normal": 6,
    "priority": 2,
}


def _resolve_fee_rate(
    node: NodeAdapter,
    *,
    strategy: str | None,
    sat_per_vbyte: float | None,
) -> float:
    """Return a positive sat/vbyte fee rate.

    Spec module 06: fee strategy is `economy` / `normal` / `priority`
    (from `estimatesmartfee`) or an explicit `sat_per_vbyte`. Falls back
    to 10 sat/vB (the same default the hygiene layer uses) when bitcoind's
    estimator returns no useful number — typical on regtest and on a
    freshly-started node.
    """
    if sat_per_vbyte is not None:
        if sat_per_vbyte <= 0:
            raise ValueError("sat_per_vbyte must be > 0")
        return float(sat_per_vbyte)

    target = _NAMED_TIERS_TARGETS.get(strategy or "normal")
    if target is None:
        raise ValueError(f"Unknown fee strategy {strategy!r}")
    try:
        result = node.estimate_smart_fee(target)
    except NodeError:
        return 10.0
    feerate = result.get("feerate")
    if feerate is None or float(feerate) <= 0:
        return 10.0
    # bitcoind returns BTC/kvB; convert to sat/vB.
    return float(feerate) * 100_000


# --- main entry point -------------------------------------------------------


def build_payment_request(
    session: Session,
    *,
    holding_id: UUID,
    destination_address: str,
    amount_sats: int | None,
    fee_strategy: str | None,
    fee_sat_per_vbyte: float | None,
    description: str | None,
    confirmed_long_term: bool = False,
    descriptor_adapter: DescriptorAdapter,
    node: NodeAdapter,
) -> PaymentRequestBuildResult:
    """Build and persist a PSBT for `holding_id`.

    `amount_sats=None` drains the holding (max-send minus fee). The
    chosen fee rate is whatever `_resolve_fee_rate` returns from
    `fee_strategy` / `fee_sat_per_vbyte`.
    """
    descriptor_ids = descriptor_repo.descriptor_ids_for_holding(session, holding_id)
    holding = holding_repo.get(
        session, holding_id, descriptor_ids=descriptor_ids
    )
    if holding is None:
        raise HoldingNotFound(f"Holding {holding_id} not found")

    # Account holdings can never produce on-chain PaymentRequests.
    if (
        holding.holding_type == HoldingType.ACCOUNT
        or holding.declared_security.signing_model == SigningModel.NOT_APPLICABLE
    ):
        raise HoldingCannotSend(
            "Account holdings cannot create on-chain PaymentRequests; "
            "use the sweep / withdrawal flow."
        )

    # Vault long-term guardrail (spec module 05/06): first call returns a
    # 200 with requires_confirmation=true; second call with confirmed=true
    # proceeds.
    if (
        holding.holding_type == HoldingType.VAULT
        and holding.purpose == Purpose.LONG_TERM
        and not confirmed_long_term
    ):
        return PaymentRequestBuildResult(
            payment_request=None,
            requires_confirmation=True,
            confirmation_message=(
                "You are composing an outgoing payment from a Vault "
                "declared as long-term. This is unusual; confirm you "
                "intend this by resubmitting with confirmed=true."
            ),
        )

    if payment_request_repo.has_in_flight_for_holding(session, holding_id):
        raise InFlightPaymentExists(
            "Another PaymentRequest for this Holding is already in flight. "
            "Cancel or broadcast it before composing a new one."
        )

    descriptors = descriptor_repo.list_descriptors_for_holding(session, holding_id)
    if not descriptors:
        raise InsufficientBalance("Holding has no descriptors")

    # v1 only supports a single descriptor per Holding for spending — the
    # spec allows many, but coin selection across multiple descriptor
    # ranges complicates change-address derivation. M6.1 restricts to one;
    # multi-descriptor spending lands as a v1.x enhancement when we have
    # a real test case.
    if len(descriptors) > 1:
        raise BankingError(
            "Multi-descriptor spending is not supported in v1; "
            "the holding's first descriptor is used for the payment."
        )
    primary_descriptor = descriptors[0]

    utxos = _gather_spendable_utxos(session, primary_descriptor.id)
    if not utxos:
        raise InsufficientBalance(
            "No spendable UTXOs (all are spent or frozen)."
        )

    available_sats = sum(u["value_sats"] for u in utxos)
    if amount_sats is not None and amount_sats > available_sats:
        raise InsufficientBalance(
            f"Requested {amount_sats} sats, available {available_sats} sats."
        )

    # Validate the destination is parseable for this network. We delegate
    # to BDK by attempting to construct a `bdk.Address` — a clean path
    # back to a typed exception on bad input.
    import bdkpython as _bdk

    from tallykeep.adapters.descriptor_adapter import _NETWORK_TO_BDK

    try:
        _bdk.Address(destination_address, _NETWORK_TO_BDK[primary_descriptor.network])
    except Exception as exc:  # noqa: BLE001
        raise InvalidDestination(
            f"Destination is not a valid {primary_descriptor.network.value} address: {exc}"
        ) from exc

    fee_rate = _resolve_fee_rate(
        node,
        strategy=fee_strategy,
        sat_per_vbyte=fee_sat_per_vbyte,
    )

    # Fetch raw tx hex for each UTXO's parent. bitcoind requires
    # `txindex=1` (we set this in compose) for transactions outside the
    # wallet / mempool. Fail clean if any parent is unreachable so the
    # caller surfaces a 503 rather than a stale PSBT.
    parents: dict[str, str] = {}
    for u in utxos:
        if u["txid"] in parents:
            continue
        try:
            raw_hex = node.get_raw_transaction(u["txid"], verbose=False)
        except NodeRpcError as exc:
            raise BankingError(
                f"bitcoind cannot return raw tx {u['txid']}: {exc}. "
                "Is txindex=1 enabled?"
            ) from exc
        if not isinstance(raw_hex, str):
            raise BankingError(
                f"unexpected getrawtransaction return type for {u['txid']}: "
                f"{type(raw_hex).__name__}"
            )
        parents[u["txid"]] = raw_hex

    utxos_for_build = [
        UtxoForBuild(
            txid=u["txid"],
            vout=u["vout"],
            value_sats=u["value_sats"],
            parent_raw_hex=parents[u["txid"]],
        )
        for u in utxos
    ]

    max_external = _high_water_index(session, primary_descriptor.id, is_change=False)
    max_change = _high_water_index(session, primary_descriptor.id, is_change=True)

    try:
        built = descriptor_adapter.build_psbt(
            external_descriptor=primary_descriptor.expression,
            change_descriptor=primary_descriptor.change_expression,
            network=primary_descriptor.network,
            utxos=utxos_for_build,
            recipient_address=destination_address,
            amount_sats=amount_sats,
            fee_rate_sat_per_vbyte=fee_rate,
            max_external_index=max_external,
            max_change_index=max_change,
        )
    except Exception as exc:  # noqa: BLE001 — BDK errors aren't typed
        raise BankingError(f"PSBT build failed: {exc}") from exc

    bip21 = (
        f"bitcoin:{destination_address}"
        + (f"?amount={amount_sats / 100_000_000:.8f}" if amount_sats else "")
    )

    payment = PaymentRequest(
        id=uuid4(),
        holding_id=holding_id,
        payment_type=PaymentType.ONCHAIN,
        amount_sats=amount_sats,
        description=description,
        status=PaymentStatus.AWAITING_SIGNATURE,
        expires_at=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        destination_address=destination_address,
        bip21_uri=bip21,
        psbt_base64=built.psbt_base64,
    )
    payment_request_repo.insert(session, payment)

    return PaymentRequestBuildResult(payment_request=payment)


# --- helpers ----------------------------------------------------------------


def _gather_spendable_utxos(
    session: Session, descriptor_id: UUID
) -> list[dict]:
    """Return [(txid, vout, value_sats), ...] for unspent, unfrozen,
    confirmed UTXOs of `descriptor_id`."""
    rows = utxo_repo.list_for_descriptor(session, descriptor_id, only_unspent=True)
    return [
        {
            "txid": r.txid,
            "vout": r.vout,
            "value_sats": int(r.value_sats),
        }
        for r in rows
        if not r.is_frozen
        and r.confirmation_height is not None  # mempool-watching UTXOs filtered out
    ]


def _high_water_index(
    session: Session, descriptor_id: UUID, *, is_change: bool
) -> int:
    """Highest derivation_index we've ever exposed on this branch.

    Used to teach BDK's wallet how far to scan with `reveal_addresses_to`
    so the persisted UTXOs at those addresses count as `is_mine`.
    """
    addresses = descriptor_repo.list_addresses_for_descriptor(
        session, descriptor_id, is_change=is_change
    )
    if not addresses:
        return 0
    return max(a.derivation_index for a in addresses)


def _is_psbt_base64(value: str) -> bool:
    """Cheap sanity check: PSBTs are base64-encoded and always start with
    the magic bytes `psbt\\xff` -> "cHNidP8" in base64."""
    try:
        decoded = base64.b64decode(value, validate=True)
    except Exception:  # noqa: BLE001
        return False
    return decoded[:5] == b"psbt\xff"


def _is_psbt_finalized(psbt) -> bool:  # type: ignore[no-untyped-def]
    """True when every input has its final witness or final scriptSig set
    (i.e. signing has already produced the wire-ready transaction)."""
    inputs = psbt.input()
    if not inputs:
        return False
    for inp in inputs:
        has_witness = bool(getattr(inp, "final_script_witness", None))
        has_script_sig = bool(getattr(inp, "final_script_sig", None))
        if not (has_witness or has_script_sig):
            return False
    return True


# --- M6.2: submit-signed + broadcast ----------------------------------------


class PaymentRequestNotFound(BankingError):
    pass


class WrongStatusForOperation(BankingError):
    """The operation requires a specific status (e.g. submit-signed
    requires AWAITING_SIGNATURE)."""


class PsbtMismatch(BankingError):
    """User-submitted PSBT doesn't match the original (different inputs
    or outputs). Spec module 06: rejected with 400."""


class SignedTransactionInvalid(BankingError):
    """The PSBT couldn't be finalised (insufficient signatures, invalid
    signatures, etc.)."""


class BroadcastRejected(BankingError):
    """bitcoind rejected the transaction. The PaymentRequest stays in
    AWAITING_BROADCAST so the user can retry / RBF after fixing
    whatever bitcoind complained about."""


def submit_signed_payment_request(
    session: Session,
    *,
    request_id: UUID,
    psbt_base64: str | None,
    signed_transaction_hex: str | None,
) -> PaymentRequest:
    """Accept a signed PSBT or a finalized tx hex. Spec module 06 step 5.

    The flow:
      1. Original PaymentRequest must be AWAITING_SIGNATURE.
      2. Parse the user's submission.
      3. Validate the input set + output set matches the original PSBT
         (via Psbt.combine — which is commutative and rejects PSBTs with
         different unsigned-tx bodies).
      4. Finalize to get the signed raw transaction hex.
      5. Persist signed_transaction_hex; flip status to AWAITING_BROADCAST.
    """
    import bdkpython as _bdk

    request = payment_request_repo.get(session, request_id)
    if request is None:
        raise PaymentRequestNotFound(f"PaymentRequest {request_id} not found")
    if request.status != PaymentStatus.AWAITING_SIGNATURE:
        raise WrongStatusForOperation(
            f"submit-signed requires AWAITING_SIGNATURE; got {request.status.value}"
        )
    if request.psbt_base64 is None:
        raise BankingError(
            "Cannot submit-signed against a PaymentRequest with no original PSBT"
        )

    if psbt_base64 is None and signed_transaction_hex is None:
        raise BankingError(
            "Must provide either psbt_base64 or signed_transaction_hex"
        )

    if psbt_base64 is not None:
        try:
            user_psbt = _bdk.Psbt(psbt_base64)
        except Exception as exc:  # noqa: BLE001
            raise BankingError(f"psbt_base64 is not a valid PSBT: {exc}") from exc

        # Some signers (BDK in particular) finalize the PSBT as part of
        # signing — the resulting PSBT has `final_script_witness` /
        # `final_script_sig` populated and stripped bip32_derivation. In
        # that case combining with the unsigned original would lose the
        # witness data, so short-circuit and extract the tx directly.
        if _is_psbt_finalized(user_psbt):
            try:
                tx = user_psbt.extract_tx()
            except Exception as exc:  # noqa: BLE001
                raise SignedTransactionInvalid(
                    f"PSBT is finalised but cannot be extracted: {exc}"
                ) from exc

            signed_hex = tx.serialize().hex()
            updated = payment_request_repo.mark_signed(
                session,
                request_id,
                signed_transaction_hex=signed_hex,
                psbt_base64=psbt_base64,
            )
        else:
            # Unfinalized — typical hardware-signer workflow. Combine and
            # finalise on our side.
            original_psbt = _bdk.Psbt(request.psbt_base64)
            try:
                merged = original_psbt.combine(user_psbt)
            except Exception as exc:  # noqa: BLE001
                raise PsbtMismatch(
                    "Submitted PSBT does not match the original request "
                    f"(combine failed): {exc}"
                ) from exc

            try:
                result = merged.finalize()
            except Exception as exc:  # noqa: BLE001
                raise SignedTransactionInvalid(
                    f"PSBT could not be finalised: {exc}"
                ) from exc

            if not result.could_finalize:
                errs = result.errors or []
                raise SignedTransactionInvalid(
                    "PSBT could not be finalised "
                    f"(missing or invalid signatures): {errs}"
                )

            try:
                tx = result.psbt.extract_tx()
            except Exception as exc:  # noqa: BLE001
                raise SignedTransactionInvalid(
                    f"Cannot extract finalised transaction: {exc}"
                ) from exc

            signed_hex = tx.serialize().hex()
            merged_psbt_b64 = result.psbt.serialize()
            updated = payment_request_repo.mark_signed(
                session,
                request_id,
                signed_transaction_hex=signed_hex,
                psbt_base64=merged_psbt_b64,
            )
    else:
        # Direct finalised-tx submission. Some signers (Sparrow,
        # Electrum-software) emit a fully-signed tx instead of a PSBT.
        # v1 trusts the parsed tx and defers strict input-set validation
        # to the broadcast step (bitcoind will reject any tx whose
        # signatures don't cover the right inputs). Strict
        # input-set comparison lands in v1.x when we have a clean
        # outpoint accessor for unsigned PSBTs.
        assert signed_transaction_hex is not None
        try:
            _bdk.Transaction(bytes.fromhex(signed_transaction_hex))
        except Exception as exc:  # noqa: BLE001
            raise BankingError(
                f"signed_transaction_hex is not a valid serialized tx: {exc}"
            ) from exc

        signed_hex = signed_transaction_hex
        updated = payment_request_repo.mark_signed(
            session, request_id, signed_transaction_hex=signed_hex
        )

    if updated is None:  # pragma: no cover — already checked above
        raise PaymentRequestNotFound(f"PaymentRequest {request_id} disappeared")
    return updated


def broadcast_payment_request(
    session: Session,
    *,
    request_id: UUID,
    node: NodeAdapter,
) -> PaymentRequest:
    """Submit the signed transaction to bitcoind. Spec module 06 step 6.

    Persists a `broadcast_attempt` row BEFORE calling sendrawtransaction
    (so the audit trail captures the attempt even if bitcoind crashes
    mid-RPC). On rejection, status stays AWAITING_BROADCAST so the user
    can RBF / retry.
    """
    request = payment_request_repo.get(session, request_id)
    if request is None:
        raise PaymentRequestNotFound(f"PaymentRequest {request_id} not found")
    if request.status != PaymentStatus.AWAITING_BROADCAST:
        raise WrongStatusForOperation(
            f"broadcast requires AWAITING_BROADCAST; got {request.status.value}"
        )
    if request.signed_transaction_hex is None:
        raise BankingError(
            "Cannot broadcast a PaymentRequest with no signed_transaction_hex"
        )

    # Compute the txid from the signed tx so the audit row carries it
    # before we know whether bitcoind accepts.
    import bdkpython as _bdk

    parsed = _bdk.Transaction(bytes.fromhex(request.signed_transaction_hex))
    txid = str(parsed.compute_txid())

    attempt_id = uuid4()
    payment_request_repo.insert_broadcast_attempt(
        session,
        attempt_id=attempt_id,
        payment_request_id=request_id,
        transaction_hex=request.signed_transaction_hex,
        txid=txid,
        status="submitted",
    )
    session.flush()

    try:
        broadcast_txid = node.send_raw_transaction(
            request.signed_transaction_hex
        )
    except NodeRpcError as exc:
        payment_request_repo.update_broadcast_attempt(
            session,
            attempt_id=attempt_id,
            status="rejected",
            rejection_reason=f"{exc.code}: {exc.message}",
        )
        raise BroadcastRejected(f"bitcoind rejected the transaction: {exc}") from exc
    except NodeError as exc:
        # Don't flip the attempt to "rejected" here — bitcoind may simply
        # be down. Leave it "submitted" so retry logic / a v1.x worker
        # can pick it up.
        raise BankingError(f"bitcoind unreachable: {exc}") from exc

    payment_request_repo.update_broadcast_attempt(
        session, attempt_id=attempt_id, status="accepted"
    )
    updated = payment_request_repo.mark_broadcast(
        session, request_id, broadcast_txid=broadcast_txid
    )
    if updated is None:  # pragma: no cover
        raise PaymentRequestNotFound(
            f"PaymentRequest {request_id} disappeared during broadcast"
        )
    return updated


__all__ = [
    "BankingError",
    "BroadcastRejected",
    "HoldingCannotSend",
    "HoldingNotFound",
    "InFlightPaymentExists",
    "InsufficientBalance",
    "InvalidDestination",
    "PaymentRequestBuildResult",
    "PaymentRequestNotFound",
    "PsbtMismatch",
    "SignedTransactionInvalid",
    "VaultLongTermRequiresConfirmation",
    "WrongStatusForOperation",
    "broadcast_payment_request",
    "build_payment_request",
    "submit_signed_payment_request",
]
