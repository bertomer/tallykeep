"""423 Locked middleware — spec module 04.

When the secret store is locked, every endpoint except the unlock endpoints, the
health endpoint, and the OpenAPI spec returns 423.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# Paths that always work regardless of lock state.
ALWAYS_ALLOWED_PREFIXES = (
    "/api/v1/health",
    "/api/v1/unlock",
    "/openapi.json",
    "/docs",
)


class LockMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable],
    ):
        path = request.url.path

        # Allowlist: health and unlock work regardless of lock state.
        if any(path == p or path.startswith(p + "/") or path == p for p in ALWAYS_ALLOWED_PREFIXES):
            return await call_next(request)
        # Defensive equality check above also handles bare /api/v1/unlock without trailing slash.

        store = getattr(request.app.state, "secret_store", None)
        if store is None or not store.is_unlocked():
            return JSONResponse(
                status_code=423,
                content={
                    "type": "/errors/locked",
                    "title": "Locked",
                    "status": 423,
                    "detail": (
                        "Secret store is locked. POST /api/v1/unlock with the "
                        "passphrase to proceed."
                    ),
                },
            )

        return await call_next(request)
