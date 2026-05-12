"""Unit tests for AuthMiddleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tallykeep.infrastructure.secrets import InMemorySecretStore
from tallykeep.main import create_app


def _authed_client() -> TestClient:
    """App client with auth_disabled=False (auth enforced)."""
    store = InMemorySecretStore()
    store.initialize("test passphrase")
    app = create_app()
    app.state.secret_store = store
    # auth_disabled NOT set — credentials required
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.unit
def test_exempt_paths_pass_without_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
    from tallykeep.configuration import get_settings
    get_settings.cache_clear()
    try:
        c = _authed_client()
        with c:
            assert c.get("/api/v1/health").status_code != 401
            assert c.get("/api/v1/server/info").status_code != 401
            assert c.post("/api/v1/pairing/issue").status_code != 401
    finally:
        get_settings.cache_clear()


@pytest.mark.unit
def test_protected_path_without_credential_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
    from tallykeep.configuration import get_settings
    get_settings.cache_clear()
    try:
        c = _authed_client()
        with c:
            resp = c.get("/api/v1/holdings")
            assert resp.status_code == 401
    finally:
        get_settings.cache_clear()


@pytest.mark.unit
def test_protected_path_with_malformed_header_returns_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TALLYKEEP_DATABASE_URL", "")
    from tallykeep.configuration import get_settings
    get_settings.cache_clear()
    try:
        c = _authed_client()
        with c:
            resp = c.get("/api/v1/holdings", headers={"Authorization": "Basic abc123"})
            assert resp.status_code == 401
    finally:
        get_settings.cache_clear()
