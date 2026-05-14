"""Integration tests for the M6.4 Invoice flow.

Covers:
  - POST /banking/invoices creates an Invoice + reserves the next
    unused address + builds a BIP21 URI.
  - The reservation prevents the SAME address from being handed out
    again on a subsequent /invoices POST.
  - GET / GET-by-id / list endpoints.
  - Cancellation flips status to CANCELLED and unblocks the address.
  - GET /qr returns a 400×400 PNG.
  - Payment detection: the chain listener marks the invoice PAID and
    populates resulting_ledger_entry_id when a tx pays the reserved
    address; OVERPAID when the amount is exceeded.
"""

from __future__ import annotations

import secrets
import time

import pytest


pytestmark = pytest.mark.integration


_BASE_TPUB = (
    "tpubD6NzVbkrYhZ4XYa9MoLt4BiMZ4gkt2faZ4BcmKu2a9te4LDpQmvEz2L2yDERivHxFPnxXXhqDRkUNnQCpZggCyEZLBktV7VaSmwayqMJy1s"
)
_FINGERPRINT = "73c5da0a"
_NEXT_BRANCH = {"value": 700}


def _next_pair() -> tuple[str, str]:
    base = _NEXT_BRANCH["value"]
    _NEXT_BRANCH["value"] += 2
    return (
        f"wpkh([{_FINGERPRINT}]{_BASE_TPUB}/{base}/*)",
        f"wpkh([{_FINGERPRINT}]{_BASE_TPUB}/{base + 1}/*)",
    )


def _purse_body(*, gap_limit: int = 5) -> dict:
    ext, chg = _next_pair()
    return {
        "name": f"Invoice test {secrets.token_hex(2)}",
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
                "expression": ext,
                "change_expression": chg,
                "network": "regtest",
                "gap_limit": gap_limit,
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


def _faucet(node, sats_target_addr, sats):  # type: ignore[no-untyped-def]
    funding = f"inv_{secrets.token_hex(4)}"
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
    txid = node.send_to_address_from_wallet(funding, sats_target_addr, sats)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    return funding, txid


# --- create / get / list / cancel -----------------------------------------


def test_create_invoice_returns_201_with_bip21(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()

    response = client.post(
        "/api/v1/banking/invoices",
        json={
            "holding_id": purse["id"],
            "amount_sats": 50_000,
            "description": "Bike payment",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "open"
    assert body["amount_sats"] == 50_000
    assert body["receiving_address"].startswith("bcrt1q")
    assert body["bip21_uri"].startswith(f"bitcoin:{body['receiving_address']}")
    assert "amount=0.00050000" in body["bip21_uri"]
    assert "label=Bike%20payment" in body["bip21_uri"]


def test_create_invoice_amountless(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    body = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"]},
    ).json()
    assert body["amount_sats"] is None
    assert body["bip21_uri"] == f"bitcoin:{body['receiving_address']}"


def test_create_invoice_rejects_unknown_holding(app_with_db) -> None:
    client, _ = app_with_db
    response = client.post(
        "/api/v1/banking/invoices",
        json={
            "holding_id": "00000000-0000-0000-0000-0000000000ff",
            "amount_sats": 1_000,
        },
    )
    assert response.status_code == 404


def test_invoice_reservation_prevents_address_reuse(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()

    first = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    ).json()
    second = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 2_000},
    ).json()
    assert first["receiving_address"] != second["receiving_address"]


def test_invoice_reservation_409_when_gap_exhausted(app_with_db) -> None:
    """Once every address up to gap_limit is reserved, /invoices returns 409."""
    client, _ = app_with_db
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=2)
    ).json()
    # Two addresses, two invoices = exhausted.
    client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    )
    client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    )
    third = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    )
    assert third.status_code == 409


def test_get_invoice_and_list(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    inv = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    ).json()

    by_id = client.get(f"/api/v1/banking/invoices/{inv['id']}").json()
    assert by_id["id"] == inv["id"]

    listed = client.get(
        f"/api/v1/banking/invoices?holding_id={purse['id']}"
    ).json()["invoices"]
    assert any(i["id"] == inv["id"] for i in listed)


def test_cancel_invoice_releases_reservation(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=1)
    ).json()
    first = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    ).json()
    cancelled = client.post(
        f"/api/v1/banking/invoices/{first['id']}/cancel"
    ).json()
    assert cancelled["status"] == "cancelled"

    # Now the address is no longer reserved — a new invoice can grab it.
    second = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    )
    assert second.status_code == 201
    assert second.json()["receiving_address"] == first["receiving_address"]


# --- QR endpoint -----------------------------------------------------------


def test_qr_endpoint_returns_png(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    inv = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 1_000},
    ).json()

    qr = client.get(f"/api/v1/banking/invoices/{inv['id']}/qr")
    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/png"
    # PNG magic bytes
    assert qr.content[:8] == b"\x89PNG\r\n\x1a\n"


# --- payment detection ----------------------------------------------------


def test_listener_marks_invoice_paid_when_address_funded(
    app_with_db_and_node,
) -> None:
    """End-to-end: create an Invoice on a funded purse's next address,
    pay exactly the invoice amount, mine, and verify the invoice goes
    to PAID with `resulting_ledger_entry_id` linked."""
    from tallykeep.adapters.node_adapter import NodeAdapter
    from tallykeep.infrastructure.event_bus import Event, InMemoryEventBus
    from tallykeep.workers.listeners.chain_listener import ChainListener

    client, factory, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()

    invoice = client.post(
        "/api/v1/banking/invoices",
        json={
            "holding_id": purse["id"],
            "amount_sats": 25_000,
            "description": "exact pay",
        },
    ).json()

    bus = InMemoryEventBus()
    captured: list[Event] = []
    bus.subscribe(["banking.invoice.*"], captured.append)
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
        _, _ = _faucet(node, invoice["receiving_address"], 25_000)

        deadline = time.time() + 30
        while time.time() < deadline:
            current = client.get(
                f"/api/v1/banking/invoices/{invoice['id']}"
            ).json()
            if current["status"] in ("paid", "overpaid"):
                break
            time.sleep(0.3)
        else:
            pytest.fail(f"invoice never marked paid; final: {current}")

        assert current["status"] == "paid"
        assert current["resulting_ledger_entry_id"] is not None

        topics = [e.topic for e in captured]
        assert "banking.invoice.paid" in topics
    finally:
        listener.stop()
        listener_node.close()


def test_listener_marks_invoice_overpaid_when_amount_exceeded(
    app_with_db_and_node,
) -> None:
    from tallykeep.adapters.node_adapter import NodeAdapter
    from tallykeep.infrastructure.event_bus import InMemoryEventBus
    from tallykeep.workers.listeners.chain_listener import ChainListener

    client, factory, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    invoice = client.post(
        "/api/v1/banking/invoices",
        json={"holding_id": purse["id"], "amount_sats": 10_000},
    ).json()

    bus = InMemoryEventBus()
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
        # Pay 50k for a 10k invoice → overpaid.
        _faucet(node, invoice["receiving_address"], 50_000)

        deadline = time.time() + 30
        while time.time() < deadline:
            current = client.get(
                f"/api/v1/banking/invoices/{invoice['id']}"
            ).json()
            if current["status"] in ("paid", "overpaid"):
                break
            time.sleep(0.3)
        else:
            pytest.fail(f"invoice never marked: {current}")

        assert current["status"] == "overpaid"
    finally:
        listener.stop()
        listener_node.close()
