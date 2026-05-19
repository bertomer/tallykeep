"""Auth endpoints — passphrase-validate and device management.

POST /api/v1/auth/passphrase-validate   — phone unlock: validates passphrase, unlocks
                                          the secret store, and emits system.unlocked.
                                          Rate-limited. Exempt from both the lock
                                          middleware and device-credential auth so it
                                          works from a cold (locked) server.
DELETE /api/v1/devices/{device_id}       — revoke a paired device credential.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tallykeep.api.dependencies import get_db_session, get_secret_store
from tallykeep.infrastructure.secrets import NotInitializedError, SecretStore, WrongPassphraseError
from tallykeep.models.paired_device import PairedDeviceRow

router = APIRouter(tags=["auth"])

# Rate-limit: after this many consecutive wrong-passphrase attempts from one IP,
# return 429 until the window resets.
_RATE_LIMIT_MAX_FAILURES = 10
_RATE_LIMIT_WINDOW_SECONDS = 900  # 15 minutes


def _get_rate_limit_store(request: Request) -> dict[str, Any]:
    if not hasattr(request.app.state, "passphrase_rate_limits"):
        request.app.state.passphrase_rate_limits = defaultdict(
            lambda: {"failures": 0, "window_start": datetime.now(UTC)}
        )
    return request.app.state.passphrase_rate_limits  # type: ignore[no-any-return]


def _check_rate_limit(store: dict[str, Any], client_ip: str) -> None:
    """Raise HTTPException 429 if the client has exceeded the failure threshold."""
    entry = store[client_ip]
    now = datetime.now(UTC)
    if (now - entry["window_start"]).total_seconds() > _RATE_LIMIT_WINDOW_SECONDS:
        entry["failures"] = 0
        entry["window_start"] = now
    if entry["failures"] >= _RATE_LIMIT_MAX_FAILURES:
        raise HTTPException(
            status_code=429,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(_RATE_LIMIT_WINDOW_SECONDS)},
        )


# Keep old name as an alias so other callers (if any) don't break.
def _check_and_record_attempt(
    store: dict[str, Any], client_ip: str, success: bool
) -> None:
    _check_rate_limit(store, client_ip)
    if success:
        store[client_ip]["failures"] = 0
    else:
        store[client_ip]["failures"] += 1


# ---------- Request / response models ----------

class PassphraseValidateRequest(BaseModel):
    passphrase: str = Field(min_length=1, max_length=4096)


class PassphraseValidateResponse(BaseModel):
    valid: bool


# ---------- Endpoints ----------

@router.post(
    "/auth/passphrase-validate",
    response_model=PassphraseValidateResponse,
    responses={
        401: {"description": "Wrong passphrase"},
        429: {"description": "Too many failed attempts"},
    },
)
async def post_passphrase_validate(
    body: PassphraseValidateRequest,
    request: Request,
    store: SecretStore = Depends(get_secret_store),
) -> PassphraseValidateResponse:
    """Phone unlock: validate passphrase, unlock the secret store, emit system.unlocked.

    Exempt from the lock middleware so it works against a cold (locked) server.
    Rate-limited per ADR-0008.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limits = _get_rate_limit_store(request)

    _check_rate_limit(rate_limits, client_ip)

    try:
        store.unlock(body.passphrase)
    except NotInitializedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except WrongPassphraseError:
        rate_limits[client_ip]["failures"] += 1
        raise HTTPException(status_code=401, detail="Wrong passphrase")

    rate_limits[client_ip]["failures"] = 0

    bus = getattr(request.app.state, "event_bus", None)
    if bus is not None:
        try:
            bus.publish(
                "system.unlocked",
                {"topic": "system.unlocked", "timestamp": datetime.now(UTC).isoformat()},
            )
        except Exception:
            pass

    return PassphraseValidateResponse(valid=True)


@router.delete(
    "/devices/{device_id}",
    status_code=204,
    response_model=None,
    responses={
        404: {"description": "Device not found"},
    },
)
async def delete_device(
    device_id: UUID,
    session: Session = Depends(get_db_session),
) -> None:
    """Revoke a paired device credential.

    After revocation, subsequent requests from that device return 401.
    The device-list UI (desktop iteration) calls this; the endpoint ships now
    so the backend contract is in place.
    """
    row = session.get(PairedDeviceRow, device_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        session.commit()
