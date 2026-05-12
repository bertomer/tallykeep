"""Pairing endpoints — device onboarding (auth layer, spec 01 §"Network security posture").

POST /api/v1/pairing/issue   — server-side: generate a one-time pairing token.
POST /api/v1/pairing/redeem  — phone-side: exchange token for a long-lived device credential.

Token lifecycle: single-use, ~60 s TTL, stored in process memory on app.state.
Device credential: 32 random bytes (base64url), Argon2id-hashed and stored in paired_device table.
Both endpoints are exempt from auth middleware and lock middleware (phones need them before
they have a device credential, and the store may be locked when the client connects).
"""

from __future__ import annotations

import secrets
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from argon2 import PasswordHasher
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session
from tallykeep.models.paired_device import PairedDeviceRow

router = APIRouter(tags=["pairing"])

# One-time pairing tokens are short-lived — no need to persist them across restarts.
# Stored in app.state.pairing_tokens: {token_hex: {"expires_at": datetime, "redeemed": bool}}
PAIRING_TOKEN_TTL_SECONDS = 60

# Credential hashing uses minimal Argon2id cost because the credential is
# 32 random bytes (256 bits entropy). The slowness of Argon2id is for
# low-entropy passwords; here we need only the one-way property.
_credential_hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


def _get_token_store(request: Request) -> dict[str, Any]:
    """Return (and lazily create) the in-memory pairing token store."""
    if not hasattr(request.app.state, "pairing_tokens"):
        request.app.state.pairing_tokens = {}
    return request.app.state.pairing_tokens  # type: ignore[no-any-return]


def _purge_expired(store: dict[str, Any]) -> None:
    now = datetime.now(UTC)
    expired = [k for k, v in store.items() if v["expires_at"] < now]
    for k in expired:
        del store[k]


# ---------- Request / response models ----------

class PairingIssueResponse(BaseModel):
    pairing_token: str
    expires_at: str  # ISO-8601 UTC


class PairingRedeemRequest(BaseModel):
    pairing_token: str = Field(min_length=1, max_length=256)
    device_label: str | None = Field(default=None, max_length=200)


class PairingRedeemResponse(BaseModel):
    device_id: str
    device_credential: str  # raw base64url credential; phone stores via NativeBridge


# ---------- Endpoints ----------

@router.post("/pairing/issue", response_model=PairingIssueResponse)
async def post_pairing_issue(request: Request) -> PairingIssueResponse:
    """Generate a one-time pairing token.

    Called by the server operator (CLI or future desktop UI) to display as a QR
    or plain token. Exempt from auth because it's a server-admin operation that
    runs before any device is paired (or when adding a second device later).
    """
    store = _get_token_store(request)
    _purge_expired(store)

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=PAIRING_TOKEN_TTL_SECONDS)
    store[token] = {"expires_at": expires_at, "redeemed": False}
    return PairingIssueResponse(
        pairing_token=token,
        expires_at=expires_at.isoformat(),
    )


@router.post(
    "/pairing/redeem",
    response_model=PairingRedeemResponse,
    responses={
        401: {"description": "Invalid, expired, or already-redeemed token"},
    },
)
async def post_pairing_redeem(
    body: PairingRedeemRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> PairingRedeemResponse:
    """Exchange a one-time pairing token for a long-lived device credential.

    Phone-side endpoint. After this call the phone stores the returned
    device_credential via NativeBridge.secureStorage. The credential is
    returned exactly once; if lost, re-pair.
    """
    store = _get_token_store(request)
    _purge_expired(store)

    entry = store.get(body.pairing_token)
    if entry is None or entry["redeemed"] or datetime.now(UTC) > entry["expires_at"]:
        raise HTTPException(status_code=401, detail="Invalid, expired, or already-redeemed pairing token")

    # Mark redeemed immediately to prevent double-use (token is valid only once).
    entry["redeemed"] = True

    raw_credential = secrets.token_bytes(32)
    credential_b64 = urlsafe_b64encode(raw_credential).rstrip(b"=").decode("ascii")

    credential_hash = _credential_hasher.hash(credential_b64)
    now = datetime.now(UTC)
    device_id = uuid4()

    row = PairedDeviceRow(
        id=device_id,
        credential_hash=credential_hash,
        label=body.device_label,
        created_at=now,
        last_seen_at=now,
        revoked_at=None,
    )
    session.add(row)
    session.commit()

    return PairingRedeemResponse(
        device_id=str(device_id),
        device_credential=credential_b64,
    )
