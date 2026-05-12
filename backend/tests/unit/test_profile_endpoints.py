"""Integration tests for profile endpoints — principles_acknowledged_at field."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_profile_principles_acknowledged_at_is_null_by_default(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db
    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    assert resp.json()["principles_acknowledged_at"] is None


@pytest.mark.integration
def test_profile_patch_principles_acknowledged_sets_timestamp(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db
    resp = client.patch("/api/v1/profile", json={"principles_acknowledged": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["principles_acknowledged_at"] is not None


@pytest.mark.integration
def test_profile_patch_principles_acknowledged_idempotent(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    """Second acknowledgment must not overwrite the original timestamp."""
    client, _ = app_with_db

    r1 = client.patch("/api/v1/profile", json={"principles_acknowledged": True})
    assert r1.status_code == 200
    ts1 = r1.json()["principles_acknowledged_at"]
    assert ts1 is not None

    r2 = client.patch("/api/v1/profile", json={"principles_acknowledged": True})
    assert r2.status_code == 200
    ts2 = r2.json()["principles_acknowledged_at"]

    assert ts1 == ts2


@pytest.mark.integration
def test_profile_get_reflects_acknowledged_after_patch(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db

    client.patch("/api/v1/profile", json={"principles_acknowledged": True})

    resp = client.get("/api/v1/profile")
    assert resp.status_code == 200
    assert resp.json()["principles_acknowledged_at"] is not None


@pytest.mark.integration
def test_profile_patch_empty_body_returns_422(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db
    resp = client.patch("/api/v1/profile", json={})
    assert resp.status_code == 422
