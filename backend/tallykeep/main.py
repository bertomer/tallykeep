"""FastAPI entry point.

Wires the API and lifecycle hooks. The worker has its own entry point at
`tallykeep.worker`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from tallykeep import __version__
from tallykeep.api.lock_middleware import LockMiddleware
from tallykeep.api.v1 import health, unlock
from tallykeep.configuration import get_settings
from tallykeep.infrastructure.database import get_session_factory
from tallykeep.infrastructure.secrets import (
    EncryptedDatabaseSecretStore,
    SecretStore,
)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Wire long-lived state on startup, tear it down on shutdown.

    Tests can override `app.state.secret_store` *after* the app is created and
    before the first request — the override survives because we only seed the
    default store here when nothing has been set.
    """
    if not hasattr(app.state, "secret_store"):
        settings = get_settings()
        if settings.database_url:
            store: SecretStore = EncryptedDatabaseSecretStore(get_session_factory())
        else:
            # No database configured — defer creation until tests inject a store.
            # The lock middleware will return 423 for any non-allowlisted request.
            store = None  # type: ignore[assignment]
        app.state.secret_store = store

    yield

    # Discard in-memory key on shutdown so a fast restart doesn't leak it via
    # core dumps or similar.
    store = getattr(app.state, "secret_store", None)
    if store is not None:
        try:
            store.lock()
        except Exception:  # pragma: no cover — best-effort cleanup
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title="TallyKeep",
        version=__version__,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )

    # 423-Locked middleware sits in front of every router so unlock state is
    # enforced uniformly.
    app.add_middleware(LockMiddleware)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(unlock.router, prefix="/api/v1")

    return app


app = create_app()
