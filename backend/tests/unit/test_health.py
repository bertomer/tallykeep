"""Smoke tests for /api/v1/health.

This is the first non-regression test for the project. Every milestone adds tests
here or in sibling files; the response shape is part of the API contract and must
remain green forever (spec module 04).

Subsystem-value semantics evolve as milestones wire each probe — see
`test_unlock_endpoints.py` for the unlock-probe assertions and the integration
suite for database-probe assertions.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


def test_health_returns_200(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_payload_shape(client) -> None:
    """The shape is part of the API contract per spec module 04.

    The set of subsystem keys is locked: database, bitcoind, redis, event_bus,
    unlocked. Subsystem values may evolve as milestones land, but the keys do not
    change.
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


def test_health_overall_consistent_with_checks(client) -> None:
    """Any failed check ⇒ overall status `degraded`. Otherwise `ok`."""
    body = client.get("/api/v1/health").json()
    any_failed = any(not check["ok"] for check in body["checks"].values())
    if any_failed:
        assert body["status"] == "degraded"
    else:
        assert body["status"] == "ok"


def test_health_unimplemented_probes_have_a_reason(client) -> None:
    """Probes still pending later milestones must surface their state explicitly.

    Currently bitcoind / redis / event_bus return `not_yet_implemented`. The check
    will relax as each probe lands; the *requirement* is that no probe silently
    returns `ok=False` with no diagnostic information.
    """
    body = client.get("/api/v1/health").json()
    for name, check in body["checks"].items():
        if not check["ok"]:
            assert check.get("reason"), (
                f"check {name!r} reports ok=False but has no reason"
            )


def test_openapi_endpoint_serves_spec(client) -> None:
    """OpenAPI spec must be available so the frontend can generate its typed client."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["openapi"].startswith("3.")
    assert "/api/v1/health" in spec["paths"]
