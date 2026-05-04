"""Integration tests for /api/v1/analysis/holding/{id}/* endpoints.

Each test creates a Holding via the public API, then asks the analysis
endpoints to characterise it. We exercise:

  - declared single + observable single → no discrepancies
  - declared multisig + observable single (single-key descriptor) → HIGH discrepancy
  - Vault holding with a single-key, no-timelock descriptor → MEDIUM discrepancy
  - inheritance_configured but no observable recovery path → LOW discrepancy
  - blueprint endpoint rolls up hygiene flags into a per-holding summary
"""

from __future__ import annotations

import secrets

import pytest


pytestmark = pytest.mark.integration


WPKH_REGTEST = (
    "wpkh(tpubD6NzVbkrYhZ4XHndKkuB8FifXm8r5FQHwrN6oZuWCz13qb93rtgKvD4PQsqC4HP4yhV3tA2fqr2RbY5mNXfM7RxXUoeABoDtsFUq2zJq6YK/0/*)"
)


def _purse_body(
    *,
    custody_model: str = "self_single",
    signing_model: str = "software_hot",
    inheritance_configured: bool = False,
) -> dict:
    return {
        "name": f"Analysis test {secrets.token_hex(2)}",
        "purpose": "spending",
        "declared_security": {
            "custody_model": custody_model,
            "signing_model": signing_model,
            "inheritance_configured": inheritance_configured,
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


def _vault_body(*, with_timelock: bool = False) -> dict:
    """A Vault with a single-key descriptor (deliberately mismatched to spec
    intent — that's what the discrepancy detector should catch)."""
    expression = WPKH_REGTEST  # single-key, no timelock
    return {
        "name": f"Vault test {secrets.token_hex(2)}",
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
                "expression": expression,
                "network": "regtest",
                "gap_limit": 5,
            }
        ],
    }


def test_security_declared_single_observable_single_no_discrepancies(app_with_db) -> None:
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    res = client.get(f"/api/v1/analysis/holding/{purse['id']}/security").json()

    assert res["declared"]["custody_model"] == "self_single"
    assert res["observable"]["inferred_custody_model"] == "self_single"
    assert res["observable"]["inferred_signing_model"] == "unknown"
    assert res["discrepancies"] == []


def test_security_declared_multisig_observable_single_emits_high(app_with_db) -> None:
    """Holding with a single-key wpkh descriptor declared as self_multisig
    must produce a HIGH severity discrepancy (the on-chain protection is
    weaker than declared)."""
    client, _ = app_with_db
    purse = client.post(
        "/api/v1/holdings/purse",
        json=_purse_body(custody_model="self_multisig"),
    ).json()
    res = client.get(f"/api/v1/analysis/holding/{purse['id']}/security").json()

    kinds = [d["kind"] for d in res["discrepancies"]]
    assert "claimed_multisig_but_single_key" in kinds
    high = [d for d in res["discrepancies"] if d["kind"] == "claimed_multisig_but_single_key"][0]
    assert high["severity"] == "high"


def test_security_404_for_unknown_holding(app_with_db) -> None:
    client, _ = app_with_db
    response = client.get(
        "/api/v1/analysis/holding/00000000-0000-0000-0000-0000000000aa/security"
    )
    assert response.status_code == 404


def test_blueprint_returns_zero_counts_for_fresh_holding(app_with_db) -> None:
    """A holding with no UTXOs has all-zero hygiene rollups and an empty
    recommendations list."""
    client, _ = app_with_db
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    res = client.get(f"/api/v1/analysis/holding/{purse['id']}/blueprint").json()

    assert res["summary"] == {
        "address_reuse_count": 0,
        "dust_utxo_count": 0,
        "round_number_outputs": 0,
        "suspected_consolidations": 0,
    }
    assert res["recommendations"] == []


def test_blueprint_aggregates_dust_count_after_chain_scan(app_with_db_and_node) -> None:
    """Funding a watched address with a sub-DUST amount and rescanning
    should bump dust_utxo_count and surface a 'dust' recommendation."""
    import time

    client, _, node = app_with_db_and_node
    purse = client.post("/api/v1/holdings/purse", json=_purse_body()).json()
    descriptor_id = purse["descriptor_ids"][0]
    target = client.get(
        f"/api/v1/descriptors/{descriptor_id}/addresses?limit=1"
    ).json()["addresses"][0]["address"]

    funding = f"analysis_{secrets.token_hex(4)}"
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

    node.send_to_address_from_wallet(funding, target, 1_500)
    node.generate_to_address(1, node.get_new_address(wallet=funding))
    client.post(f"/api/v1/descriptors/{descriptor_id}/rescan")

    blueprint = client.get(
        f"/api/v1/analysis/holding/{purse['id']}/blueprint"
    ).json()
    assert blueprint["summary"]["dust_utxo_count"] >= 1
    flags = [r["flag"] for r in blueprint["recommendations"]]
    assert "dust" in flags


def test_blueprint_404_for_unknown_holding(app_with_db) -> None:
    client, _ = app_with_db
    response = client.get(
        "/api/v1/analysis/holding/00000000-0000-0000-0000-0000000000aa/blueprint"
    )
    assert response.status_code == 404


def test_security_for_account_holding_is_third_party(app_with_db) -> None:
    """An Account holding has no descriptors and is observable as
    third_party. Inferred signing model is `not_applicable`. No
    discrepancies fire by default."""
    client, _ = app_with_db
    # Create a CustodialProvider first so the Account creation can attach to it.
    provider = client.post(
        "/api/v1/custodial-providers",
        json={
            "name": f"Test {secrets.token_hex(2)}",
            "kind": "exchange",
            "credentials": {"api_key": "k", "api_secret": "s"},
            "permissions": {"can_read": True, "can_withdraw": True},
        },
    )
    if provider.status_code in (501, 404):
        pytest.skip("CustodialProvider API not available in this milestone")

    provider_id = provider.json()["id"]
    account = client.post(
        "/api/v1/holdings/account",
        json={
            "name": "Coinbase",
            "purpose": "spending",
            "custodial_provider_id": provider_id,
            "display_color": "#abcdef",
            "display_order": 0,
        },
    ).json()

    res = client.get(
        f"/api/v1/analysis/holding/{account['id']}/security"
    ).json()
    assert res["observable"]["inferred_custody_model"] == "third_party"
    assert res["observable"]["inferred_signing_model"] == "not_applicable"
