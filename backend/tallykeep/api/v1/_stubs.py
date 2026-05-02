"""Helpers for the M3 stub routes.

Each milestone past M3 implements its own routes; until then the routes exist as
501-returning stubs so the API contract from spec module 04 is reservable end-to-end
(the OpenAPI spec covers everything, the frontend can generate its typed client now).
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

from tallykeep.schemas.errors import problem


def not_implemented_response(*, milestone: str, route: str) -> JSONResponse:
    """Return a 501 JSONResponse with an RFC-7807-shaped body at the top level.

    Use as the return value of every stub handler:
        @router.get("/holdings")
        async def list_holdings():
            return not_implemented_response(
                milestone="M4", route="GET /api/v1/holdings"
            )
    """
    return JSONResponse(
        status_code=501,
        content=problem(
            status=501,
            type_slug="not-implemented",
            title="Not implemented",
            detail=(
                f"{route} is reserved by spec module 04 and lands in {milestone}."
            ),
            milestone=milestone,
            route=route,
        ),
    )
