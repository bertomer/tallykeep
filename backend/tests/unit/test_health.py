"""Smoke tests for /api/v1/health.

This is the first non-regression test for the project. Every milestone adds tests here
or in sibling files; this one must remain green forever (the contract is locked by
spec module 04).
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_health_returns_200(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_payload_shape(client) -> None:
    """The shape is part of the API contract per spec module 04.

    The set of subsystem keys is locked: database, bitcoind, redis, event_bus, unlocked.
    Subsystem values may evolve as milestones land, but the keys do not change.
    """
    response = client.get("/api/v1/health")
    body = response.json()

    assert set(body.keys()) == {"status", "version", "checks"}
    assert body["status"] in {"ok", "degraded"}
    assert isinstance(body["version"], str) and body["version"]

    expected_subsystems = {"database", "bitcoind", "redis", "event_bus", "unlocked"}
    assert set(body["checks"].keys()) == expected_subsystems

    for name, check in body["checks"].items():
        assert isinstance(check, dict), f"check {name!r} must be a dict"
        assert "ok" in check, f"check {name!r} missing 'ok' field"
        assert isinstance(check["ok"], bool)


def test_health_status_is_degraded_when_any_check_fails(client) -> None:
    """In M0 every subsystem is `not_yet_implemented`, so overall must be degraded.

    Once subsystems are wired, this test relaxes — but the rule "any failed check ⇒
    degraded overall" stays. Update the assertion in lockstep with the wiring milestone.
    """
    body = client.get("/api/v1/health").json()
    any_failed = any(not check["ok"] for check in body["checks"].values())
    if any_failed:
        assert body["status"] == "degraded"
    else:
        assert body["status"] == "ok"


def test_openapi_endpoint_serves_spec(client) -> None:
    """OpenAPI spec must be available so the frontend can generate its typed client."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    assert "/api/v1/health" in spec["paths"]
