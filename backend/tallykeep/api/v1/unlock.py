"""Unlock endpoints — spec module 04.

POST /api/v1/unlock                — verify passphrase, unlock the secret store.
POST /api/v1/unlock/initialize     — first-run setup; both initializes and unlocks.

On successful unlock, emits system.unlocked (topic-only) on the event bus.
The worker's CustodialPoller subscribes to this event and triggers a catch-up
burst of poll-cycle calls to the backend. No passphrase or derived material
in the event payload. (ADR-0016)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from tallykeep.api.dependencies import get_event_bus, get_secret_store
from tallykeep.infrastructure.secrets import (
    AlreadyInitializedError,
    NotInitializedError,
    SecretStore,
    WrongPassphraseError,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["unlock"])


class UnlockRequest(BaseModel):
    passphrase: str = Field(min_length=1, max_length=4096)


class UnlockResponse(BaseModel):
    unlocked: bool


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
    "/unlock",
    response_model=UnlockResponse,
    responses={
        401: {"description": "Bad passphrase"},
        503: {"description": "Crypto parameters not initialized — first run required"},
    },
)
async def post_unlock(
    request: Request,
    body: UnlockRequest,
    store: SecretStore = Depends(get_secret_store),
) -> UnlockResponse:
    try:
        store.unlock(body.passphrase)
    except NotInitializedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WrongPassphraseError as exc:
        raise HTTPException(status_code=401, detail="Bad passphrase") from exc

    _emit_system_unlocked(request)
    return UnlockResponse(unlocked=True)


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
