"""Unlock-endpoint tests + 423 lock-middleware tests.

Uses the in-memory SecretStore (with cheap KDF parameters) so the suite stays fast
and database-free. Postgres-backed coverage is in the integration suite.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tallykeep.infrastructure.secrets import InMemorySecretStore
from tallykeep.main import create_app


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _cheap_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1)
    monkeypatch.setattr("tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1)


@pytest.fixture()
def store() -> InMemorySecretStore:
    return InMemorySecretStore()


@pytest.fixture()
def client_with_store(store: InMemorySecretStore) -> Iterator[TestClient]:
    """A fresh app with the given store pre-installed.

    Per `_lifespan` in main.py, when `app.state.secret_store` is already set the
    startup hook leaves it alone — that is the test injection seam.
    """
    app = create_app()
    app.state.secret_store = store
    with TestClient(app) as c:
        yield c


# --- /unlock/initialize -----------------------------------------------------------


class TestInitialize:
    def test_first_initialize_returns_200_and_unlocks(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        response = client_with_store.post(
            "/api/v1/unlock/initialize", json={"passphrase": "strong passphrase"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body == {"initialized": True, "unlocked": True}
        assert store.is_initialized()
        assert store.is_unlocked()

    def test_second_initialize_returns_409(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("first")
        response = client_with_store.post(
            "/api/v1/unlock/initialize", json={"passphrase": "again"}
        )
        assert response.status_code == 409

    def test_empty_passphrase_rejected_by_validation(
        self, client_with_store: TestClient
    ) -> None:
        response = client_with_store.post(
            "/api/v1/unlock/initialize", json={"passphrase": ""}
        )
        assert response.status_code == 422


# --- /unlock ----------------------------------------------------------------------


class TestUnlock:
    def test_unlock_with_correct_passphrase_returns_200(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("right")
        store.lock()
        response = client_with_store.post(
            "/api/v1/unlock", json={"passphrase": "right"}
        )
        assert response.status_code == 200
        assert response.json() == {"unlocked": True}
        assert store.is_unlocked()

    def test_unlock_with_wrong_passphrase_returns_401(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("right")
        store.lock()
        response = client_with_store.post(
            "/api/v1/unlock", json={"passphrase": "wrong"}
        )
        assert response.status_code == 401
        assert not store.is_unlocked()

    def test_unlock_before_initialize_returns_503(
        self, client_with_store: TestClient
    ) -> None:
        response = client_with_store.post(
            "/api/v1/unlock", json={"passphrase": "anything"}
        )
        assert response.status_code == 503


# --- 423 Locked middleware --------------------------------------------------------


class TestLockMiddleware:
    """Spec module 04: when the store is locked, every endpoint except /unlock and
    /health (and the OpenAPI spec) returns 423."""

    def test_health_works_when_locked(self, client_with_store: TestClient) -> None:
        response = client_with_store.get("/api/v1/health")
        assert response.status_code == 200

    def test_openapi_works_when_locked(self, client_with_store: TestClient) -> None:
        response = client_with_store.get("/openapi.json")
        assert response.status_code == 200

    def test_unlock_endpoints_work_when_locked(
        self, client_with_store: TestClient
    ) -> None:
        # /unlock without a prior initialize is a 503, not a 423 — proves the
        # middleware lets the request reach the route.
        response = client_with_store.post(
            "/api/v1/unlock", json={"passphrase": "x"}
        )
        assert response.status_code == 503

    def test_unknown_path_returns_423_when_locked(
        self, client_with_store: TestClient
    ) -> None:
        response = client_with_store.get("/api/v1/holdings")
        assert response.status_code == 423
        body = response.json()
        assert body["status"] == 423
        assert body["title"] == "Locked"

    def test_unlocked_app_does_not_423(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("p")
        # POST /api/v1/holdings/account is an M8 stub that does not touch the
        # database — perfect probe here, since this fixture has no DB wired.
        # Any non-423 response proves the lock middleware passed the request
        # through to the handler.
        response = client_with_store.post(
            "/api/v1/holdings/account", json={}
        )
        assert response.status_code != 423

    def test_no_store_configured_returns_423(self) -> None:
        """When app.state.secret_store is None, the middleware must still 423."""
        app = create_app()
        app.state.secret_store = None
        with TestClient(app) as c:
            response = c.get("/api/v1/holdings")
            assert response.status_code == 423


# --- /health probe wiring --------------------------------------------------------


class TestHealthUnlockProbe:
    def test_unlocked_probe_reflects_store_state_locked(
        self, client_with_store: TestClient
    ) -> None:
        body = client_with_store.get("/api/v1/health").json()
        unlocked = body["checks"]["unlocked"]
        assert unlocked["ok"] is False
        assert unlocked["reason"] == "not_initialized"

    def test_unlocked_probe_after_initialize(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("p")
        body = client_with_store.get("/api/v1/health").json()
        unlocked = body["checks"]["unlocked"]
        assert unlocked["ok"] is True

    def test_unlocked_probe_after_explicit_lock(
        self, client_with_store: TestClient, store: InMemorySecretStore
    ) -> None:
        store.initialize("p")
        store.lock()
        body = client_with_store.get("/api/v1/health").json()
        unlocked = body["checks"]["unlocked"]
        assert unlocked["ok"] is False
        assert unlocked["reason"] == "locked"
