"""Shared FastAPI dependencies.

Each dependency reads from `request.app.state` so tests can swap implementations by
mutating `app.state` before issuing requests.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.infrastructure.job_queue import JobQueue
from tallykeep.infrastructure.secrets import SecretStore


def get_secret_store(request: Request) -> SecretStore:
    store = getattr(request.app.state, "secret_store", None)
    if store is None:  # pragma: no cover — guarded by app startup
        raise RuntimeError("Secret store not initialized on app.state")
    return store


def get_session_factory(request: Request) -> sessionmaker[Session]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise RuntimeError(
            "Database session factory not initialized on app.state"
        )
    return factory


def get_db_session(request: Request) -> Iterator[Session]:
    """Per-request session — closed after the response is rendered."""
    factory = get_session_factory(request)
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_event_bus(request: Request) -> EventBus | None:
    """Returns the bus or None when not configured (e.g. in unit tests)."""
    return getattr(request.app.state, "event_bus", None)


def get_job_queue(request: Request) -> JobQueue:
    from fastapi import HTTPException

    queue = getattr(request.app.state, "job_queue", None)
    if queue is None:
        raise HTTPException(status_code=503, detail="Job queue not available")
    return queue


def get_node_adapter(request: Request):  # type: ignore[no-untyped-def]
    """Return the bitcoind NodeAdapter; 503 to the caller if not configured.

    Endpoints that need the chain depend on this. Tests inject their own (or
    pre-set the attribute on app.state) before issuing requests.
    """
    from fastapi import HTTPException

    adapter = getattr(request.app.state, "node_adapter", None)
    if adapter is None:
        raise HTTPException(
            status_code=503,
            detail="bitcoind RPC is not configured",
        )
    return adapter
