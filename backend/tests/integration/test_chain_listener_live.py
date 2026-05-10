"""End-to-end ChainListener test against a real bitcoind regtest.

Flow:
  1. Boot a Purse with a watch-only descriptor.
  2. Start a ChainListener pointed at our test bitcoind ZMQ port.
  3. Fund a watched address from the bitcoind faucet.
  4. Mine a block to trigger hashtx + hashblock.
  5. Assert the listener persisted a UTXO + LedgerEntry AND emitted the
     expected events on a captured InMemoryEventBus.

The listener runs in its own thread, so the test polls (with a generous
timeout) for the assertions to converge — there's no clean signal for "the
listener has finished processing this notification".
"""

from __future__ import annotations

import os
import secrets
import time

import pytest


pytestmark = pytest.mark.integration


WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


def _purse_body() -> dict:
    return {
        "name": f"Listener test {secrets.token_hex(2)}",
        "purpose": "spending",
        "seed_origin": "external_watch_only",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": WPKH_REGTEST,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _make_funding_wallet(node) -> str:  # type: ignore[no-untyped-def]
    name = f"listener_{secrets.token_hex(4)}"
    node.create_wallet(name)
    address = node.get_new_address(wallet=name)
    node.generate_to_address(150, address)
    deadline = time.time() + 10.0
    previous_url = node._rpc_url
    node._rpc_url = previous_url.rstrip("/") + f"/wallet/{name}"
    try:
        while time.time() < deadline:
            balance = node._call("getbalance")
            if float(balance) > 0:
                break
            time.sleep(0.3)
        else:
            pytest.fail("funding wallet shows zero balance after 150 blocks")
    finally:
        node._rpc_url = previous_url
    return name


def _resolve_zmq_endpoint(rpc_url: str) -> str:
    """Derive the ZMQ endpoint from the RPC URL or env override.

    docker-compose binds bitcoind ZMQ on host 127.0.0.1:28332. The same
    docker network exposes it as tcp://bitcoind:28332. Tests running on the
    host need 127.0.0.1; CI inside the container needs `bitcoind`. Honour
    `TALLYKEEP_BITCOIND_ZMQ_ENDPOINT` if set.
    """
    override = os.environ.get("TALLYKEEP_BITCOIND_ZMQ_ENDPOINT", "")
    if override:
        return override
    # The TALLYKEEP_BITCOIND_RPC_URL env variable is something like
    # http://tallykeep:tallykeep_dev@bitcoind:18443 in-container; derive the
    # ZMQ endpoint from the same hostname.
    from urllib.parse import urlparse

    parsed = urlparse(rpc_url)
    host = parsed.hostname or "127.0.0.1"
    return f"tcp://{host}:28332"


def test_listener_persists_and_emits_on_block_confirmation(
    app_with_db_and_node,
) -> None:
    from tallykeep.infrastructure.event_bus import Event, InMemoryEventBus
    from tallykeep.models import LedgerEntryRow, UTXORow
    from tallykeep.workers.listeners.chain_listener import ChainListener

    client, factory, node = app_with_db_and_node

    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    bus = InMemoryEventBus()
    captured: list[Event] = []
    bus.subscribe(["chain.*", "holding.*", "ledger_entry.*"], captured.append)

    zmq_endpoint = _resolve_zmq_endpoint(node._rpc_url)

    # The listener and the test share a bitcoind, but NodeAdapter is not thread-
    # safe (it mutates `_rpc_url` for wallet-scoped RPC). Give the listener its
    # own adapter so concurrent calls cannot collide.
    from tallykeep.adapters.node_adapter import NodeAdapter

    listener_node = NodeAdapter(node._rpc_url, timeout_seconds=30.0)
    listener = ChainListener(
        zmq_endpoint=zmq_endpoint,
        node=listener_node,
        bus=bus,
        session_factory=factory,
    )
    # Stage the funding wallet BEFORE the listener subscribes so the listener
    # doesn't see (and serially process) the 150 coinbase + hashblock events
    # generated to build wallet balance. The listener should only need to
    # observe our single spend tx and the block that confirms it.
    funding = _make_funding_wallet(node)

    listener.start()
    # Tiny warmup so the SUB socket is fully wired before the publisher fires
    # its first relevant message — avoids ZMQ's slow-joiner edge case.
    time.sleep(0.3)
    try:
        txid = node.send_to_address_from_wallet(funding, target, 1_500)
        node.generate_to_address(1, node.get_new_address(wallet=funding))

        # Wait up to 30s for the listener to: see hashtx, fetch the decoded
        # tx, persist it, then see hashblock, refresh the height, and emit.
        # Generous deadline because bitcoind's default rpcthreads=4 plus the
        # other RPC traffic in this test (faucet, mining, ZMQ) can briefly
        # serialise the listener's getrawtransaction call.
        # bitcoind randomises output ordering for privacy, so our 1500-sat
        # payment can land at vout=0 OR vout=1 (the change vout being the
        # other). Match by (txid, value) so the test is order-agnostic.
        deadline = time.time() + 30.0
        while time.time() < deadline:
            with factory() as session:
                row = (
                    session.query(UTXORow)
                    .filter_by(txid=txid, value_sats=1_500)
                    .one_or_none()
                )
                if row is not None and row.confirmation_height is not None:
                    break
            time.sleep(0.3)
        else:
            pytest.fail(f"listener never persisted UTXO for txid {txid}")

        with factory() as session:
            utxo = (
                session.query(UTXORow)
                .filter_by(txid=txid, value_sats=1_500)
                .one()
            )
            assert utxo.value_sats == 1_500
            assert utxo.confirmation_height is not None

            entries = session.query(LedgerEntryRow).filter_by(
                source_reference=txid
            ).all()
            assert len(entries) == 1
            assert entries[0].direction == "incoming"
            assert entries[0].net_amount_sats == 1_500

        # The listener emits at least one tx event (mempool or confirmed) and
        # a holding.utxo.received. We tolerate either order — both happen
        # within the 15s window.
        topics = {e.topic for e in captured}
        assert "holding.utxo.received" in topics, captured
        assert any(t.startswith("chain.tx.") for t in topics), captured
        assert "ledger_entry.requires_categorization" in topics, captured
    finally:
        listener.stop()
        listener_node.close()
