"""Integration tests for sweep-policy and sweep-execution endpoints (M8).

These tests exercise the full HTTP → service → repository → DB round-trip.
Account-holding creation (which requires live exchange credentials) is NOT
tested here; those happy-path flows belong to end-to-end tests once a mock
exchange adapter is provided.
"""

from __future__ import annotations

from uuid import uuid4

import pytest


pytestmark = pytest.mark.integration


# Two different mainnet descriptors so no unique-expression constraint fires.
_WPKH_A = "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/0/*)"
_WPKH_B = "wpkh(xpub6BosfCnifzxcFwrSzQiqu2DBVTshkCXacvNsWGYJVVhhawA7d4R5WSWGFNbi8Aw6ZRc1brxMyWMzG3DSSSSoekkudhUd9yLb6qx39T9nMdj/1/*)"

_SEC = {
    "custody_model": "self_single",
    "signing_model": "hardware_offline",
    "geographic_distribution": False,
    "inheritance_configured": False,
}


def _create_purse(client, expression: str, name: str = "Purse") -> str:
    resp = client.post(
        "/api/v1/holdings/purse",
        json={
            "name": name,
            "purpose": "reserve",
            "purse_mode": "watch_only",
            "declared_security": _SEC,
            "display_color": "#000000",
            "display_order": 0,
            "descriptors": [
                {"name": "main", "expression": expression, "network": "mainnet", "gap_limit": 5}
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _policy_body(source_id: str, destination_id: str, **overrides) -> dict:  # type: ignore[no-untyped-def]
    body = {
        "name": "Test sweep",
        "source_holding_id": source_id,
        "destination_holding_id": destination_id,
        "trigger_type": "threshold",
        "trigger_configuration": {"threshold_sats": 500_000, "cooldown_hours": 24},
        "minimum_balance_sats": 100_000,
        "maximum_per_period_sats": 1_000_000,
        "requires_user_confirmation": True,
        "is_dry_run": False,
    }
    body.update(overrides)
    return body


# --- Sweep policies --------------------------------------------------------


def test_create_and_get_sweep_policy(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "Source")
    dst_id = _create_purse(client, _WPKH_B, "Destination")

    resp = client.post("/api/v1/sweep-policies", json=_policy_body(src_id, dst_id))
    assert resp.status_code == 201, resp.text
    policy = resp.json()
    policy_id = policy["id"]

    assert policy["name"] == "Test sweep"
    assert policy["source_holding_id"] == src_id
    assert policy["destination_holding_id"] == dst_id
    assert policy["is_enabled"] is False
    assert policy["trigger_type"] == "threshold"
    assert policy["is_dry_run"] is False
    assert isinstance(policy["safety_warnings"], list)

    get_resp = client.get(f"/api/v1/sweep-policies/{policy_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == policy_id


def test_list_sweep_policies(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "Source2")
    dst_id = _create_purse(client, _WPKH_B, "Destination2")

    client.post("/api/v1/sweep-policies", json=_policy_body(src_id, dst_id, name="P1"))
    client.post("/api/v1/sweep-policies", json=_policy_body(src_id, dst_id, name="P2"))

    all_resp = client.get("/api/v1/sweep-policies")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) >= 2

    filtered = client.get(f"/api/v1/sweep-policies?source_holding_id={src_id}")
    assert filtered.status_code == 200
    names = {p["name"] for p in filtered.json()}
    assert "P1" in names and "P2" in names


def test_patch_sweep_policy(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcPatch")
    dst_id = _create_purse(client, _WPKH_B, "DstPatch")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]

    patch_resp = client.patch(
        f"/api/v1/sweep-policies/{policy_id}",
        json={"name": "Updated name", "maximum_per_period_sats": 2_000_000},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated name"
    assert patch_resp.json()["maximum_per_period_sats"] == 2_000_000


def test_enable_requires_acknowledged_warnings(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcEnable")
    dst_id = _create_purse(client, _WPKH_B, "DstEnable")

    # Both are Purses → DESTINATION_KEYS_ON_HOST warning fires.
    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]

    # Attempt to enable — should fail with 409 (unacknowledged warnings).
    enable_resp = client.post(f"/api/v1/sweep-policies/{policy_id}/enable")
    assert enable_resp.status_code == 409

    # Acknowledge warnings.
    ack_resp = client.post(f"/api/v1/sweep-policies/{policy_id}/acknowledge-warnings")
    assert ack_resp.status_code == 200
    assert all(w["user_acknowledged"] for w in ack_resp.json()["safety_warnings"])

    # Now enable succeeds.
    enable_resp2 = client.post(f"/api/v1/sweep-policies/{policy_id}/enable")
    assert enable_resp2.status_code == 200
    assert enable_resp2.json()["is_enabled"] is True


def test_disable_sweep_policy(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcDisable")
    dst_id = _create_purse(client, _WPKH_B, "DstDisable")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]
    client.post(f"/api/v1/sweep-policies/{policy_id}/acknowledge-warnings")
    client.post(f"/api/v1/sweep-policies/{policy_id}/enable")

    disable_resp = client.post(f"/api/v1/sweep-policies/{policy_id}/disable")
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_enabled"] is False


def test_delete_sweep_policy(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcDel")
    dst_id = _create_purse(client, _WPKH_B, "DstDel")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]

    del_resp = client.delete(f"/api/v1/sweep-policies/{policy_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/sweep-policies/{policy_id}")
    assert get_resp.status_code == 404


def test_delete_enabled_policy_fails(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcDelEnabled")
    dst_id = _create_purse(client, _WPKH_B, "DstDelEnabled")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]
    client.post(f"/api/v1/sweep-policies/{policy_id}/acknowledge-warnings")
    client.post(f"/api/v1/sweep-policies/{policy_id}/enable")

    del_resp = client.delete(f"/api/v1/sweep-policies/{policy_id}")
    assert del_resp.status_code == 422


def test_pause_and_resume_all(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcPause")
    dst_id = _create_purse(client, _WPKH_B, "DstPause")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]
    client.post(f"/api/v1/sweep-policies/{policy_id}/acknowledge-warnings")
    client.post(f"/api/v1/sweep-policies/{policy_id}/enable")

    pause_resp = client.post("/api/v1/sweep-policies/pause-all")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["paused"] >= 1

    resume_resp = client.post("/api/v1/sweep-policies/resume-all")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["resumed"] >= 1


def test_create_policy_same_source_and_destination_fails(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcSame")

    resp = client.post(
        "/api/v1/sweep-policies",
        json=_policy_body(src_id, src_id),
    )
    assert resp.status_code == 422


def test_create_policy_unknown_source_fails(app_with_db) -> None:
    client, _ = app_with_db
    dst_id = _create_purse(client, _WPKH_B, "DstUnknown")

    resp = client.post(
        "/api/v1/sweep-policies",
        json=_policy_body(str(uuid4()), dst_id),
    )
    assert resp.status_code == 422


# --- Sweep executions ----------------------------------------------------------


def test_list_sweep_executions_empty(app_with_db) -> None:
    client, _ = app_with_db
    resp = client.get("/api/v1/sweep-executions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_unknown_execution_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    resp = client.get(f"/api/v1/sweep-executions/{uuid4()}")
    assert resp.status_code == 404


def test_list_policy_executions(app_with_db) -> None:
    client, _ = app_with_db
    src_id = _create_purse(client, _WPKH_A, "SrcExec")
    dst_id = _create_purse(client, _WPKH_B, "DstExec")

    policy_id = client.post(
        "/api/v1/sweep-policies", json=_policy_body(src_id, dst_id)
    ).json()["id"]

    resp = client.get(f"/api/v1/sweep-policies/{policy_id}/executions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- Custodial providers: supported adapters ----------------------------------


def test_supported_adapters_returns_list(app_with_db) -> None:
    client, _ = app_with_db
    resp = client.get("/api/v1/custodial-providers/supported")
    assert resp.status_code == 200
    body = resp.json()
    assert "supported" in body
    assert isinstance(body["supported"], list)
    assert len(body["supported"]) > 0


def test_get_unknown_provider_returns_404(app_with_db) -> None:
    client, _ = app_with_db
    resp = client.get(f"/api/v1/custodial-providers/{uuid4()}")
    assert resp.status_code == 404
