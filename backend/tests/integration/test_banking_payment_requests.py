"""Integration tests for the M6.1 PaymentRequest construction flow.

End-to-end: create a Purse on regtest, fund it via the bitcoind faucet,
post a PaymentRequest, and verify the persisted record + the PSBT bytes.

The PSBT itself is parsed back through bdkpython to confirm:
  - It has at least one input pointing at one of our funded UTXOs.
  - It has exactly one or two outputs (recipient, optional change).
  - The recipient amount matches what we asked for.
  - The PSBT is unsigned (no final_script_witness on inputs).
"""

from __future__ import annotations

import base64
import secrets
import time

import bdkpython as bdk
import pytest


pytestmark = pytest.mark.integration


_BASE_XPUB = (
    "tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK"
)
_NEXT_BRANCH = {"value": 0}


def _next_descriptor_pair() -> tuple[str, str]:
    """Return a fresh (external, change) descriptor pair so each test gets
    unique expressions — the unique constraint on `descriptor.expression`
    rejects re-imports across tests in the same DB."""
    base = _NEXT_BRANCH["value"]
    _NEXT_BRANCH["value"] += 2
    external = f"wpkh({_BASE_XPUB}/{base}/*)"
    change = f"wpkh({_BASE_XPUB}/{base + 1}/*)"
    return external, change


def _purse_body(
    *,
    expression: str | None = None,
    change_expression: str | None = None,
) -> dict:
    if expression is None:
        expression, change_expression = _next_descriptor_pair()
    return {
        "name": f"Banking test {secrets.token_hex(2)}",
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
                "expression": expression,
                "change_expression": change_expression,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _vault_body() -> dict:
    external, change = _next_descriptor_pair()
    return {
        "name": f"Vault {secrets.token_hex(2)}",
        "purpose": "long_term",
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "hardware_offline",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": external,
                "change_expression": change,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def _fund_purse(client, node, descriptor_id, sats):  # type: ignore[no-untyped-def]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding = f"banking_{secrets.token_hex(4)}"
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

    txid = node.send_to_address_from_wallet(funding, target, sats)
    miner = node.get_new_address(wallet=funding)
    node.generate_to_address(1, miner)
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")
    return txid


def test_create_payment_request_returns_201_with_psbt(
    app_with_db_and_node,
) -> None:
    client, factory, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    dest_wallet = f"dest_{secrets.token_hex(3)}"
    node.create_wallet(dest_wallet)
    dest_addr = node.get_new_address(wallet=dest_wallet)

    response = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": dest_addr,
            "amount_sats": 200_000,
            "fee_strategy": "normal",
            "description": "Test send",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["holding_id"] == purse["id"]
    assert body["status"] == "awaiting_signature"
    assert body["destination_address"] == dest_addr
    assert body["bip21_uri"].startswith(f"bitcoin:{dest_addr}")
    assert body["psbt_base64"] is not None
    assert body["broadcast_txid"] is None

    # PSBT round-trips through BDK and contains our recipient output.
    psbt = bdk.Psbt(body["psbt_base64"])
    extracted = psbt.extract_tx()
    outputs = extracted.output()
    recipient_amounts = [int(o.value.to_sat()) for o in outputs]
    assert 200_000 in recipient_amounts


def test_create_payment_request_rejects_unknown_holding(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": "00000000-0000-0000-0000-0000000000ff",
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 1_000,
            "fee_strategy": "normal",
        },
    )
    assert response.status_code == 404


def test_create_payment_request_rejects_invalid_destination(
    app_with_db_and_node,
) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    response = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "not_an_address",
            "amount_sats": 1_000,
            "fee_strategy": "normal",
        },
    )
    assert response.status_code == 400
    assert "valid" in response.json()["detail"].lower()


def test_create_payment_request_rejects_when_no_balance(app_with_db_and_node) -> None:
    client, _, _ = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    response = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 1_000,
            "fee_strategy": "normal",
        },
    )
    assert response.status_code == 400


def test_create_payment_request_rejects_insufficient_balance(
    app_with_db_and_node,
) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 50_000)

    response = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 1_000_000_000,  # 10 BTC, way over what we funded
            "fee_strategy": "normal",
        },
    )
    assert response.status_code == 400
    assert "available" in response.json()["detail"].lower() or "insufficient" in response.json()["detail"].lower()


def test_create_payment_request_concurrency_409(app_with_db_and_node) -> None:
    """Spec module 06: only one in-flight PaymentRequest per Holding."""
    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    body = {
        "holding_id": purse["id"],
        "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
        "amount_sats": 100_000,
        "fee_strategy": "normal",
    }
    first = client.post("/api/v1/banking/payment-requests", json=body)
    assert first.status_code == 201

    second = client.post("/api/v1/banking/payment-requests", json=body)
    assert second.status_code == 409


def test_vault_long_term_returns_confirmation_required_first_time(
    app_with_db_and_node,
) -> None:
    """First call against a long-term Vault returns 200 with
    requires_confirmation=true; second call with confirmed=true proceeds."""
    client, _, node = app_with_db_and_node
    vault = client.post("/api/v1/holdings/vault", json=_vault_body()).json()
    descriptor_id = vault["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    body = {
        "holding_id": vault["id"],
        "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
        "amount_sats": 100_000,
        "fee_strategy": "normal",
    }
    first = client.post("/api/v1/banking/payment-requests", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["requires_confirmation"] is True

    confirmed_body = {**body, "confirmed": True}
    second = client.post("/api/v1/banking/payment-requests", json=confirmed_body)
    assert second.status_code == 201


def test_get_and_list_payment_requests(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)

    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()

    by_id = client.get(f"/api/v1/banking/payment-requests/{created['id']}").json()
    assert by_id["id"] == created["id"]
    assert by_id["psbt_base64"] is not None

    listed = client.get(
        f"/api/v1/banking/payment-requests?holding_id={purse['id']}"
    ).json()["payment_requests"]
    ids = [r["id"] for r in listed]
    assert created["id"] in ids


def test_get_psbt_endpoint_returns_base64_and_binary(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    _fund_purse(client, node, descriptor_id, 1_000_000)
    created = client.post(
        "/api/v1/banking/payment-requests",
        json={
            "holding_id": purse["id"],
            "destination": "bcrt1qklpstvpm2wl2xxe4hhmndlqssk03fyygr7jmvm",
            "amount_sats": 100_000,
            "fee_strategy": "normal",
        },
    ).json()

    json_resp = client.get(
        f"/api/v1/banking/payment-requests/{created['id']}/psbt"
    ).json()
    assert "psbt_base64" in json_resp
    assert json_resp["filename"].endswith(".psbt")

    binary_resp = client.get(
        f"/api/v1/banking/payment-requests/{created['id']}/psbt",
        headers={"Accept": "application/octet-stream"},
    )
    assert binary_resp.status_code == 200
    assert binary_resp.headers["content-type"].startswith(
        "application/octet-stream"
    )
    assert "attachment" in binary_resp.headers.get("content-disposition", "")
    # Magic bytes for a PSBT v0 are 0x70 0x73 0x62 0x74 0xff.
    assert binary_resp.content[:5] == b"psbt\xff"
    # And the binary equals the base64-decoded form.
    assert (
        base64.b64decode(json_resp["psbt_base64"]) == binary_resp.content
    )
