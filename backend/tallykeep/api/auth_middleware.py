"""Device-credential auth middleware — auth layer (spec 01 §"Network security posture").

Every API endpoint requires a valid device credential
(`Authorization: Bearer <credential>`) except the explicitly exempted paths.

Exempt paths (no device credential needed):
  /api/v1/health          — always open
  /api/v1/unlock          — server-admin passphrase unlock (runs before any device is paired)
  /api/v1/server/info     — open metadata for pairing flow
  /api/v1/pairing         — issue and redeem (phone has no credential yet)
  /openapi.json /docs     — development tooling

Validation: credentials are Argon2id-hashed at pairing time. Because running
Argon2id on every request would be prohibitively slow, validated credentials are
cached in process memory (credential → device_id). Cache TTL is 5 minutes;
entries are evicted on revocation via the DELETE /api/v1/devices/:id endpoint.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher, exceptions as argon2_exceptions
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware

from tallykeep.models.paired_device import PairedDeviceRow


AUTH_EXEMPT_PREFIXES = (
    "/api/v1/health",
    "/api/v1/unlock",
    "/api/v1/server/info",
    "/api/v1/pairing",
    "/api/v1/auth/passphrase-validate",
    "/openapi.json",
    "/docs",
)

_CREDENTIAL_CACHE_TTL_SECONDS = 300  # 5 minutes

_credential_hasher = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)


def _is_exempt(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in AUTH_EXEMPT_PREFIXES)


def _get_credential_cache(request: Request) -> dict[str, Any]:
    if not hasattr(request.app.state, "credential_cache"):
        request.app.state.credential_cache = {}
    return request.app.state.credential_cache  # type: ignore[no-any-return]


def _cache_lookup(cache: dict[str, Any], credential: str) -> str | None:
    """Return cached device_id if the credential is known-valid, else None."""
    entry = cache.get(credential)
    if entry is None:
        return None
    if datetime.now(UTC) > entry["expires_at"]:
        del cache[credential]
        return None
    return entry["device_id"]  # type: ignore[no-any-return]


def _cache_store(cache: dict[str, Any], credential: str, device_id: str) -> None:
    cache[credential] = {
        "device_id": device_id,
        "expires_at": datetime.now(UTC) + timedelta(seconds=_CREDENTIAL_CACHE_TTL_SECONDS),
    }


def _validate_credential_against_db(
    session: Session, credential: str
) -> str | None:
    """Return device_id if valid + not-revoked, else None. Runs Argon2id verify."""
    rows = session.execute(select(PairedDeviceRow).where(PairedDeviceRow.revoked_at.is_(None))).scalars().all()
    for row in rows:
        try:
            if _credential_hasher.verify(row.credential_hash, credential):
                # Update last_seen_at on successful auth.
                row.last_seen_at = datetime.now(UTC)
                session.commit()
                return str(row.id)
        except argon2_exceptions.VerifyMismatchError:
            continue
        except argon2_exceptions.VerificationError:
            continue
    return None


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        path = request.url.path

        if _is_exempt(path):
            return await call_next(request)

        # Tests may set app.state.auth_disabled = True to bypass credential checks.
        # This is an in-process flag only — not controllable via HTTP.
        if getattr(request.app.state, "auth_disabled", False):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return _unauthorized("Missing or malformed Authorization header")

        credential = auth_header[len("Bearer "):]
        if not credential:
            return _unauthorized("Empty credential")

        cache = _get_credential_cache(request)
        device_id = _cache_lookup(cache, credential)

        if device_id is None:
            # Cache miss — check the database.
            session_factory = getattr(request.app.state, "session_factory", None)
            if session_factory is None:
                # No database configured (test or bootstrap mode) — deny.
                return _unauthorized("No device store available")

            with session_factory() as session:
                device_id = _validate_credential_against_db(session, credential)

            if device_id is None:
                return _unauthorized("Invalid or revoked credential")

            _cache_store(cache, credential, device_id)

        # Expose device_id downstream via request.state for audit logging later.
        request.state.device_id = device_id
        return await call_next(request)


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "type": "/errors/unauthorized",
            "title": "Unauthorized",
            "status": 401,
            "detail": detail,
        },
    )
