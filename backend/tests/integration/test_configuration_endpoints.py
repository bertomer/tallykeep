"""Integration tests for /api/v1/configuration."""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.integration


# --- GET ------------------------------------------------------------------------


def test_get_configuration_returns_all_sections_when_empty(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.get("/api/v1/configuration")

    assert response.status_code == 200
    body = response.json()
    expected_sections = {
        "bitcoind",
        "fee_estimation",
        "custodial_polling",
        "analysis",
        "notifications",
    }
    assert set(body.keys()) == expected_sections
    # Every field defaults to None when no override exists.
    for section in expected_sections:
        for value in body[section].values():
            assert value is None


# --- PATCH ----------------------------------------------------------------------


def test_patch_configuration_persists_section(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"bitcoind": {"rpc_host": "192.168.1.42", "rpc_port": 8332}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["bitcoind"]["rpc_host"] == "192.168.1.42"
    assert body["bitcoind"]["rpc_port"] == 8332

    # Persists across reads.
    body = client.get("/api/v1/configuration").json()
    assert body["bitcoind"]["rpc_host"] == "192.168.1.42"


def test_patch_configuration_partial_update_preserves_other_sections(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    client.patch(
        "/api/v1/configuration",
        json={"bitcoind": {"rpc_host": "host1", "rpc_port": 8332}},
    )
    client.patch(
        "/api/v1/configuration",
        json={"fee_estimation": {"strategy": "priority"}},
    )

    body = client.get("/api/v1/configuration").json()
    assert body["bitcoind"]["rpc_host"] == "host1"
    assert body["bitcoind"]["rpc_port"] == 8332
    assert body["fee_estimation"]["strategy"] == "priority"


def test_patch_configuration_rejects_unknown_section(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"surely_not_real_section": {"foo": "bar"}},
    )
    assert response.status_code == 422


def test_patch_configuration_rejects_unknown_field_in_section(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"bitcoind": {"not_a_real_field": "x"}},
    )
    assert response.status_code == 422


def test_patch_configuration_rejects_out_of_range_port(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"bitcoind": {"rpc_port": 99999}},
    )
    assert response.status_code == 422


def test_patch_configuration_rejects_too_short_polling_interval(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"custodial_polling": {"interval_seconds": 5}},  # min is 60
    )
    assert response.status_code == 422


def test_patch_configuration_keeps_lock_middleware_passing(
    app_with_db,  # type: ignore[no-untyped-def]
) -> None:
    """Sanity: the configuration endpoint is gated by the lock middleware just
    like every other endpoint. The fixture pre-installs an unlocked InMemory
    secret store, so PATCH must succeed (200), not 423."""
    client, _ = app_with_db
    response = client.patch(
        "/api/v1/configuration",
        json={"notifications": {"enabled": True}},
    )
    assert response.status_code == 200
    assert response.json()["notifications"]["enabled"] is True
