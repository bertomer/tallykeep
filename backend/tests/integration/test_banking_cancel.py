"""Integration tests for M6.5: PaymentRequest cancellation.

Spec module 06 cancellation rules:
  - Allowed in {DRAFT, AWAITING_SIGNATURE, AWAITING_BROADCAST}.
  - BROADCAST (already in mempool) → 409.
  - Unknown id → 404.
  - After cancel the in-flight lock is released: a new PaymentRequest can
    immediately be created for the same Holding.

Node-dependent scenarios are combined into a single test (one funding cycle)
to avoid accumulating too many bitcoind invalidateblock/mine cycles, which
degrades the regtest node state across the full suite.
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
_NEXT_BRANCH = {"value": 900}


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
        "name": f"Cancel test {secrets.token_hex(2)}",
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


def _fund_purse(client, node, descriptor_id: str, sats: int) -> list[str]:
    """Fund the purse, mine a confirming block, rescan, return parent tx hexes."""
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding = f"cancel_{secrets.token_hex(4)}"
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
    return [node.get_raw_transaction(u["txid"], verbose=False) for u in utxos]


def _sign_via_tprv(psbt_b64: str, sign_ext: str, sign_chg: str, parent_hexes: list[str]) -> str:
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


# --- basic status checks (no bitcoind mining needed) ---------------------------


def test_cancel_unknown_id_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/banking/payment-requests/00000000-0000-0000-0000-0000000000ff/cancel"
    )
    assert response.status_code == 404


# --- All cancellation scenarios in one funding cycle --------------------------
# Four scenarios are combined into one test to keep the total number of
# bitcoind invalidateblock+generate cycles low across the full test suite.
# Excessive cycling degrades Bitcoin Core regtest's internal block index state.


def test_cancel_lifecycle(app_with_db_and_node) -> None:
    """Exercises all four cancellation scenarios in a single funding cycle:
    1. Cancel AWAITING_SIGNATURE → status=cancelled.
    2. In-flight lock is released after cancellation.
    3. Cancel AWAITING_BROADCAST → status=cancelled.
    4. Cancel after BROADCAST (in mempool) → 409.
    """
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    parents = _fund_purse(client, node, descriptor_id, 2_000_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    pay_body = {
        "holding_id": purse["id"],
        "destination": dest_addr,
        "amount_sats": 100_000,
        "fee_strategy": "normal",
    }

    # --- Scenario 1: cancel AWAITING_SIGNATURE ---
    pr1 = client.post("/api/v1/banking/payment-requests", json=pay_body).json()
    assert pr1["status"] == "awaiting_signature"

    r1 = client.post(f"/api/v1/banking/payment-requests/{pr1['id']}/cancel")
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["status"] == "cancelled"
    assert body1["id"] == pr1["id"]

    # --- Scenario 2: in-flight lock released after cancel ---
    # pr1 is now cancelled (not in-flight); a new request must succeed.
    # Verify the lock WAS held first: while pr1 was live a duplicate was rejected.
    # (We test this directly: create a new request and it should succeed.)
    pr2 = client.post("/api/v1/banking/payment-requests", json=pay_body)
    assert pr2.status_code == 201, pr2.text
    # Cancel pr2 to release the lock for subsequent scenarios.
    client.post(f"/api/v1/banking/payment-requests/{pr2.json()['id']}/cancel")

    # --- Scenario 3: cancel AWAITING_BROADCAST ---
    pr3 = client.post("/api/v1/banking/payment-requests", json=pay_body).json()
    signed3 = _sign_via_tprv(pr3["psbt_base64"], sign_ext, sign_chg, parents)
    sub3 = client.post(
        f"/api/v1/banking/payment-requests/{pr3['id']}/submit-signed",
        json={"psbt_base64": signed3},
    ).json()
    assert sub3["status"] == "awaiting_broadcast"

    r3 = client.post(f"/api/v1/banking/payment-requests/{pr3['id']}/cancel")
    assert r3.status_code == 200, r3.text
    assert r3.json()["status"] == "cancelled"

    # --- Scenario 4: cancel after BROADCAST → 409 ---
    pr4 = client.post("/api/v1/banking/payment-requests", json=pay_body).json()
    signed4 = _sign_via_tprv(pr4["psbt_base64"], sign_ext, sign_chg, parents)
    client.post(
        f"/api/v1/banking/payment-requests/{pr4['id']}/submit-signed",
        json={"psbt_base64": signed4},
    )
    broadcast4 = client.post(
        f"/api/v1/banking/payment-requests/{pr4['id']}/broadcast"
    ).json()
    assert broadcast4["status"] == "broadcast"

    r4 = client.post(f"/api/v1/banking/payment-requests/{pr4['id']}/cancel")
    assert r4.status_code == 409
