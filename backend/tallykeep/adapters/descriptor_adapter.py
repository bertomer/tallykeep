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


__all__ = [
    "DerivedAddress",
    "DescriptorAdapter",
    "DescriptorParseError",
    "ParsedDescriptor",
    "UnsupportedDescriptorError",
]
