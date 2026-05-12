"""Unit tests for GET /api/v1/server/info."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_server_info_default_empty_label(client: TestClient) -> None:
    resp = client.get("/api/v1/server/info")
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_label"] == ""


@pytest.mark.unit
def test_server_info_custom_label(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tallykeep.configuration import get_settings

    monkeypatch.setenv("TALLYKEEP_SERVER_LABEL", "Home Lab")
    get_settings.cache_clear()
    try:
        resp = client.get("/api/v1/server/info")
        assert resp.status_code == 200
        assert resp.json()["server_label"] == "Home Lab"
    finally:
        get_settings.cache_clear()


@pytest.mark.unit
def test_server_info_accessible_while_locked(monkeypatch: pytest.MonkeyPatch) -> None:
    """server/info must work regardless of secret-store lock state."""
    from tallykeep.infrastructure.secrets import InMemorySecretStore
    from tallykeep.main import create_app

    monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
    from tallykeep.configuration import get_settings

    get_settings.cache_clear()
    try:
        store = InMemorySecretStore()
        # intentionally NOT initialized or unlocked
        app = create_app()
        app.state.secret_store = store
        with TestClient(app) as c:
            resp = c.get("/api/v1/server/info")
        assert resp.status_code == 200
    finally:
        get_settings.cache_clear()
