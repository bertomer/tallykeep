"""Unlock endpoints — spec module 04.

POST /api/v1/unlock/initialize     — first-run setup; both initializes and unlocks.

Day-to-day unlock (after a restart) is handled by POST /api/v1/auth/passphrase-validate,
which validates the passphrase, unlocks the secret store, and emits system.unlocked in
one call. That endpoint also carries rate limiting, making it the right phone-facing path.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from tallykeep.api.dependencies import get_event_bus, get_secret_store
from tallykeep.infrastructure.secrets import (
    AlreadyInitializedError,
    SecretStore,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["unlock"])


class UnlockRequest(BaseModel):
    passphrase: str = Field(min_length=1, max_length=4096)


class InitializeResponse(BaseModel):
    initialized: bool
    unlocked: bool


def _emit_system_unlocked(request: Request) -> None:
    bus = getattr(request.app.state, "event_bus", None)
    if bus is not None:
        try:
            bus.publish(
                "system.unlocked",
                {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
            )
            logger.info("unlock: emitted system.unlocked (topic-only)")
        except Exception:
            logger.warning("unlock: could not emit system.unlocked", exc_info=True)


@router.post(
    "/unlock/initialize",
    response_model=InitializeResponse,
    responses={
        409: {"description": "Already initialized"},
    },
)
async def post_unlock_initialize(
    request: Request,
    body: UnlockRequest,
    store: SecretStore = Depends(get_secret_store),
) -> InitializeResponse:
    try:
        store.initialize(body.passphrase)
    except AlreadyInitializedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    _emit_system_unlocked(request)
    return InitializeResponse(initialized=True, unlocked=True)
