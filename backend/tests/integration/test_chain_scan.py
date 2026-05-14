"""End-to-end chain-scan integration test.

Flow:
  1. Create a Purse on regtest with a watch-only descriptor.
  2. Read one of the pre-derived addresses from the API.
  3. Use the bitcoind faucet wallet to send sats to that address.
  4. Mine a block so the tx confirms.
  5. POST /api/v1/descriptors/{id}/rescan.
  6. Verify the UTXO, the balance, and a single LedgerEntry per discovered UTXO.

Uses the standard tpub from the abandon-...-about test mnemonic. tpub keys
share BIP 32 magic bytes between testnet and regtest, so bdkpython produces
bcrt1q addresses when we attach `network=regtest`.
"""

from __future__ import annotations

import secrets

import pytest


pytestmark = pytest.mark.integration


# tpub derived from the abandon-abandon-...-about test mnemonic. Used for any
# regtest-compatible test that needs a stable, well-known xpub.
WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


def _purse_body(*, descriptor_name: str = "main", gap_limit: int = 10) -> dict:
    return {
        "name": f"Smoke wallet {secrets.token_hex(2)}",
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
                "name": descriptor_name,
                "expression": WPKH_REGTEST,
                "network": "regtest",
                "gap_limit": gap_limit,
            }
        ],
    }


def _make_funding_wallet(node) -> str:  # type: ignore[no-untyped-def]
    """Mirror of the test_node_adapter fixture, inlined here so this file
    doesn't depend on it."""
    import time

    name = f"chainscan_{secrets.token_hex(4)}"
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
            pytest.fail(f"funding wallet {name!r} shows zero balance after 150 blocks")
    finally:
        node._rpc_url = previous_url

    return name


def test_rescan_finds_utxo_and_creates_ledger_entry(
    app_with_db_and_node,
) -> None:
    """Tolerant of regtest chains that have accumulated UTXOs from prior
    runs against this same xpub: assertions target the specific (txid, value)
    we just created, not absolute counts."""
    client, factory, node = app_with_db_and_node

    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=10)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]

    addresses = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=10"
    ).json()["addresses"]
    target = addresses[0]["address"]
    assert target.startswith("bcrt1q"), target

    funding = _make_funding_wallet(node)
    txid = node.send_to_address_from_wallet(funding, target, 1_000)
    miner_address = node.get_new_address(wallet=funding)
    node.generate_to_address(1, miner_address)

    rescan = client.post(
        f"/api/v1/descriptors/{descriptor_id}/rescan"
    ).json()
    assert rescan["utxos_discovered"] >= 1
    assert rescan["ledger_entries_created"] >= 1
    assert rescan["height_at_scan"] > 0

    utxos = client.get(
        f"/api/v1/descriptors/{descriptor_id}/utxos?limit=200"
    ).json()["utxos"]
    matching = [u for u in utxos if u["txid"] == txid]
    assert len(matching) == 1, (
        f"expected exactly one UTXO for our txid {txid}; got: {matching}"
    )
    u = matching[0]
    assert u["value_sats"] == 1_000
    assert u["confirmation_height"] is not None
    assert u["is_spent"] is False
    assert u["is_frozen"] is False

    balance = client.get(
        f"/api/v1/descriptors/{descriptor_id}/balance"
    ).json()
    assert balance["confirmed_sats"] >= 1_000

    from tallykeep.models import (
        LedgerEntryHoldingLinkRow,
        LedgerEntryRow,
    )

    with factory() as session:
        entry = session.query(LedgerEntryRow).filter_by(
            source="onchain_transaction", source_reference=txid
        ).one()
        assert entry.direction == "incoming"
        assert entry.net_amount_sats == 1_000

        link = session.query(LedgerEntryHoldingLinkRow).filter_by(
            ledger_entry_id=entry.id, holding_id=purse["id"]
        ).one()
        assert link.holding_amount_sats == 1_000


def test_rescan_is_idempotent(app_with_db_and_node) -> None:
    """Re-running the scan must not duplicate UTXOs or LedgerEntries.

    Idempotency holds regardless of how many UTXOs were discovered on the
    first scan: the second scan's `utxos_discovered` must be 0 and
    `utxos_pre_existing` must equal the prior `utxos_discovered`.
    """
    client, _, node = app_with_db_and_node

    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=5)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding = _make_funding_wallet(node)
    txid = node.send_to_address_from_wallet(funding, target, 1_500)
    node.generate_to_address(1, node.get_new_address(wallet=funding))

    first = client.post(f"/api/v1/descriptors/{descriptor_id}/rescan").json()
    assert first["utxos_discovered"] >= 1
    pre_count = first["utxos_discovered"]

    second = client.post(f"/api/v1/descriptors/{descriptor_id}/rescan").json()
    assert second["utxos_discovered"] == 0
    assert second["utxos_pre_existing"] == pre_count

    utxos = client.get(
        f"/api/v1/descriptors/{descriptor_id}/utxos?limit=200"
    ).json()["utxos"]
    matching = [u for u in utxos if u["txid"] == txid]
    assert len(matching) == 1
    assert matching[0]["value_sats"] == 1_500


def test_rescan_unknown_descriptor_returns_404(app_with_db_and_node) -> None:
    client, _, _ = app_with_db_and_node
    response = client.post(
        "/api/v1/descriptors/00000000-0000-0000-0000-0000000000ff/rescan"
    )
    assert response.status_code == 404


def test_freeze_unfreeze_roundtrip(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=5)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]
    funding = _make_funding_wallet(node)
    target_funding_txid = node.send_to_address_from_wallet(funding, target, 2_000)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")
    utxos = client.get(
        f"/api/v1/descriptors/{descriptor_id}/utxos?limit=200"
    ).json()["utxos"]
    ours = [u for u in utxos if u["txid"] == target_funding_txid]
    assert len(ours) == 1
    utxo_id = ours[0]["id"]

    frozen = client.post(f"/api/v1/utxos/{utxo_id}/freeze").json()
    assert frozen["is_frozen"] is True

    frozen_only = client.get("/api/v1/utxos?frozen=true&limit=200").json()["utxos"]
    assert any(u["id"] == utxo_id for u in frozen_only)

    unfrozen = client.post(f"/api/v1/utxos/{utxo_id}/unfreeze").json()
    assert unfrozen["is_frozen"] is False


def test_utxos_list_filtered_by_holding(app_with_db_and_node) -> None:
    client, _, node = app_with_db_and_node
    purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(gap_limit=5)
    ).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]
    funding = _make_funding_wallet(node)
    txid = node.send_to_address_from_wallet(funding, target, 3_000)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")

    holding_id = purse["id"]
    utxos = client.get(
        f"/api/v1/utxos?holding_id={holding_id}&limit=200"
    ).json()["utxos"]
    matching = [u for u in utxos if u["txid"] == txid]
    assert len(matching) == 1
    assert matching[0]["descriptor_id"] == descriptor_id
    assert matching[0]["value_sats"] == 3_000
