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


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    not_yet = CheckResult(ok=False, reason="not_yet_implemented")
    checks: dict[str, CheckResult] = {
        "database": _probe_database(),
        "bitcoind": not_yet,
        "redis": not_yet,
        "event_bus": not_yet,
        "unlocked": _probe_unlocked(request),
    }
    overall: Literal["ok", "degraded"] = (
        "ok" if all(c.ok for c in checks.values()) else "degraded"
    )
    return HealthResponse(status=overall, version=__version__, checks=checks)
