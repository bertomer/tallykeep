"""FastAPI entry point.

Spec module 01: backend handles HTTP API and SSE. This module wires the API only;
the worker process has its own entry point at `tallykeep.worker`.
"""

from __future__ import annotations

from fastapi import FastAPI

from tallykeep import __version__
from tallykeep.api.v1 import health


def create_app() -> FastAPI:
    app = FastAPI(
        title="TallyKeep",
        version=__version__,
        # OpenAPI is exposed at /openapi.json by default. Per spec module 04, the
        # frontend consumes it via a generated typed client.
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url=None,
    )

    app.include_router(health.router, prefix="/api/v1")

    return app


app = create_app()
