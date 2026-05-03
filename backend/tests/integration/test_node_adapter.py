"""NodeAdapter integration tests against the regtest bitcoind container.

Exercises the methods that the savings layer (M5.2 onwards) depends on:
get_blockchain_info, scan_descriptors, get_raw_transaction, get_mempool_entry,
plus the regtest helpers (create_wallet, generate_to_address,
send_to_address_from_wallet) used by later milestones to fund test addresses.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator

import pytest

from tallykeep.adapters.node_adapter import (
    NodeAdapter,
    NodeError,
    ScanResult,
)


pytestmark = pytest.mark.integration


@pytest.fixture()
def node(bitcoind_rpc_url: str, bitcoind_clean_chain) -> Iterator[NodeAdapter]:  # type: ignore[no-untyped-def]
    # Depends on bitcoind_clean_chain so multi-test sessions don't accumulate
    # blocks past the halving cliff. 60s timeout covers `generate_to_address`
    # bursts on slow CI runners.
    with NodeAdapter(bitcoind_rpc_url, timeout_seconds=60.0) as adapter:
        yield adapter


@pytest.fixture()
def funding_wallet(node: NodeAdapter) -> str:
    """Create a fresh bitcoind-side wallet that holds spendable coins.

    The wallet name is randomized per test. Mines 150 blocks crediting the
    wallet's first address — regtest has a 100-block coinbase maturity, so
    blocks 1..50 of that batch are mature and spendable.

    Verifies non-zero spendable balance before yielding so we fail fast on
    setup quirks rather than mid-test.
    """
    import time

    name = f"funding_{secrets.token_hex(4)}"
    node.create_wallet(name)
    address = node.get_new_address(wallet=name)
    node.generate_to_address(150, address)

    # Poll the wallet's balance briefly — bitcoind sometimes lags on wallet
    # rescan immediately after bulk block generation.
    deadline = time.time() + 10.0
    previous_url = node._rpc_url
    node._rpc_url = previous_url.rstrip("/") + f"/wallet/{name}"
    try:
        while time.time() < deadline:
            balance_btc = node._call("getbalance")
            if float(balance_btc) > 0:
                break
            time.sleep(0.3)
        else:
            pytest.fail(
                f"funding_wallet {name!r} shows zero balance after 150 mined blocks"
            )
    finally:
        node._rpc_url = previous_url

    return name


# --- basic introspection -----------------------------------------------------


def test_get_blockchain_info(node: NodeAdapter) -> None:
    info = node.get_blockchain_info()
    assert info.chain == "regtest"
    assert info.blocks >= 0
    assert info.headers >= info.blocks
    assert len(info.best_block_hash) == 64


def test_is_healthy_against_real_bitcoind(node: NodeAdapter) -> None:
    assert node.is_healthy() is True


def test_is_healthy_against_unreachable_url() -> None:
    """A bogus URL must produce False, never an exception."""
    with NodeAdapter(
        "http://does-not-resolve.invalid:18443", timeout_seconds=1.0
    ) as bad:
        assert bad.is_healthy() is False


# --- scan_descriptors --------------------------------------------------------


def test_scan_descriptors_finds_funded_address(
    node: NodeAdapter, funding_wallet: str
) -> None:
    """Send to a known address from the funding wallet, then verify
    scan_descriptors picks up the resulting UTXO when scanning that address.

    Uses a small amount (1000 sats — above the 294-sat dust threshold for
    P2WPKH) so the test is tolerant of regtest chains that have accumulated
    many blocks and are past several halvings.
    """
    target = node.get_new_address(wallet=funding_wallet)
    txid = node.send_to_address_from_wallet(funding_wallet, target, 1_000)
    assert len(txid) == 64

    # Mine a block so the tx confirms.
    miner_address = node.get_new_address(wallet=funding_wallet)
    node.generate_to_address(1, miner_address)

    # Now scan for that exact address (scantxoutset takes addresses too via
    # `addr(...)` descriptors).
    result = node.scan_descriptors([f"addr({target})"])

    assert isinstance(result, ScanResult)
    assert result.success is True
    # Match on (txid, vout) since scantxoutset's `address` field can vary
    # by bitcoind version (sometimes absent, sometimes in a different case).
    matching = [u for u in result.utxos if u.txid == txid]
    assert len(matching) >= 1, (
        f"scantxoutset returned no UTXOs for target={target}, txid={txid}; "
        f"got: {result.utxos}"
    )
    # Exactly one output of 1000 sats should be among them (the other vout is
    # the funding wallet's change output, which scantxoutset's `addr({target})`
    # filter does not match).
    assert any(u.amount_sats == 1_000 for u in matching)


def test_scan_descriptors_with_no_match_yields_empty(
    node: NodeAdapter, funding_wallet: str
) -> None:
    """Scanning an `addr(...)` descriptor for a never-used regtest address
    returns no UTXOs."""
    # Use a fresh address from the funding wallet but never send anything to
    # it. scantxoutset against `addr(<that_addr>)` should return an empty set.
    fresh = node.get_new_address(wallet=funding_wallet)
    result = node.scan_descriptors([f"addr({fresh})"])
    assert result.success is True
    assert result.utxos == []
    assert result.total_amount_sats == 0


# --- get_raw_transaction -----------------------------------------------------


def test_get_raw_transaction_returns_decoded_tx(
    node: NodeAdapter, funding_wallet: str
) -> None:
    target = node.get_new_address(wallet=funding_wallet)
    txid = node.send_to_address_from_wallet(funding_wallet, target, 1_000)

    # Confirm so getrawtransaction can find it without txindex (though our
    # regtest does have txindex enabled — see docker-compose.yml).
    miner_address = node.get_new_address(wallet=funding_wallet)
    node.generate_to_address(1, miner_address)

    tx = node.get_raw_transaction(txid, verbose=True)
    assert tx["txid"] == txid
    assert "vout" in tx
    # At least one output paid `target`.
    assert any(
        v.get("scriptPubKey", {}).get("address") == target
        for v in tx["vout"]
    )


# --- get_mempool_entry -------------------------------------------------------


def test_get_mempool_entry_returns_none_for_unknown_tx(
    node: NodeAdapter,
) -> None:
    # txid that has never existed.
    result = node.get_mempool_entry("a" * 64)
    assert result is None


def test_get_mempool_entry_returns_data_for_pending_tx(
    node: NodeAdapter, funding_wallet: str
) -> None:
    target = node.get_new_address(wallet=funding_wallet)
    txid = node.send_to_address_from_wallet(funding_wallet, target, 1_000)
    # Don't mine — tx should still be in the mempool.
    entry = node.get_mempool_entry(txid)
    assert entry is not None
    assert entry["vsize"] > 0
