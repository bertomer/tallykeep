"""RFC 7807 Problem Details body shape used across the API.

Spec module 04 mandates this format for error responses. We use this both for
the lock middleware (423) and for the not-yet-implemented stubs (501) added in
M3.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProblemDetails(BaseModel):
    """RFC 7807 problem-details object.

    `type` is a URI reference identifying the problem type — we use absolute
    `/errors/<slug>` references local to our API namespace for v1.
    """

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        ...,
        description="URI reference identifying the problem type",
        examples=["/errors/feature-not-implemented"],
    )
    title: str = Field(..., description="Short human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: str | None = Field(
        default=None, description="Human-readable explanation specific to this occurrence"
    )
    instance: str | None = Field(
        default=None, description="URI reference identifying the specific occurrence"
    )

    # Allow callers to attach extra fields (e.g. `milestone`, `discrepancy_kind`)
    # without breaking schema validation. Pydantic's `extra="allow"` lets these
    # round-trip in dict() / model_dump().


def problem(
    *,
    status: int,
    type_slug: str,
    title: str,
    detail: str | None = None,
    **extras: Any,
) -> dict[str, Any]:
    """Build a problem-details dict ready to pass to JSONResponse(content=...).

    `type_slug` is the path component after `/errors/` — e.g. `not-implemented`.
    """
    body: dict[str, Any] = {
        "type": f"/errors/{type_slug}",
        "title": title,
        "status": status,
    }
    if detail:
        body["detail"] = detail
    body.update(extras)
    return body
