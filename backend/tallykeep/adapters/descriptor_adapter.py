"""Anti-corruption layer around bdkpython for descriptor parsing and derivation.

Spec module 01: adapters translate foreign data shapes into domain types. Domain
code never imports `bdkpython`; it goes through `DescriptorAdapter` here.

v1 supports only single-key descriptors (PKH, WPKH, SH_WPKH, TR-single).
Multisig descriptors parse but are rejected at import — see spec module 13 / Q11.

A note on the `Network` mapping: bdkpython exposes `Network.BITCOIN` for
mainnet; our domain enum uses the more conventional `MAINNET`. The translation
is one-way (we don't need to convert bdk's enum to ours; we never receive bdk
values without first sending one in).
"""

from __future__ import annotations

from dataclasses import dataclass

import bdkpython as bdk

from tallykeep.domain.enums import AddressType, Network


# --- network mapping ---------------------------------------------------------


_NETWORK_TO_BDK: dict[Network, bdk.Network] = {
    Network.MAINNET: bdk.Network.BITCOIN,
    Network.TESTNET: bdk.Network.TESTNET,
    Network.SIGNET: bdk.Network.SIGNET,
    Network.REGTEST: bdk.Network.REGTEST,
}


# --- descriptor type mapping --------------------------------------------------


# Single-key descriptor types accepted in v1. Multisig variants (SH_SORTED_MULTI,
# WSH_SORTED_MULTI, SH_WSH_SORTED_MULTI) and bare/script variants land in v2 per
# spec module 13.
_SINGLE_KEY_TYPES: frozenset[bdk.DescriptorType] = frozenset(
    {
        bdk.DescriptorType.PKH,
        bdk.DescriptorType.WPKH,
        bdk.DescriptorType.SH_WPKH,
        bdk.DescriptorType.TR,
    }
)


_BDK_TYPE_TO_ADDRESS_TYPE: dict[bdk.DescriptorType, AddressType] = {
    bdk.DescriptorType.PKH: AddressType.LEGACY,
    bdk.DescriptorType.SH_WPKH: AddressType.NESTED_SEGWIT,
    bdk.DescriptorType.WPKH: AddressType.NATIVE_SEGWIT,
    bdk.DescriptorType.TR: AddressType.TAPROOT,
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
    """

    expression: str
    canonical_expression: str
    address_type: AddressType
    descriptor_id: str  # bdk's stable id, useful as a dedup key in tests
    is_multipath: bool


@dataclass(frozen=True)
class DerivedAddress:
    address: str
    derivation_index: int


# --- adapter -----------------------------------------------------------------


class DescriptorAdapter:
    """Stateless adapter — every method takes everything it needs as arguments."""

    def parse(self, expression: str, network: Network) -> ParsedDescriptor:
        """Parse a BIP 380 expression and return its canonical form + address type.

        Raises:
            DescriptorParseError: bdkpython rejected the expression.
            UnsupportedDescriptorError: the descriptor parses but uses a
                construct v1 does not support (e.g. multisig, BARE, multipath).
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
        if desc_type not in _SINGLE_KEY_TYPES:
            raise UnsupportedDescriptorError(
                f"Descriptor type {desc_type.name} is not supported in v1. "
                "Multisig (sh / wsh / tr-multi) and bare scripts are deferred "
                "to v2 per spec module 13."
            )

        return ParsedDescriptor(
            expression=expression,
            canonical_expression=str(descriptor),  # `__str__` returns the canonical form
            address_type=_BDK_TYPE_TO_ADDRESS_TYPE[desc_type],
            descriptor_id=str(descriptor.descriptor_id()),
            is_multipath=False,
        )

    def derive_addresses(
        self,
        expression: str,
        network: Network,
        *,
        start_index: int = 0,
        count: int = 20,
    ) -> list[DerivedAddress]:
        """Derive `count` addresses from `start_index` onwards.

        The caller passes the descriptor expression rather than a ParsedDescriptor
        to keep this method usable without a prior `parse()` call (some flows
        only need derivation, not the full validation). Validation still runs
        — invalid descriptors fail fast before any derivation happens.
        """
        if count < 0:
            raise ValueError("count must be >= 0")
        if start_index < 0:
            raise ValueError("start_index must be >= 0")

        # Run parse() so unsupported descriptor types fail early. We discard the
        # result; the descriptor object itself is recreated below so we don't
        # have to thread it through.
        self.parse(expression, network)

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
    ) -> str:
        """Convenience: derive a single address at `index`."""
        if index < 0:
            raise ValueError("index must be >= 0")
        self.parse(expression, network)
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
]
