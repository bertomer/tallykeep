"""Integration tests for M6.3: confirmation tracking through the chain
listener.

When a broadcast PaymentRequest's transaction lands in a block, the
ChainListener must:
  1. Flip the PaymentRequest's status to CONFIRMED.
  2. Set `resulting_ledger_entry_id` on the PaymentRequest.
  3. Emit `banking.payment_request.confirmed` on the bus.

These tests drive the full flow end-to-end:
  - build a watch-only Purse with origin-annotated descriptors
  - fund it from regtest
  - POST /payment-requests, sign in test, /submit-signed, /broadcast
  - mine a confirming block; the chain listener (running in its own
    thread, started by the test) picks up the new tx and links the
    PaymentRequest
"""

from __future__ import annotations

import secrets
import time

import bdkpython as bdk
import pytest


pytestmark = pytest.mark.integration


_BASE_TPUB = (
    "tpubD6NzVbkrYhZ4XYa9MoLt4BiMZ4gkt2faZ4BcmKu2a9te4LDpQmvEz2L2yDERivHxFPnxXXhqDRkUNnQCpZggCyEZLBktV7VaSmwayqMJy1s"
)
_BASE_TPRV = (
    "tprv8ZgxMBicQKsPe5YMU9gHen4Ez3ApihUfykaqUorj9t6FDqy3nP6eoXiAo2ssvpAjoLroQxHqr3R5nE3a5dU3DHTjTgJDd7zrbniJr6nrCzd"
)
_FINGERPRINT = "73c5da0a"
_NEXT_BRANCH = {"value": 500}


def _next_pair() -> tuple[str, str, str, str]:
    base = _NEXT_BRANCH["value"]
    _NEXT_BRANCH["value"] += 2
    return (
        f"wpkh([{_FINGERPRINT}]{_BASE_TPUB}/{base}/*)",
        f"wpkh([{_FINGERPRINT}]{_BASE_TPUB}/{base + 1}/*)",
        f"wpkh([{_FINGERPRINT}]{_BASE_TPRV}/{base}/*)",
        f"wpkh([{_FINGERPRINT}]{_BASE_TPRV}/{base + 1}/*)",
    )


def _purse_body(watch_ext: str, watch_chg: str) -> dict:
    return {
        "name": f"Confirm test {secrets.token_hex(2)}",
        "purpose": "spending",
        "purse_mode": "watch_only",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": watch_ext,
                "change_expression": watch_chg,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _resolve_zmq_endpoint(rpc_url: str) -> str:
    import os
    from urllib.parse import urlparse

    override = os.environ.get("TALLYKEEP_BITCOIND_ZMQ_ENDPOINT", "")
    if override:
        return override
    return f"tcp://{urlparse(rpc_url).hostname}:28332"


def _fund_and_get_parents(client, node, descriptor_id: str, sats: int):  # type: ignore[no-untyped-def]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]
    funding = f"confirm_{secrets.token_hex(4)}"
    node.create_wallet(funding)
    node.generate_to_address(150, node.get_new_address(wallet=funding))
    deadline = time.time() + 10
    while time.time() < deadline:
        previous = node._rpc_url
        node._rpc_url = previous.rstrip("/") + f"/wallet/{funding}"
        try:
            balance = node._call("getbalance")
        finally:
            node._rpc_url = previous
        if float(balance) > 0:
            break
        time.sleep(0.3)
    node.send_to_address_from_wallet(funding, target, sats)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")
    utxos = client.get(
        f"/api/v1/descriptors/{descriptor_id}/utxos?limit=200"
    ).json()["utxos"]
    parents = []
    for u in utxos:
        parents.append(node.get_raw_transaction(u["txid"], verbose=False))
    return funding, parents


def _sign_via_tprv(
    psbt_b64: str,
    sign_ext: str,
    sign_chg: str,
    parent_hexes: list[str],
) -> str:
    desc = bdk.Descriptor(sign_ext, bdk.Network.REGTEST)
    chg = bdk.Descriptor(sign_chg, bdk.Network.REGTEST)
    wallet = bdk.Wallet(
        desc, chg, bdk.Network.REGTEST,
        bdk.Persister.new_in_memory(), lookahead=25,
    )
    wallet.reveal_addresses_to(bdk.KeychainKind.EXTERNAL, 4)
    wallet.reveal_addresses_to(bdk.KeychainKind.INTERNAL, 4)
    if parent_hexes:
        wallet.apply_unconfirmed_txs(
            [
                bdk.UnconfirmedTx(
                    tx=bdk.Transaction(bytes.fromhex(h)),
                    last_seen=int(time.time()),
                )
                for h in parent_hexes
            ]
        )
    psbt = bdk.Psbt(psbt_b64)
    if not wallet.sign(psbt):
        raise RuntimeError("BDK declined to sign")
    return psbt.serialize()


def test_listener_marks_payment_request_confirmed(app_with_db_and_node) -> None:
    """End-to-end: build → sign → submit → broadcast → mine → listener
    confirms. The PaymentRequest must end up with status=confirmed and
    resulting_ledger_entry_id pointing at a real LedgerEntry."""
    from tallykeep.adapters.node_adapter import NodeAdapter
    from tallykeep.infrastructure.event_bus import Event, InMemoryEventBus
    from tallykeep.workers.listeners.chain_listener import ChainListener

    client, factory, node = app_with_db_and_node

    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    funding, parents = _fund_and_get_parents(client, node, descriptor_id, 1_000_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": dest_addr,
            "amount_sats": 250_000,
            "fee_strategy": "normal",
        },
    ).json()
    request_id = created["id"]
    signed = _sign_via_tprv(created["psbt_base64"], sign_ext, sign_chg, parents)

    submitted = client.post(
        f"/api/v1/banking/payment-requests/{request_id}/submit-signed",
        json={"psbt_base64": signed},
    ).json()
    assert submitted["status"] == "awaiting_broadcast"

    # Spin up our own listener pointed at bitcoind ZMQ; we re-use the
    # backend's session factory so writes share the test's database.
    bus = InMemoryEventBus()
    captured: list[Event] = []
    bus.subscribe(["banking.*"], captured.append)

    listener_node = NodeAdapter(node._rpc_url, timeout_seconds=30.0)
    listener = ChainListener(
        zmq_endpoint=_resolve_zmq_endpoint(node._rpc_url),
        node=listener_node,
        bus=bus,
        session_factory=factory,
    )
    listener.start()
    time.sleep(0.3)
    try:
        broadcast = client.post(
            f"/api/v1/banking/payment-requests/{request_id}/broadcast",
        ).json()
        assert broadcast["status"] == "broadcast"
        broadcast_txid = broadcast["broadcast_txid"]
        assert broadcast_txid is not None

        # Confirm the tx by mining a block.
        node.generate_to_address(1, node.get_new_address(wallet=funding))

        deadline = time.time() + 30
        while time.time() < deadline:
            current = client.get(
                f"/api/v1/banking/payment-requests/{request_id}"
            ).json()
            if current["status"] == "confirmed":
                break
            time.sleep(0.3)
        else:
            pytest.fail(
                f"PaymentRequest never reached confirmed status; "
                f"final state: {current}"
            )

        assert current["resulting_ledger_entry_id"] is not None
        assert current["broadcast_txid"] == broadcast_txid

        topics = [e.topic for e in captured]
        assert "banking.payment_request.confirmed" in topics
        confirmed_event = next(
            e for e in captured if e.topic == "banking.payment_request.confirmed"
        )
        assert confirmed_event.payload["id"] == request_id
        assert confirmed_event.payload["txid"] == broadcast_txid
    finally:
        listener.stop()
        listener_node.close()
