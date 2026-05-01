"""Health endpoint per spec module 04.

Each subsystem check has a stable shape `{ok: bool, ...}`. Subsystems that are not yet
wired in this milestone return `ok: false` with `reason: "not_yet_implemented"` and the
overall status is `degraded`. As later milestones land each subsystem, this file is
where they get wired in — there should be no churn elsewhere.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from tallykeep import __version__

router = APIRouter(tags=["health"])


class CheckResult(BaseModel):
    ok: bool
    detail: str | None = None
    reason: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: dict[str, CheckResult]


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    # Each subsystem will be replaced by a real probe as it lands. Keeping the keys
    # stable now means the frontend and tests can rely on them across milestones.
    not_yet = CheckResult(ok=False, reason="not_yet_implemented")
    checks: dict[str, CheckResult] = {
        "database": not_yet,
        "bitcoind": not_yet,
        "redis": not_yet,
        "event_bus": not_yet,
        "unlocked": CheckResult(ok=False, reason="not_yet_implemented"),
    }
    overall: Literal["ok", "degraded"] = (
        "ok" if all(c.ok for c in checks.values()) else "degraded"
    )
    return HealthResponse(status=overall, version=__version__, checks=checks)
