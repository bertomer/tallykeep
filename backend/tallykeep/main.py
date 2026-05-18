"""FastAPI entry point.

Wires the API and lifecycle hooks. The worker has its own entry point at
`tallykeep.worker`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

import logging

from tallykeep import __version__
from tallykeep.api.auth_middleware import AuthMiddleware
from tallykeep.api.lock_middleware import LockMiddleware
from tallykeep.api.v1 import (
    addresses as addresses_routes,
    analysis as analysis_routes,
    auth as auth_routes,
    banking as banking_routes,
    configuration as configuration_routes,
    custodial_providers as custodial_providers_routes,
    descriptors as descriptors_routes,
    events_stream as events_stream_routes,
    export as export_routes,
    feature_flags as feature_flags_routes,
    health,
    holdings as holdings_routes,
    internal_custodial as internal_custodial_routes,
    jobs as jobs_routes,
    ledger_entries as ledger_entries_routes,
    lightning as lightning_routes,
    pairing as pairing_routes,
    profile as profile_routes,
    server_info as server_info_routes,
    treasury as treasury_routes,
    unlock,
    utxos as utxos_routes,
)
from tallykeep.configuration import get_settings
from tallykeep.infrastructure.database import get_session_factory
from tallykeep.infrastructure.event_bus import EventBus, RedisEventBus
from tallykeep.infrastructure.job_queue import InMemoryJobQueue, JobQueue, RedisQueueJobQueue
from tallykeep.infrastructure.secrets import (
    EncryptedDatabaseSecretStore,
    SecretStore,
)


# Wire application logger early so tallykeep.* INFO output reaches stdout
# regardless of which log handler uvicorn or the test runner installs.
_app_log = logging.getLogger("tallykeep")
if not _app_log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s] %(message)s"))
    _h.setLevel(logging.INFO)
    _app_log.setLevel(logging.INFO)
    _app_log.addHandler(_h)
    _app_log.propagate = False

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Wire long-lived state on startup, tear it down on shutdown.

    Tests can override `app.state.secret_store` and `app.state.event_bus` *after*
    the app is created and before the first request — the override survives
    because we only seed defaults here when nothing has been set.
    """
    from datetime import UTC, datetime

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

    if not hasattr(app.state, "job_queue"):
        if settings.redis_url:
            try:
                job_queue: JobQueue = RedisQueueJobQueue(settings.redis_url)
            except Exception:  # noqa: BLE001
                logger.exception("RedisQueueJobQueue failed to start; falling back to in-memory")
                job_queue = InMemoryJobQueue()
        else:
            job_queue = InMemoryJobQueue()
        app.state.job_queue = job_queue

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

    # Emit system.locked once at startup so the worker's CustodialPoller knows
    # the backend has restarted and credentials are not yet available.
    # Payload is topic-only — no secrets, no passphrase. (ADR-0016)
    bus = getattr(app.state, "event_bus", None)
    if bus is not None:
        try:
            bus.publish(
                "system.locked",
                {"topic": "system.locked", "timestamp": datetime.now(UTC).isoformat()},
            )
            logger.info("backend: emitted system.locked (topic-only) at startup")
        except Exception:  # noqa: BLE001 — best-effort; lock middleware covers requests
            logger.warning("backend: could not emit system.locked at startup", exc_info=True)

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

    jq = getattr(app.state, "job_queue", None)
    if jq is not None:
        try:
            jq.close()
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

    # Middleware registration order in Starlette: last registered = outermost
    # (runs first on the way in). LockMiddleware is outermost: a locked server
    # returns 423 before auth is checked. AuthMiddleware is inner.
    app.add_middleware(AuthMiddleware)
    app.add_middleware(LockMiddleware)

    # Implemented in M0-M3.1
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(unlock.router, prefix="/api/v1")
    app.include_router(server_info_routes.router, prefix="/api/v1")
    app.include_router(pairing_routes.router, prefix="/api/v1")
    app.include_router(auth_routes.router, prefix="/api/v1")
    app.include_router(profile_routes.router, prefix="/api/v1")
    app.include_router(feature_flags_routes.router, prefix="/api/v1")
    app.include_router(configuration_routes.router, prefix="/api/v1")

    # M3.2+ routes
    app.include_router(holdings_routes.router, prefix="/api/v1")
    app.include_router(descriptors_routes.router, prefix="/api/v1")
    app.include_router(custodial_providers_routes.router, prefix="/api/v1")
    app.include_router(addresses_routes.router, prefix="/api/v1")
    app.include_router(utxos_routes.router, prefix="/api/v1")
    app.include_router(ledger_entries_routes.router, prefix="/api/v1")
    app.include_router(banking_routes.router, prefix="/api/v1")
    app.include_router(treasury_routes.router, prefix="/api/v1")
    app.include_router(analysis_routes.router, prefix="/api/v1")
    app.include_router(jobs_routes.router, prefix="/api/v1")
    app.include_router(export_routes.router, prefix="/api/v1")
    app.include_router(lightning_routes.router, prefix="/api/v1")

    # Internal — loopback-only by convention (process-level token hardening deferred).
    app.include_router(internal_custodial_routes.router, prefix="/api/v1")

    # SSE event stream
    app.include_router(events_stream_routes.router, prefix="/api/v1")

    return app


app = create_app()
