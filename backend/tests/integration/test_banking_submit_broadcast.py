"""Integration tests for M6.2: submit-signed + broadcast + fee-estimate.

These tests use the standard BIP-39 test mnemonic ("abandon ... about")
so we have a private key that matches the watch-only tpub the rest of
the suite uses. The corresponding master tprv is `tprv8ZgxMBicQKsPe5YM...`.

Flow:
  1. Build a watch-only Purse on regtest with the tpub.
  2. Fund a watched address.
  3. POST /banking/payment-requests to get an unsigned PSBT.
  4. Sign the PSBT in-test using a fresh BDK wallet that holds the
     matching tprv descriptors and has been taught about our UTXOs via
     `apply_unconfirmed_txs`.
  5. POST /submit-signed with the signed PSBT.
  6. POST /broadcast.
  7. Assert the txid appears in bitcoind's mempool.
"""

from __future__ import annotations

import base64
import secrets
import time

import bdkpython as bdk
import pytest


pytestmark = pytest.mark.integration


# Master tpub/tprv derived from the standard "abandon abandon ... about"
# mnemonic — bdkpython gives these specific values for that mnemonic on
# REGTEST. The other M-test files use a different tpub (the testnet
# equivalent of BIP32 test vector 1) — we don't reuse it because we
# don't have a tprv to sign with for that one.
_BASE_TPUB = (
    "tpubD6NzVbkrYhZ4XYa9MoLt4BiMZ4gkt2faZ4BcmKu2a9te4LDpQmvEz2L2yDERivHxFPnxXXhqDRkUNnQCpZggCyEZLBktV7VaSmwayqMJy1s"
)
_BASE_TPRV = (
    "tprv8ZgxMBicQKsPe5YMU9gHen4Ez3ApihUfykaqUorj9t6FDqy3nP6eoXiAo2ssvpAjoLroQxHqr3R5nE3a5dU3DHTjTgJDd7zrbniJr6nrCzd"
)
_NEXT_BRANCH = {"value": 200}


_FINGERPRINT = "73c5da0a"  # master fingerprint for the abandon/about mnemonic


def _next_pair() -> tuple[str, str, str, str]:
    """Return (watch_external, watch_change, sign_external, sign_change)
    for a fresh branch index — keeps each test isolated.

    Each descriptor includes origin annotation `[fingerprint]` so
    BDK populates bip32_derivation in the PSBT inputs. Without that
    annotation, the PSBT carries an unsigned script with no pubkey
    metadata, which makes finalisation fail with "Missing pubkey for
    a pkh/wpkh".
    """
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
        "name": f"Submit test {secrets.token_hex(2)}",
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


def _fund(client, node, descriptor_id: str, sats: int) -> str:
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]
    funding = f"submit_{secrets.token_hex(4)}"
    node.create_wallet(funding)
    funding_addr = node.get_new_address(wallet=funding)
    node.generate_to_address(150, funding_addr)
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
    miner = node.get_new_address(wallet=funding)
    node.generate_to_address(1, miner)
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")
    return target


def _sign_psbt_with_tprv(
    psbt_base64: str,
    *,
    sign_external_descriptor: str,
    sign_change_descriptor: str,
    parent_raw_hexes: list[str],
    max_external_index: int,
    max_change_index: int,
) -> str:
    """Sign the PSBT via a fresh BDK wallet built from signing descriptors.

    We feed the wallet the parent transactions of every input so its
    UTXO index treats them as `is_mine`; only then does `wallet.sign`
    produce signatures.
    """
    desc = bdk.Descriptor(sign_external_descriptor, bdk.Network.REGTEST)
    chg = bdk.Descriptor(sign_change_descriptor, bdk.Network.REGTEST)
    lookahead = max(max_external_index, max_change_index) + 25
    wallet = bdk.Wallet(
        desc, chg, bdk.Network.REGTEST, bdk.Persister.new_in_memory(),
        lookahead=lookahead,
    )
    wallet.reveal_addresses_to(bdk.KeychainKind.EXTERNAL, max_external_index)
    wallet.reveal_addresses_to(bdk.KeychainKind.INTERNAL, max_change_index)
    if parent_raw_hexes:
        unconfirmed = [
            bdk.UnconfirmedTx(
                tx=bdk.Transaction(bytes.fromhex(h)),
                last_seen=int(time.time()),
            )
            for h in parent_raw_hexes
        ]
        wallet.apply_unconfirmed_txs(unconfirmed)

    psbt = bdk.Psbt(psbt_base64)
    finalized = wallet.sign(psbt)
    if not finalized:
        raise RuntimeError("BDK wallet declined to finalize the PSBT")
    return psbt.serialize()


def _parent_raw_hexes_for_descriptor(node, client, descriptor_id) -> list[str]:  # type: ignore[no-untyped-def]
    """Pull the parent-tx hex for every UTXO our descriptor owns."""
    utxos = client.get(
        f"/api/v1/descriptors/{descriptor_id}/utxos?limit=200"
    ).json()["utxos"]
    seen: set[str] = set()
    out: list[str] = []
    for u in utxos:
        if u["txid"] in seen:
            continue
        seen.add(u["txid"])
        out.append(node.get_raw_transaction(u["txid"], verbose=False))
    return out


# --- happy path ------------------------------------------------------------


def test_submit_signed_and_broadcast_full_flow(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund(client, node, descriptor_id, 1_000_000)

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
    psbt_b64 = created["psbt_base64"]

    parents = _parent_raw_hexes_for_descriptor(node, client, descriptor_id)
    signed_b64 = _sign_psbt_with_tprv(
        psbt_b64,
        sign_external_descriptor=sign_ext,
        sign_change_descriptor=sign_chg,
        parent_raw_hexes=parents,
        max_external_index=4,
        max_change_index=4,
    )

    submit = client.post(
        f"/api/v1/banking/payment-requests/{request_id}/submit-signed",
        json={"psbt_base64": signed_b64},
    )
    assert submit.status_code == 200, submit.text
    submit_body = submit.json()
    assert submit_body["status"] == "awaiting_broadcast"
    assert submit_body["signed_transaction_hex"] is not None

    broadcast = client.post(
        f"/api/v1/banking/payment-requests/{request_id}/broadcast",
    )
    assert broadcast.status_code == 200, broadcast.text
    broadcast_body = broadcast.json()
    assert broadcast_body["status"] == "broadcast"
    assert broadcast_body["broadcast_txid"] is not None

    # The tx must be visible in bitcoind's mempool now.
    entry = node.get_mempool_entry(broadcast_body["broadcast_txid"])
    assert entry is not None
    assert entry["fees"]["base"] > 0


def test_submit_signed_with_finalized_tx_hex(app_with_db_and_node) -> None:
    """The submit-signed endpoint also accepts a fully-finalized hex (no
    PSBT)."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, sign_ext, sign_chg = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund(client, node, descriptor_id, 1_000_000)

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
    request_id = created["id"]

    parents = _parent_raw_hexes_for_descriptor(node, client, descriptor_id)
    signed_b64 = _sign_psbt_with_tprv(
        created["psbt_base64"],
        sign_external_descriptor=sign_ext,
        sign_change_descriptor=sign_chg,
        parent_raw_hexes=parents,
        max_external_index=4,
        max_change_index=4,
    )
    psbt = bdk.Psbt(signed_b64)
    psbt.finalize()
    final_tx = psbt.extract_tx()
    finalized_hex = final_tx.serialize().hex()

    submit = client.post(
        f"/api/v1/banking/payment-requests/{request_id}/submit-signed",
        json={"signed_transaction_hex": finalized_hex},
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["status"] == "awaiting_broadcast"


# --- error paths -----------------------------------------------------------


def test_submit_signed_rejects_unsigned_psbt(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, _, _ = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund(client, node, descriptor_id, 1_000_000)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()
    submit = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/submit-signed",
        json={"psbt_base64": created["psbt_base64"]},  # original — no signatures added
    )
    assert submit.status_code == 400, submit.text
    assert "finalis" in submit.json()["detail"].lower()


def test_submit_signed_404_for_unknown_request(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/banking/payment-requests/00000000-0000-0000-0000-0000000000ff/submit-signed",
        json={"psbt_base64": "AAAA"},
    )
    assert response.status_code == 404


def test_submit_signed_requires_a_body(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, _, _ = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund(client, node, descriptor_id, 1_000_000)
    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()
    response = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/submit-signed",
        json={},
    )
    assert response.status_code == 400


def test_broadcast_409_when_not_signed(app_with_db_and_node) -> None:
    """Calling /broadcast on a PaymentRequest that's still
    AWAITING_SIGNATURE should be rejected."""
    client, _, node = app_with_db_and_node
    watch_ext, watch_chg, _, _ = _next_pair()
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(watch_ext, watch_chg)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund(client, node, descriptor_id, 1_000_000)
    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()
    response = client.post(
        f"/api/v1/banking/payment-requests/{created['id']}/broadcast",
    )
    assert response.status_code == 409


# --- fee-estimate ----------------------------------------------------------


def test_fee_estimate_named_tier(app_with_db_and_node) -> None:
    client, _, _ = app_with_db_and_node
    res = client.post(
        "/api/v1/banking/fee-estimate", json={"strategy": "normal"}
    ).json()
    assert "sat_per_vbyte" in res
    assert res["target_blocks"] == 6
    assert res["sat_per_vbyte"] > 0


def test_fee_estimate_explicit_target_blocks(app_with_db_and_node) -> None:
    client, _, _ = app_with_db_and_node
    res = client.post(
        "/api/v1/banking/fee-estimate", json={"target_blocks": 10}
    ).json()
    assert res["target_blocks"] == 10
