"""Unlock endpoints — spec module 04.

POST /api/v1/unlock                — verify passphrase, unlock the secret store.
POST /api/v1/unlock/initialize     — first-run setup; both initializes and unlocks.

On successful unlock, an immediate poll is dispatched for every active custodial
provider via the backend's CustodialPollHandler — no interval guard, no event bus.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from tallykeep.api.dependencies import get_secret_store
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


def _trigger_immediate_polls(request: Request) -> None:
    handler = getattr(request.app.state, "custodial_poll_handler", None)
    if handler is not None:
        try:
            handler.poll_all_immediately()
        except Exception:
            logger.warning("unlock: could not trigger immediate polls", exc_info=True)


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

    _trigger_immediate_polls(request)
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

    _trigger_immediate_polls(request)
    return InitializeResponse(initialized=True, unlocked=True)
