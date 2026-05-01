"""Shared FastAPI dependencies.

Each dependency reads from `request.app.state` so tests can swap implementations by
mutating `app.state` before issuing requests.
"""

from __future__ import annotations

from fastapi import Request

from tallykeep.infrastructure.secrets import SecretStore


def get_secret_store(request: Request) -> SecretStore:
    store = getattr(request.app.state, "secret_store", None)
    if store is None:  # pragma: no cover — guarded by app startup
        raise RuntimeError("Secret store not initialized on app.state")
    return store
