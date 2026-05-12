"""Unit tests for pairing endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_issue_returns_token(client: TestClient) -> None:
    resp = client.post("/api/v1/pairing/issue")
    assert resp.status_code == 200
    data = resp.json()
    assert "pairing_token" in data
    assert len(data["pairing_token"]) > 10
    assert "expires_at" in data


@pytest.mark.unit
def test_issue_tokens_are_unique(client: TestClient) -> None:
    t1 = client.post("/api/v1/pairing/issue").json()["pairing_token"]
    t2 = client.post("/api/v1/pairing/issue").json()["pairing_token"]
    assert t1 != t2


@pytest.mark.integration
def test_redeem_invalid_token_returns_401(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db
    resp = client.post("/api/v1/pairing/redeem", json={"pairing_token": "notavalidtoken"})
    assert resp.status_code == 401


@pytest.mark.integration
def test_redeem_empty_token_returns_422(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db
    resp = client.post("/api/v1/pairing/redeem", json={"pairing_token": ""})
    assert resp.status_code == 422


@pytest.mark.integration
def test_redeem_valid_token_returns_credential(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db

    issue_resp = client.post("/api/v1/pairing/issue")
    assert issue_resp.status_code == 200
    token = issue_resp.json()["pairing_token"]

    redeem_resp = client.post(
        "/api/v1/pairing/redeem",
        json={"pairing_token": token, "device_label": "test phone"},
    )
    assert redeem_resp.status_code == 200
    data = redeem_resp.json()
    assert "device_id" in data
    assert "device_credential" in data
    assert len(data["device_credential"]) > 10


@pytest.mark.integration
def test_redeem_same_token_twice_returns_401_second_time(app_with_db: tuple) -> None:  # type: ignore[type-arg]
    client, _ = app_with_db

    token = client.post("/api/v1/pairing/issue").json()["pairing_token"]
    first = client.post("/api/v1/pairing/redeem", json={"pairing_token": token})
    assert first.status_code == 200

    second = client.post("/api/v1/pairing/redeem", json={"pairing_token": token})
    assert second.status_code == 401


@pytest.mark.unit
def test_pairing_accessible_while_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pairing issue must work regardless of secret-store lock state."""
    from tallykeep.infrastructure.secrets import InMemorySecretStore
    from tallykeep.main import create_app
    from tallykeep.configuration import get_settings

    monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
    get_settings.cache_clear()
    try:
        store = InMemorySecretStore()
        app = create_app()
        app.state.secret_store = store
        with TestClient(app) as c:
            resp = c.post("/api/v1/pairing/issue")
        assert resp.status_code == 200
    finally:
        get_settings.cache_clear()
