"""Integration tests for the M5.7 summary endpoints.

  - GET /api/v1/holdings/{id}/summary
  - GET /api/v1/holdings/summary/global

Both rely on chain-state aggregation (UTXO sums per descriptor). For the
balance-rollup tests we use the live `app_with_db_and_node` fixture so
funded addresses produce real persistent UTXO rows; the structural
tests (404, empty stack, multiple holdings sum) use the cheaper
`app_with_db` fixture and skip the funded-balance path.
"""

from __future__ import annotations

import secrets
from uuid import uuid4

import pytest


pytestmark = pytest.mark.integration


_BRANCH_INDEX = {"next": 100}
_BASE_XPUB = (
    "tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK"
)


def _next_descriptor() -> str:
    idx = _BRANCH_INDEX["next"]
    _BRANCH_INDEX["next"] += 1
    return f"wpkh({_BASE_XPUB}/{idx}/*)"


def _purse_body(*, expression: str | None = None, purpose: str = "spending") -> dict:
    return {
        "name": f"Summary test {secrets.token_hex(2)}",
        "purpose": purpose,
        "declared_security": {
            "custody_model": "self_single",
            "signing_model": "software_hot",
        },
        "display_color": "#10b981",
        "display_order": 0,
        "descriptors": [
            {
                "name": "main",
                "expression": expression or _next_descriptor(),
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def test_holding_summary_404_for_unknown_id(app_with_db) -> None:
    client, _ = app_with_db
    response = client.get(f"/api/v1/holdings/{uuid4()}/summary")
    assert response.status_code == 404


def test_holding_summary_zero_balance_when_no_utxos(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    res = client.get(f"/api/v1/holdings/{purse['id']}/summary").json()

    assert res["holding"]["id"] == purse["id"]
    assert res["confirmed_sats"] == 0
    assert res["unconfirmed_sats"] == 0
    assert res["descriptor_count"] == 1
    assert res["utxo_count"] == 0
    assert res["observable_security"]["inferred_custody_model"] == "self_single"


def test_global_summary_empty_when_no_holdings(app_with_db) -> None:
    client, _ = app_with_db
    res = client.get("/api/v1/holdings/summary/global").json()
    assert res["total_sats"] == 0
    assert res["holdings"] == []
    assert res["by_type"] == {}
    assert res["by_purpose"] == {}


def test_global_summary_aggregates_per_type_and_purpose(app_with_db) -> None:
    client, _ = app_with_db
    spending_purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(purpose="spending")
    ).json()
    reserve_purse = client.post(
        "/api/v1/holdings/purse", json=_purse_body(purpose="reserve")
    ).json()
    res = client.get("/api/v1/holdings/summary/global").json()

    ids = {h["holding_id"] for h in res["holdings"]}
    assert spending_purse["id"] in ids
    assert reserve_purse["id"] in ids
    # Both balances are zero before funding, so by_purpose still has the keys
    # but with value 0.
    assert "spending" in res["by_purpose"]
    assert "reserve" in res["by_purpose"]
    assert res["by_purpose"]["spending"] == 0
    assert res["by_purpose"]["reserve"] == 0


def test_global_summary_excludes_archived_by_default(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    client.post(f"/api/v1/holdings/{purse['id']}/archive")

    default = client.get("/api/v1/holdings/summary/global").json()
    assert all(h["holding_id"] != purse["id"] for h in default["holdings"])

    full = client.get(
        "/api/v1/holdings/summary/global?include_archived=true"
    ).json()
    assert any(h["holding_id"] == purse["id"] for h in full["holdings"])


def test_holding_summary_includes_funded_balance(app_with_db_and_node) -> None:
    """Fund a watched address, /rescan, and assert the summary endpoint
    reflects both the confirmed_sats and the utxo_count."""
    import time

    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding = f"summary_{secrets.token_hex(4)}"
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

    node.send_to_address_from_wallet(funding, target, 5_000)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")

    res = client.get(f"/api/v1/holdings/{purse['id']}/summary").json()
    assert res["confirmed_sats"] >= 5_000
    assert res["utxo_count"] >= 1


def test_holding_summary_surfaces_discrepancy(app_with_db) -> None:
    """A Holding declared self_multisig with a single-key descriptor
    surfaces the high-severity discrepancy directly on the /summary
    response (no separate /security call needed)."""
    client, _ = app_with_db
    body = _purse_body()
    body["declared_security"]["custody_model"] = "self_multisig"
    purse = client.post("/api/v1/holdings/purse", json=body).json()

    res = client.get(f"/api/v1/holdings/{purse['id']}/summary").json()
    kinds = [d["kind"] for d in res["discrepancies"]]
    assert "claimed_multisig_but_single_key" in kinds
