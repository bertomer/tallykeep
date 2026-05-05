"""Integration tests for M6.5: PaymentRequest cancellation.

Spec module 06 cancellation rules:
  - Allowed in {DRAFT, AWAITING_SIGNATURE, AWAITING_BROADCAST}.
  - BROADCAST (already in mempool) → 409.
  - Unknown id → 404.
  - After cancel the in-flight lock is released: a new PaymentRequest can
    immediately be created for the same Holding.

Tests that need a real signed transaction (AWAITING_BROADCAST and BROADCAST
paths) use app_with_db_and_node + the tprv signing helper from the M6.3
suite. Simpler status checks use app_with_db only.
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


# --- basic status checks -------------------------------------------------------


def test_cancel_unknown_id_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/banking/payment-requests/00000000-0000-0000-0000-0000000000ff/cancel"
    )
    assert response.status_code == 404


# --- AWAITING_SIGNATURE --------------------------------------------------------


def test_cancel_awaiting_signature_returns_cancelled(app_with_db_and_node) -> None:
    """Cancel a freshly-built PaymentRequest (status=AWAITING_SIGNATURE)."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, _, _ = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 500_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": dest_addr,
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()
    assert created["status"] == "awaiting_signature"

    cancelled = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/cancel"
    )
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "cancelled"
    assert body["id"] == created["id"]


def test_cancel_releases_inflight_lock(app_with_db_and_node) -> None:
    """After cancellation the in-flight-per-Holding lock is released; a new
    PaymentRequest can immediately be created for the same Holding."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, _, _ = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    pay_body = {
        "holding_id": purse["id"],
        "destination": dest_addr,
        "amount_sats": 100_000,
        "fee_strategy": "normal",
    }
    first = client.post("/api/v1/banking/payment-requests", json=pay_body).json()
    # A second attempt while the first is in-flight must fail.
    assert client.post("/api/v1/banking/payment-requests", json=pay_body).status_code == 409

    client.post(f"/api/v1/banking/payment-requests/{first['id']}/cancel")

    # Now a new one must succeed.
    second = client.post("/api/v1/banking/payment-requests", json=pay_body)
    assert second.status_code == 201, second.text


# --- AWAITING_BROADCAST --------------------------------------------------------


def test_cancel_awaiting_broadcast_returns_cancelled(app_with_db_and_node) -> None:
    """Cancel a signed-but-not-yet-broadcast PaymentRequest."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    parents = _fund_purse(client, node, descriptor_id, 500_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": dest_addr,
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()

    signed_psbt = _sign_via_tprv(created["psbt_base64"], sign_ext, sign_chg, parents)
    submitted = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/submit-signed",
        json={"psbt_base64": signed_psbt},
    ).json()
    assert submitted["status"] == "awaiting_broadcast"

    cancelled = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/cancel"
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"


# --- BROADCAST (in mempool) → 409 ---------------------------------------------


def test_cancel_broadcast_returns_409(app_with_db_and_node) -> None:
    """Once a transaction is in the mempool (status=BROADCAST), cancellation
    is not possible on-chain; the endpoint must return 409."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    parents = _fund_purse(client, node, descriptor_id, 500_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": dest_addr,
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()

    signed_psbt = _sign_via_tprv(created["psbt_base64"], sign_ext, sign_chg, parents)
    client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/submit-signed",
        json={"psbt_base64": signed_psbt},
    )
    broadcast = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/broadcast",
    ).json()
    assert broadcast["status"] == "broadcast"

    response = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/cancel"
    )
    assert response.status_code == 409
