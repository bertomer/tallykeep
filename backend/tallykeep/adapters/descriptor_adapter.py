"""Anti-corruption layer around bdkpython for descriptor parsing and derivation.

Spec module 01: adapters translate foreign data shapes into domain types. Domain
code never imports `bdkpython`; it goes through `DescriptorAdapter` here.

Single-key descriptors (PKH, WPKH, SH_WPKH, TR-single) are accepted by default.
Vault descriptors (multisig and single-key+timelock) are accepted when
`allow_multisig=True` is passed to `parse()`. Vault creation uses this; Purse
and Strongbox creation do not.

Vault v1 accept set (all require `allow_multisig=True`):
  - WSH_SORTED_MULTI / SH_SORTED_MULTI / SH_WSH_SORTED_MULTI (existing)
  - BDK type WSH: wsh(multi), wsh(and_v(timelock, pk)), wsh(and_v(timelock, multi))
  - BDK type SH: sh(multi)
  - BDK type TR with miniscript: tr(key, multi_a(...)), tr(key, and_v(timelock, pk))

A note on the `Network` mapping: bdkpython exposes `Network.BITCOIN` for
mainnet; our domain enum uses the more conventional `MAINNET`. The translation
is one-way (we don't need to convert bdk's enum to ours; we never receive bdk
values without first sending one in).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import bdkpython as bdk

from tallykeep.domain.enums import AddressType, Network


# Regex to extract the threshold from sortedmulti / multi / multi_a expressions.
_MULTISIG_THRESHOLD_RE = re.compile(r'(?:sorted)?multi(?:_a)?\(\s*(\d+)\s*,')
# Extended public key pattern — covers xpub/tpub/ypub/zpub and capital variants.
_XPUB_RE = re.compile(r'[a-zA-Z]{1,4}pub[a-zA-Z0-9]+')
# Timelock detection.
_TIMELOCK_AFTER_RE = re.compile(r'after\(\s*(\d+)\s*\)')   # CLTV (absolute block height)
_TIMELOCK_OLDER_RE = re.compile(r'older\(\s*(\d+)\s*\)')   # CSV (relative block count)
# BIP32 key-origin fingerprint — 8 hex chars before the first `/` or `]` in brackets.
_FINGERPRINT_RE = re.compile(r'\[([0-9a-fA-F]{8})[/\]]')
# Taproot-specific multisig fragments.
_TAPROOT_MULTISIG_RE = re.compile(r'(?:sorted)?multi_a\(')
# Multi-path / branching miniscript fragments NOT in the v1 accept set.
# Matches or_i / or_d / or_c / or_b combinators, thresh(), and hash-lock
# primitives (sha256, hash256, ripemd160, hash160).  Any expression containing
# these must route to "unsupported descriptor form" — not to Vault parseback —
# even if it also carries a timelock or multisig fragment.
_UNSUPPORTED_FRAGMENT_RE = re.compile(
    r'\bor_[idcb]\(|\bthresh\(|\bsha256\(|\bhash256\(|\bripemd160\(|\bhash160\('
)


# --- network mapping ---------------------------------------------------------


_NETWORK_TO_BDK: dict[Network, bdk.Network] = {
    Network.MAINNET: bdk.Network.BITCOIN,
    Network.TESTNET: bdk.Network.TESTNET,
    Network.SIGNET: bdk.Network.SIGNET,
    Network.REGTEST: bdk.Network.REGTEST,
}


# --- descriptor type mapping --------------------------------------------------


_SINGLE_KEY_TYPES: frozenset[bdk.DescriptorType] = frozenset(
    {
        bdk.DescriptorType.PKH,
        bdk.DescriptorType.WPKH,
        bdk.DescriptorType.SH_WPKH,
        bdk.DescriptorType.TR,
    }
)

_MULTISIG_TYPES: frozenset[bdk.DescriptorType] = frozenset(
    {
        bdk.DescriptorType.SH_SORTED_MULTI,
        bdk.DescriptorType.WSH_SORTED_MULTI,
        bdk.DescriptorType.SH_WSH_SORTED_MULTI,
    }
)

# WSH / SH / TR also cover miniscript descriptors (Vault v1 accept set).
# These are only valid when allow_multisig=True.
_MINISCRIPT_TYPES: frozenset[bdk.DescriptorType] = frozenset(
    {
        bdk.DescriptorType.WSH,  # wsh(multi), wsh(sortedmulti), wsh(miniscript)
        bdk.DescriptorType.SH,   # sh(multi)
    }
)

_BDK_TYPE_TO_ADDRESS_TYPE: dict[bdk.DescriptorType, AddressType] = {
    bdk.DescriptorType.PKH: AddressType.LEGACY,
    bdk.DescriptorType.SH_WPKH: AddressType.NESTED_SEGWIT,
    bdk.DescriptorType.WPKH: AddressType.NATIVE_SEGWIT,
    bdk.DescriptorType.TR: AddressType.TAPROOT,
    bdk.DescriptorType.SH_SORTED_MULTI: AddressType.P2SH_MULTISIG,
    bdk.DescriptorType.WSH_SORTED_MULTI: AddressType.P2WSH,
    bdk.DescriptorType.SH_WSH_SORTED_MULTI: AddressType.P2SH_P2WSH,
    # Miniscript types (Vault v1 accept set)
    bdk.DescriptorType.WSH: AddressType.P2WSH,
    bdk.DescriptorType.SH: AddressType.P2SH_MULTISIG,
}


# --- public errors ------------------------------------------------------------


class DescriptorParseError(ValueError):
    """The descriptor expression could not be parsed by bdkpython."""


class UnsupportedDescriptorError(ValueError):
    """The descriptor parses but is not supported in v1 (e.g. multisig)."""


# --- result containers --------------------------------------------------------


@dataclass(frozen=True)
class ParsedDescriptor:
    """Bundle of facts about a parsed-and-validated descriptor.

    The original `expression` is the input string. `canonical_expression` is what
    bdkpython echoes back, with the standard `#checksum` suffix; we persist the
    canonical form so future re-imports normalize to the same value.

    For multisig descriptors `is_multisig` is True and `required_signers` /
    `total_signers` carry the m-of-n extracted from the expression.

    For Vault descriptors `timelock_kind` is "cltv" or "csv" when a miniscript
    timelock is present; `timelock_value` is the block height (CLTV) or block
    count (CSV). `cosigner_fingerprints` lists BIP32 fingerprints found in the
    key-origin brackets of the expression.
    """

    expression: str
    canonical_expression: str
    address_type: AddressType
    descriptor_id: str  # bdk's stable id, useful as a dedup key in tests
    is_multipath: bool
    is_multisig: bool = False
    required_signers: int | None = None
    total_signers: int | None = None
    timelock_kind: str | None = None          # "cltv" | "csv" | None
    timelock_value: int | None = None         # block height (CLTV) or count (CSV)
    cosigner_fingerprints: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DerivedAddress:
    address: str
    derivation_index: int


# --- adapter -----------------------------------------------------------------


def _extract_multisig_params(
    expression: str,
    *,
    is_taproot_multisig: bool = False,
) -> tuple[int | None, int | None]:
    """Extract (required_signers, total_signers) from a multisig expression.

    Uses regex heuristics on the raw expression string — BDK does not expose
    m-of-n counts as structured fields. Accurate for standard BIP 380
    sortedmulti/multi expressions; exotic or non-standard forms may return None.

    For Taproot multisig (multi_a / sortedmulti_a), pass `is_taproot_multisig=True`
    so that the internal key is subtracted from the total xpub count.
    """
    m = _MULTISIG_THRESHOLD_RE.search(expression)
    if m is None:
        return None, None
    required = int(m.group(1))
    total = len(_XPUB_RE.findall(expression))
    if is_taproot_multisig:
        total -= 1  # subtract the internal (key-path) taproot key
    return required, total if total > 0 else None


def _extract_timelock(expression: str) -> tuple[str | None, int | None]:
    """Extract (timelock_kind, timelock_value) from a miniscript expression.

    Returns ("cltv", height) for after(), ("csv", count) for older(), (None, None)
    for no timelock.
    """
    m = _TIMELOCK_AFTER_RE.search(expression)
    if m:
        return "cltv", int(m.group(1))
    m = _TIMELOCK_OLDER_RE.search(expression)
    if m:
        return "csv", int(m.group(1))
    return None, None


def _extract_fingerprints(expression: str) -> tuple[str, ...]:
    """Extract all BIP32 key-origin fingerprints from a descriptor expression.

    Returns the unique fingerprints in order of first appearance (lowercase hex).
    """
    seen: list[str] = []
    for fp in _FINGERPRINT_RE.findall(expression):
        fp_lower = fp.lower()
        if fp_lower not in seen:
            seen.append(fp_lower)
    return tuple(seen)


class DescriptorAdapter:
    """Stateless adapter — every method takes everything it needs as arguments."""

    def parse(
        self,
        expression: str,
        network: Network,
        *,
        allow_multisig: bool = False,
    ) -> ParsedDescriptor:
        """Parse a BIP 380 expression and return its canonical form + address type.

        Pass `allow_multisig=True` to accept multisig descriptor types
        (WSH_SORTED_MULTI, SH_SORTED_MULTI, SH_WSH_SORTED_MULTI). Vault creation
        uses this; Purse and Strongbox creation do not.

        Raises:
            DescriptorParseError: bdkpython rejected the expression.
            UnsupportedDescriptorError: the descriptor parses but uses a
                construct not accepted in this context (e.g. multisig when
                allow_multisig=False, BARE, multipath).
        """
        if not expression or len(expression) > 4096:
            raise DescriptorParseError(
                "Descriptor expression must be 1..4096 characters (defense against "
                "spec module 10 S6 — malicious descriptor as input)."
            )

        try:
            descriptor = bdk.Descriptor(expression, _NETWORK_TO_BDK[network])
        except Exception as exc:  # bdk's exception types are not stable across versions
            raise DescriptorParseError(
                f"bdkpython failed to parse descriptor: {exc}"
            ) from exc

        # Multipath descriptors have the `<0;1>` shorthand expanded into two
        # single-path descriptors. v1 stores external + internal paths in two
        # separate Descriptor rows (per spec module 02), so we reject the
        # shorthand here and ask the caller to provide them as separate inputs.
        if descriptor.is_multipath():
            raise UnsupportedDescriptorError(
                "Multipath descriptors (`<0;1>` shorthand) are not supported. "
                "Provide the external and change descriptors separately."
            )

        desc_type = descriptor.desc_type()

        if desc_type in _MULTISIG_TYPES:
            if not allow_multisig:
                raise UnsupportedDescriptorError(
                    f"Descriptor type {desc_type.name} is a multisig descriptor "
                    "and is not accepted here. Multisig descriptors are only "
                    "valid for Vault holdings."
                )
            address_type = _BDK_TYPE_TO_ADDRESS_TYPE[desc_type]
            required_signers, total_signers = _extract_multisig_params(expression)
            timelock_kind, timelock_value = _extract_timelock(expression)
            fingerprints = _extract_fingerprints(expression)
            return ParsedDescriptor(
                expression=expression,
                canonical_expression=str(descriptor),
                address_type=address_type,
                descriptor_id=str(descriptor.descriptor_id()),
                is_multipath=False,
                is_multisig=True,
                required_signers=required_signers,
                total_signers=total_signers,
                timelock_kind=timelock_kind,
                timelock_value=timelock_value,
                cosigner_fingerprints=fingerprints,
            )

        # Miniscript WSH / SH — covers wsh(multi), wsh(and_v(...,pk(...))),
        # wsh(and_v(...,multi(...))), sh(multi), etc.
        if desc_type in _MINISCRIPT_TYPES:
            if not allow_multisig:
                raise UnsupportedDescriptorError(
                    f"Descriptor type {desc_type.name} is a Vault descriptor "
                    "(multisig or timelock) and is not accepted here. Vault "
                    "descriptors are only valid for Vault holdings."
                )
            # Reject multi-path / branching fragments not in the v1 accept set.
            # or_i/or_d/or_c/or_b, thresh(), hash-lock primitives — these are
            # protocol-level constructs (swap-in, recovery paths, decaying
            # multisig) that must not be misclassified as simple timelocked Vaults.
            if _UNSUPPORTED_FRAGMENT_RE.search(expression):
                raise UnsupportedDescriptorError(
                    "Descriptor contains branching or hash-lock fragments "
                    "(or_i / or_d / or_c / or_b / thresh / sha256 / hash256 / "
                    "ripemd160 / hash160) that are not in the v1 Vault accept "
                    "set. This is an unsupported descriptor form."
                )
            # Reject SH without a multi/sortedmulti clause (unusual SH form).
            if desc_type == bdk.DescriptorType.SH and not _MULTISIG_THRESHOLD_RE.search(
                expression
            ):
                raise UnsupportedDescriptorError(
                    "sh() descriptors without a multi/sortedmulti clause are not "
                    "supported. Use wsh() or one of the standard multisig wrappers."
                )
            address_type = _BDK_TYPE_TO_ADDRESS_TYPE[desc_type]
            is_multisig_expr = bool(_MULTISIG_THRESHOLD_RE.search(expression))
            # For WSH, single-key+timelock has no multi clause → required=total=1.
            if is_multisig_expr:
                required_signers, total_signers = _extract_multisig_params(expression)
            else:
                required_signers, total_signers = 1, 1
            timelock_kind, timelock_value = _extract_timelock(expression)
            fingerprints = _extract_fingerprints(expression)
            return ParsedDescriptor(
                expression=expression,
                canonical_expression=str(descriptor),
                address_type=address_type,
                descriptor_id=str(descriptor.descriptor_id()),
                is_multipath=False,
                is_multisig=is_multisig_expr,
                required_signers=required_signers,
                total_signers=total_signers,
                timelock_kind=timelock_kind,
                timelock_value=timelock_value,
                cosigner_fingerprints=fingerprints,
            )

        if desc_type not in _SINGLE_KEY_TYPES:
            raise UnsupportedDescriptorError(
                f"Descriptor type {desc_type.name} is not supported. "
                "Bare scripts and other exotic forms are not accepted."
            )

        # TR type: detect miniscript content (Vault markers).
        if desc_type == bdk.DescriptorType.TR:
            timelock_kind, timelock_value = _extract_timelock(expression)
            has_taproot_multisig = bool(_TAPROOT_MULTISIG_RE.search(expression))
            is_vault_tr = timelock_kind is not None or has_taproot_multisig
            if is_vault_tr:
                if not allow_multisig:
                    raise UnsupportedDescriptorError(
                        "Taproot descriptors with a timelock or multi_a clause are "
                        "Vault descriptors and are not accepted here. Set this up "
                        "as a Vault instead."
                    )
                if _UNSUPPORTED_FRAGMENT_RE.search(expression):
                    raise UnsupportedDescriptorError(
                        "Descriptor contains branching or hash-lock fragments "
                        "(or_i / or_d / or_c / or_b / thresh / sha256 / hash256 / "
                        "ripemd160 / hash160) that are not in the v1 Vault accept "
                        "set. This is an unsupported descriptor form."
                    )
                is_multisig_tr = has_taproot_multisig
                if is_multisig_tr:
                    required_signers, total_signers = _extract_multisig_params(
                        expression, is_taproot_multisig=True
                    )
                else:
                    required_signers, total_signers = 1, 1
                fingerprints = _extract_fingerprints(expression)
                return ParsedDescriptor(
                    expression=expression,
                    canonical_expression=str(descriptor),
                    address_type=AddressType.TAPROOT,
                    descriptor_id=str(descriptor.descriptor_id()),
                    is_multipath=False,
                    is_multisig=is_multisig_tr,
                    required_signers=required_signers,
                    total_signers=total_signers,
                    timelock_kind=timelock_kind,
                    timelock_value=timelock_value,
                    cosigner_fingerprints=fingerprints,
                )

        return ParsedDescriptor(
            expression=expression,
            canonical_expression=str(descriptor),  # `__str__` returns the canonical form
            address_type=_BDK_TYPE_TO_ADDRESS_TYPE[desc_type],
            descriptor_id=str(descriptor.descriptor_id()),
            is_multipath=False,
            is_multisig=False,
        )

    def derive_addresses(
        self,
        expression: str,
        network: Network,
        *,
        start_index: int = 0,
        count: int = 20,
        allow_multisig: bool = False,
    ) -> list[DerivedAddress]:
        """Derive `count` addresses from `start_index` onwards.

        The caller passes the descriptor expression rather than a ParsedDescriptor
        to keep this method usable without a prior `parse()` call (some flows
        only need derivation, not the full validation). Validation still runs
        — invalid descriptors fail fast before any derivation happens.

        Pass `allow_multisig=True` when deriving from multisig descriptors (Vault).
        """
        if count < 0:
            raise ValueError("count must be >= 0")
        if start_index < 0:
            raise ValueError("start_index must be >= 0")

        # Run parse() so unsupported descriptor types fail early. We discard the
        # result; the descriptor object itself is recreated below so we don't
        # have to thread it through.
        self.parse(expression, network, allow_multisig=allow_multisig)

        descriptor = bdk.Descriptor(expression, _NETWORK_TO_BDK[network])
        results: list[DerivedAddress] = []
        for offset in range(count):
            index = start_index + offset
            address = descriptor.derive_address(index, _NETWORK_TO_BDK[network])
            results.append(DerivedAddress(address=str(address), derivation_index=index))
        return results

    def derive_address(
        self,
        expression: str,
        network: Network,
        index: int,
        *,
        allow_multisig: bool = False,
    ) -> str:
        """Convenience: derive a single address at `index`."""
        if index < 0:
            raise ValueError("index must be >= 0")
        self.parse(expression, network, allow_multisig=allow_multisig)
        descriptor = bdk.Descriptor(expression, _NETWORK_TO_BDK[network])
        return str(descriptor.derive_address(index, _NETWORK_TO_BDK[network]))

    # --- PSBT construction (M6.1) -------------------------------------------

    def build_psbt(
        self,
        *,
        external_descriptor: str,
        change_descriptor: str | None,
        network: Network,
        utxos: list["UtxoForBuild"],
        recipient_address: str,
        amount_sats: int | None,
        fee_rate_sat_per_vbyte: float,
        max_external_index: int,
        max_change_index: int,
    ) -> "BuiltPsbt":
        """Build an unsigned PSBT spending from `utxos` to `recipient_address`.

        Pass `amount_sats=None` to drain the wallet (subtract fee from the
        only output). The wallet's coin selection is BDK's default
        BranchAndBound — coin-selection knobs land in v1.x with the
        Sovereign-profile per-payment override.

        We teach BDK about the wallet's UTXOs by `apply_unconfirmed_txs`-ing
        every parent transaction. Each parent tx must be passed in serialized
        form (the on-chain raw hex). Callers fetch raw hex via NodeAdapter
        when our `onchain_transaction.raw_hex` is empty.
        """
        import time

        bdk_network = _NETWORK_TO_BDK[network]
        descriptor = bdk.Descriptor(external_descriptor, bdk_network)
        if change_descriptor is None:
            # bdkpython 2.x's two-keychain wallet *requires* a change descriptor.
            # We synthesize one by reusing the external descriptor — funds
            # going to "change" simply land back on the external chain. This
            # matches what we've been doing in the address-derivation path
            # for M4 when no change_expression was provided.
            change = descriptor
        else:
            change = bdk.Descriptor(change_descriptor, bdk_network)

        # Lookahead must be wide enough that BDK indexes any address we've
        # derived so far. Use max(known indexes) + 25 (the default lookahead).
        lookahead = max(max_external_index, max_change_index) + 25
        wallet = bdk.Wallet(
            descriptor,
            change,
            bdk_network,
            bdk.Persister.new_in_memory(),
            lookahead=lookahead,
        )
        # Reveal so the wallet's index covers the full range our DB knows.
        wallet.reveal_addresses_to(bdk.KeychainKind.EXTERNAL, max_external_index)
        wallet.reveal_addresses_to(bdk.KeychainKind.INTERNAL, max_change_index)

        # Teach BDK about each parent tx so the wallet's UTXO set picks up
        # our outputs. Deduplicate by raw_hex — the same parent tx may have
        # paid us multiple UTXOs.
        seen_hex: set[str] = set()
        unconfirmed: list[bdk.UnconfirmedTx] = []
        last_seen = int(time.time())
        for u in utxos:
            if u.parent_raw_hex in seen_hex:
                continue
            seen_hex.add(u.parent_raw_hex)
            tx = bdk.Transaction(bytes.fromhex(u.parent_raw_hex))
            unconfirmed.append(bdk.UnconfirmedTx(tx=tx, last_seen=last_seen))
        if unconfirmed:
            wallet.apply_unconfirmed_txs(unconfirmed)

        recipient = bdk.Address(recipient_address, bdk_network)
        recipient_script = recipient.script_pubkey()

        builder = bdk.TxBuilder()
        # Embed the global xpub map so the resulting PSBT carries enough
        # context for any signer (and our own merge+finalise path) to
        # derive pubkeys for each input. Without this, finalisation
        # fails with "Missing pubkey for a pkh/wpkh" on the merged PSBT.
        builder = builder.add_global_xpubs()
        if amount_sats is None:
            # Drain — single recipient output, fee deducted from balance.
            builder = builder.drain_to(recipient_script).drain_wallet()
        else:
            builder = builder.add_recipient(
                recipient_script, bdk.Amount.from_sat(amount_sats)
            )
        builder = builder.fee_rate(
            bdk.FeeRate.from_sat_per_vb(int(round(fee_rate_sat_per_vbyte)))
        )

        psbt = builder.finish(wallet)

        # bdkpython's Psbt.serialize() returns a base64 string directly —
        # no further encoding step. (The binary form is recovered by
        # base64-decoding when the API serves it as application/octet-stream.)
        psbt_base64 = psbt.serialize()

        # Pull the unsigned-tx vbytes for fee math + the change index for
        # gap-tracking (the `change_descriptor` path advanced the wallet's
        # internal derivation index, and we want to surface the new value
        # to the caller).
        new_change_index = wallet.derivation_index(bdk.KeychainKind.INTERNAL)

        return BuiltPsbt(
            psbt_base64=psbt_base64,
            change_keychain_index=(
                int(new_change_index) if new_change_index is not None else None
            ),
        )


@dataclass(frozen=True)
class UtxoForBuild:
    """Minimum info DescriptorAdapter.build_psbt needs about each UTXO.

    `parent_raw_hex` is the full serialized parent transaction (hex). BDK
    needs it to register the UTXO via `apply_unconfirmed_txs` so the
    wallet's coin selection considers it spendable.
    """

    txid: str
    vout: int
    value_sats: int
    parent_raw_hex: str


@dataclass(frozen=True)
class BuiltPsbt:
    psbt_base64: str
    change_keychain_index: int | None


__all__ = [
    "BuiltPsbt",
    "DerivedAddress",
    "DescriptorAdapter",
    "DescriptorParseError",
    "ParsedDescriptor",
    "UnsupportedDescriptorError",
    "UtxoForBuild",
    "_MINISCRIPT_TYPES",
    "_MULTISIG_TYPES",
]
