"""FastAPI entry point.

Wires the API and lifecycle hooks. The worker has its own entry point at
`tallykeep.worker`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

import logging

from tallykeep import __version__
from tallykeep.api.lock_middleware import LockMiddleware
from tallykeep.api.v1 import (
    addresses as addresses_routes,
    analysis as analysis_routes,
    banking as banking_routes,
    configuration as configuration_routes,
    custodial_providers as custodial_providers_routes,
    descriptors as descriptors_routes,
    events_stream as events_stream_routes,
    export as export_routes,
    feature_flags as feature_flags_routes,
    health,
    holdings as holdings_routes,
    jobs as jobs_routes,
    ledger_entries as ledger_entries_routes,
    lightning as lightning_routes,
    profile as profile_routes,
    trading as trading_routes,
    unlock,
    utxos as utxos_routes,
)
from tallykeep.configuration import get_settings
from tallykeep.infrastructure.database import get_session_factory
from tallykeep.infrastructure.event_bus import EventBus, RedisEventBus
from tallykeep.infrastructure.secrets import (
    EncryptedDatabaseSecretStore,
    SecretStore,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Wire long-lived state on startup, tear it down on shutdown.

    Tests can override `app.state.secret_store` and `app.state.event_bus` *after*
    the app is created and before the first request — the override survives
    because we only seed defaults here when nothing has been set.
    """
    settings = get_settings()

    if not hasattr(app.state, "session_factory"):
        app.state.session_factory = (
            get_session_factory() if settings.database_url else None
        )

    if not hasattr(app.state, "secret_store"):
        if settings.database_url:
            store: SecretStore = EncryptedDatabaseSecretStore(get_session_factory())
        else:
            # No database configured — defer creation until tests inject a store.
            # The lock middleware will return 423 for any non-allowlisted request.
            store = None  # type: ignore[assignment]
        app.state.secret_store = store

    if not hasattr(app.state, "event_bus"):
        if settings.redis_url:
            try:
                bus: EventBus | None = RedisEventBus(settings.redis_url)
            except Exception:  # noqa: BLE001 — Redis can be unreachable at boot
                logger.exception(
                    "RedisEventBus failed to start; /health will report degraded"
                )
                bus = None
        else:
            bus = None
        app.state.event_bus = bus

    if not hasattr(app.state, "node_adapter"):
        if settings.bitcoind_rpc_url:
            from tallykeep.adapters.node_adapter import NodeAdapter

            # Long-lived adapter — owns an httpx connection pool that gets
            # reused across requests. Closed in the shutdown path below.
            app.state.node_adapter = NodeAdapter(
                settings.bitcoind_rpc_url, timeout_seconds=30.0
            )
        else:
            app.state.node_adapter = None

    yield

    # Discard in-memory key on shutdown so a fast restart doesn't leak it via
    # core dumps or similar.
    store = getattr(app.state, "secret_store", None)
    if store is not None:
        try:
            store.lock()
        except Exception:  # pragma: no cover — best-effort cleanup
            pass

    bus = getattr(app.state, "event_bus", None)
    if bus is not None:
        try:
            bus.close()
        except Exception:  # pragma: no cover — best-effort cleanup
            pass

    node = getattr(app.state, "node_adapter", None)
    if node is not None:
        try:
            node.close()
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

    # Implemented in M0–M3.1
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(unlock.router, prefix="/api/v1")
    app.include_router(profile_routes.router, prefix="/api/v1")
    app.include_router(feature_flags_routes.router, prefix="/api/v1")
    app.include_router(configuration_routes.router, prefix="/api/v1")

    # M3.2 — every other spec-module-04 route registered as a 501 stub. The
    # OpenAPI spec covers the full surface so the frontend can generate its
    # typed client today; each stub raises with a milestone-tagged Problem
    # Details body so the user knows when to expect the real handler.
    app.include_router(holdings_routes.router, prefix="/api/v1")
    app.include_router(descriptors_routes.router, prefix="/api/v1")
    app.include_router(custodial_providers_routes.router, prefix="/api/v1")
    app.include_router(addresses_routes.router, prefix="/api/v1")
    app.include_router(utxos_routes.router, prefix="/api/v1")
    app.include_router(ledger_entries_routes.router, prefix="/api/v1")
    app.include_router(banking_routes.router, prefix="/api/v1")
    app.include_router(trading_routes.router, prefix="/api/v1")
    app.include_router(analysis_routes.router, prefix="/api/v1")
    app.include_router(jobs_routes.router, prefix="/api/v1")
    app.include_router(export_routes.router, prefix="/api/v1")
    app.include_router(lightning_routes.router, prefix="/api/v1")

    # SSE event stream — implemented as a working scaffold in M3.3, refined in
    # M9 with the full LiveUpdateBridge.
    app.include_router(events_stream_routes.router, prefix="/api/v1")

    return app


app = create_app()
