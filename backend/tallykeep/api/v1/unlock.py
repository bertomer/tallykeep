"""Unlock endpoints — spec module 04.

POST /api/v1/unlock                — verify passphrase, unlock the secret store.
POST /api/v1/unlock/initialize     — first-run setup; both initializes and unlocks.

The lock state and crypto parameters are owned by the SecretStore. These endpoints
are the only API surface that can transition between locked / unlocked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from tallykeep.api.dependencies import get_secret_store
from tallykeep.infrastructure.secrets import (
    AlreadyInitializedError,
    NotInitializedError,
    SecretStore,
    WrongPassphraseError,
)


router = APIRouter(tags=["unlock"])


class UnlockRequest(BaseModel):
    passphrase: str = Field(min_length=1, max_length=4096)


class UnlockResponse(BaseModel):
    unlocked: bool


class InitializeResponse(BaseModel):
    initialized: bool
    unlocked: bool


@router.post(
    "/unlock",
    response_model=UnlockResponse,
    responses={
        401: {"description": "Bad passphrase"},
        503: {"description": "Crypto parameters not initialized — first run required"},
    },
)
async def post_unlock(
    body: UnlockRequest,
    store: SecretStore = Depends(get_secret_store),
) -> UnlockResponse:
    try:
        store.unlock(body.passphrase)
    except NotInitializedError as exc:
        # Spec module 04: "503: crypto parameters not initialized (first-run)"
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WrongPassphraseError as exc:
        # Spec module 04: "401: bad passphrase"
        raise HTTPException(status_code=401, detail="Bad passphrase") from exc
    return UnlockResponse(unlocked=True)


@router.post(
    "/unlock/initialize",
    response_model=InitializeResponse,
    responses={
        409: {"description": "Already initialized"},
    },
)
async def post_unlock_initialize(
    body: UnlockRequest,
    store: SecretStore = Depends(get_secret_store),
) -> InitializeResponse:
    try:
        store.initialize(body.passphrase)
    except AlreadyInitializedError as exc:
        # Spec module 04: "409: already initialized"
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return InitializeResponse(initialized=True, unlocked=True)
