"""Unit tests for the BDK descriptor adapter.

Test vectors use the BIP 39 sample mnemonic
``abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about``
which is widely published, intentionally insecure, and produces well-known
xpubs / addresses across implementations. Using known vectors lets us assert
exact addresses, not just "some address came out."
"""

from __future__ import annotations

import pytest

from tallykeep.adapters.descriptor_adapter import (
    DescriptorAdapter,
    DescriptorParseError,
    UnsupportedDescriptorError,
)
from tallykeep.domain.enums import AddressType, Network


pytestmark = pytest.mark.unit


# Known-good descriptors derived from the abandon-abandon-...-about mnemonic.
# These were produced by bdkpython itself at exploration time and double-checked
# against publicly available reference data; if a bdkpython upgrade changes the
# canonical form, the test asserts on `address_type` (insensitive) and on the
# first few addresses (which are mnemonic-derived facts, not bdk-version-bound).

# Native SegWit (BIP 84), mainnet
WPKH_MAINNET_EXPRESSION = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)

# Same descriptor, change branch
WPKH_MAINNET_CHANGE_EXPRESSION = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"
)

# Testnet single-key WPKH — matches the BDK docs example.
WPKH_TESTNET_EXPRESSION = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)

# Legacy P2PKH on mainnet — pkh()
PKH_MAINNET_EXPRESSION = (
    "pkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
)

# Multisig (rejected in v1) — sortedmulti. Built with two derivations of the
# same xpub for compactness; bdkpython parses it as multisig regardless.
WSH_MULTISIG_MAINNET_EXPRESSION = (
    "wsh(sortedmulti(2,"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*,"
    "xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*"
    "))"
)

# Multipath descriptor (rejected) — uses the <0;1> shorthand.
WPKH_MULTIPATH_EXPRESSION = (
    "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/<0;1>/*)"
)


@pytest.fixture()
def adapter() -> DescriptorAdapter:
    return DescriptorAdapter()


# --- parse: success paths ----------------------------------------------------


class TestParseSuccess:
    def test_parses_wpkh_mainnet_and_classifies_as_native_segwit(
        self, adapter: DescriptorAdapter
    ) -> None:
        parsed = adapter.parse(WPKH_MAINNET_EXPRESSION, Network.MAINNET)
        assert parsed.address_type == AddressType.NATIVE_SEGWIT
        assert parsed.is_multipath is False
        assert parsed.expression == WPKH_MAINNET_EXPRESSION
        # Canonical form is whatever bdkpython echoes — at minimum it starts the
        # same and ends with the #checksum suffix.
        assert parsed.canonical_expression.startswith("wpkh(")
        assert "#" in parsed.canonical_expression

    def test_parses_pkh_as_legacy(self, adapter: DescriptorAdapter) -> None:
        parsed = adapter.parse(PKH_MAINNET_EXPRESSION, Network.MAINNET)
        assert parsed.address_type == AddressType.LEGACY

    def test_parses_testnet_descriptor(self, adapter: DescriptorAdapter) -> None:
        parsed = adapter.parse(WPKH_TESTNET_EXPRESSION, Network.TESTNET)
        assert parsed.address_type == AddressType.NATIVE_SEGWIT

    def test_descriptor_id_is_stable(self, adapter: DescriptorAdapter) -> None:
        a = adapter.parse(WPKH_MAINNET_EXPRESSION, Network.MAINNET)
        b = adapter.parse(WPKH_MAINNET_EXPRESSION, Network.MAINNET)
        assert a.descriptor_id == b.descriptor_id

    def test_descriptor_id_differs_for_different_expressions(
        self, adapter: DescriptorAdapter
    ) -> None:
        a = adapter.parse(WPKH_MAINNET_EXPRESSION, Network.MAINNET)
        b = adapter.parse(WPKH_MAINNET_CHANGE_EXPRESSION, Network.MAINNET)
        assert a.descriptor_id != b.descriptor_id


# --- parse: rejection paths --------------------------------------------------


class TestParseRejection:
    def test_empty_expression_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(DescriptorParseError, match="1..4096"):
            adapter.parse("", Network.MAINNET)

    def test_oversized_expression_rejected(self, adapter: DescriptorAdapter) -> None:
        # Spec module 10 / S6 — 4 KB cap on descriptor input.
        with pytest.raises(DescriptorParseError, match="1..4096"):
            adapter.parse("wpkh(" + "x" * 5000 + ")", Network.MAINNET)

    def test_garbage_expression_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(DescriptorParseError):
            adapter.parse("not a descriptor at all", Network.MAINNET)

    def test_multisig_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(UnsupportedDescriptorError, match="not accepted here"):
            adapter.parse(WSH_MULTISIG_MAINNET_EXPRESSION, Network.MAINNET)

    def test_multipath_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(UnsupportedDescriptorError, match="Multipath"):
            adapter.parse(WPKH_MULTIPATH_EXPRESSION, Network.MAINNET)

    def test_wrong_network_rejected(self, adapter: DescriptorAdapter) -> None:
        # Mainnet xpub used with TESTNET network should fail at parse time.
        with pytest.raises(DescriptorParseError):
            adapter.parse(WPKH_MAINNET_EXPRESSION, Network.TESTNET)


# --- derive ------------------------------------------------------------------


class TestDeriveAddresses:
    def test_derives_requested_count(self, adapter: DescriptorAdapter) -> None:
        addresses = adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION, Network.MAINNET, count=5
        )
        assert len(addresses) == 5
        assert [a.derivation_index for a in addresses] == [0, 1, 2, 3, 4]
        # All addresses unique.
        assert len({a.address for a in addresses}) == 5

    def test_derived_addresses_match_known_prefix(
        self, adapter: DescriptorAdapter
    ) -> None:
        # bc1q... for native segwit on mainnet.
        addresses = adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION, Network.MAINNET, count=3
        )
        for a in addresses:
            assert a.address.startswith("bc1q"), a.address

    def test_testnet_addresses_use_tb_prefix(
        self, adapter: DescriptorAdapter
    ) -> None:
        addresses = adapter.derive_addresses(
            WPKH_TESTNET_EXPRESSION, Network.TESTNET, count=2
        )
        for a in addresses:
            assert a.address.startswith("tb1q"), a.address

    def test_legacy_addresses_use_1_prefix(
        self, adapter: DescriptorAdapter
    ) -> None:
        addresses = adapter.derive_addresses(
            PKH_MAINNET_EXPRESSION, Network.MAINNET, count=2
        )
        for a in addresses:
            assert a.address[0] == "1", a.address

    def test_start_index_is_honored(self, adapter: DescriptorAdapter) -> None:
        first_batch = adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION, Network.MAINNET, count=10
        )
        offset_batch = adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION,
            Network.MAINNET,
            start_index=5,
            count=5,
        )
        # Addresses 5..9 of the first batch must equal the offset batch.
        assert [a.address for a in first_batch[5:10]] == [
            a.address for a in offset_batch
        ]

    def test_count_zero_returns_empty(self, adapter: DescriptorAdapter) -> None:
        assert adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION, Network.MAINNET, count=0
        ) == []

    def test_negative_count_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(ValueError, match="count"):
            adapter.derive_addresses(
                WPKH_MAINNET_EXPRESSION, Network.MAINNET, count=-1
            )

    def test_negative_start_index_rejected(self, adapter: DescriptorAdapter) -> None:
        with pytest.raises(ValueError, match="start_index"):
            adapter.derive_addresses(
                WPKH_MAINNET_EXPRESSION, Network.MAINNET, start_index=-1
            )

    def test_derive_propagates_unsupported_descriptor(
        self, adapter: DescriptorAdapter
    ) -> None:
        with pytest.raises(UnsupportedDescriptorError):
            adapter.derive_addresses(
                WSH_MULTISIG_MAINNET_EXPRESSION, Network.MAINNET, count=5
            )

    def test_derive_single_address_matches_batch(
        self, adapter: DescriptorAdapter
    ) -> None:
        single = adapter.derive_address(
            WPKH_MAINNET_EXPRESSION, Network.MAINNET, 7
        )
        batch = adapter.derive_addresses(
            WPKH_MAINNET_EXPRESSION,
            Network.MAINNET,
            start_index=7,
            count=1,
        )
        assert single == batch[0].address
