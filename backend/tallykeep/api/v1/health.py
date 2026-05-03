"""Health endpoint per spec module 04.

Each subsystem check has a stable shape `{ok: bool, ...}`. Subsystems that are not
yet wired return `ok: false` with `reason: "not_yet_implemented"` and the overall
status is `degraded`. As later milestones land each subsystem they replace the
placeholder probes here.
"""

from __future__ import annotations

from typing import Literal

import sqlalchemy as sa
from fastapi import APIRouter, Request
from pydantic import BaseModel

from tallykeep import __version__
from tallykeep.configuration import get_settings


router = APIRouter(tags=["health"])


class CheckResult(BaseModel):
    ok: bool
    detail: str | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, CheckResult]


def _probe_database() -> CheckResult:
    settings = get_settings()
    if not settings.database_url:
        return CheckResult(ok=False, reason="not_configured")
    try:
        # Lazy engine — avoid coupling /health to import-time engine creation, so
        # tests that don't have a database can still hit /health.
        from tallykeep.infrastructure.database import get_engine

        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return CheckResult(ok=True)
    except Exception as exc:  # noqa: BLE001 — we want any failure to surface here
        return CheckResult(ok=False, reason="unreachable", detail=str(exc)[:200])


def _probe_unlocked(request: Request) -> CheckResult:
    store = getattr(request.app.state, "secret_store", None)
    if store is None:
        # No store configured (no database URL); treat as not-applicable but report
        # as not-yet-implemented so the contract shape stays consistent.
        return CheckResult(ok=False, reason="not_yet_implemented")
    try:
        if store.is_unlocked():
            return CheckResult(ok=True)
        if not store.is_initialized():
            # is_initialized() may hit the database for the encrypted-database backend,
            # so we treat its failure as "we cannot determine init state" rather than
            # propagating the exception out of /health.
            return CheckResult(ok=False, reason="not_initialized")
        return CheckResult(ok=False, reason="locked")
    except Exception as exc:  # noqa: BLE001 — health probes never raise.
        return CheckResult(ok=False, reason="probe_failed", detail=str(exc)[:200])


def _probe_redis() -> CheckResult:
    settings = get_settings()
    if not settings.redis_url:
        return CheckResult(ok=False, reason="not_configured")
    try:
        import redis as _redis

        client = _redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            client.ping()
        finally:
            client.close()
        return CheckResult(ok=True)
    except Exception as exc:  # noqa: BLE001
        return CheckResult(ok=False, reason="unreachable", detail=str(exc)[:200])


def _probe_bitcoind() -> CheckResult:
    settings = get_settings()
    if not settings.bitcoind_rpc_url:
        return CheckResult(ok=False, reason="not_configured")
    try:
        from tallykeep.adapters.node_adapter import NodeAdapter

        with NodeAdapter(settings.bitcoind_rpc_url, timeout_seconds=2.0) as node:
            info = node.get_blockchain_info()
        return CheckResult(
            ok=True,
            detail=f"chain={info.chain} height={info.blocks}",
        )
    except Exception as exc:  # noqa: BLE001 — health probes never raise
        return CheckResult(ok=False, reason="unreachable", detail=str(exc)[:200])


def _probe_event_bus(request: Request) -> CheckResult:
    """Reflects the running app's bus health.

    The bus is lazily attached to `app.state.event_bus` by the worker process
    and (in M2.3) by the API process when a downstream feature needs it. When
    the bus has not been instantiated, we report 'not_initialized' rather than
    spinning one up just for the probe.
    """
    bus = getattr(request.app.state, "event_bus", None)
    if bus is None:
        return CheckResult(ok=False, reason="not_initialized")
    is_healthy = getattr(bus, "is_healthy", None)
    if not callable(is_healthy):
        # In-memory bus has no health probe — treat as healthy if it's wired.
        return CheckResult(ok=True)
    try:
        return CheckResult(ok=bool(is_healthy()))
    except Exception as exc:  # noqa: BLE001
        return CheckResult(ok=False, reason="probe_failed", detail=str(exc)[:200])


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    checks: dict[str, CheckResult] = {
        "database": _probe_database(),
        "bitcoind": _probe_bitcoind(),
        "redis": _probe_redis(),
        "event_bus": _probe_event_bus(request),
        "unlocked": _probe_unlocked(request),
    }
    overall: Literal["ok", "degraded"] = (
        "ok" if all(c.ok for c in checks.values()) else "degraded"
    )
    return HealthResponse(status=overall, version=__version__, checks=checks)
