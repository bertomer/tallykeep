"""Custodial job functions executed by the RQ worker.

These functions are enqueued by the backend (request handlers) and executed in
the worker process by the RQ worker thread. They must be importable at the
module level (no closure captures, no unpicklable references).

All dependencies (HTTP client, bus, repos) are constructed from configuration
inside the function, not injected at enqueue time.
"""

from __future__ import annotations

import logging
from uuid import UUID


logger = logging.getLogger(__name__)


def one_shot_custodial_poll(provider_id: UUID) -> dict:
    """Dispatch a single poll-cycle for the given provider against the backend.

    Executed in the worker process by the RQ worker thread. Constructs an HTTP
    client from settings rather than accepting any injected dependency so the
    function remains picklable across process boundaries.

    Return value is stored in the RQ job result and surfaced via GET /jobs/{id}.
    """
    import httpx

    from tallykeep.configuration import get_settings

    settings = get_settings()
    url = f"{settings.backend_url}/api/v1/internal/custodial/{provider_id}/poll-cycle"

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url)
    except httpx.RequestError as exc:
        logger.warning(
            "one_shot_custodial_poll: HTTP request failed for provider %s: %s",
            provider_id,
            exc,
        )
        raise RuntimeError(f"HTTP request failed: {exc}") from exc

    if resp.status_code == 423:
        logger.debug(
            "one_shot_custodial_poll: backend locked for provider %s (423)", provider_id
        )
        return {"status": "skipped", "reason": "backend_locked"}

    if resp.status_code == 404:
        logger.info(
            "one_shot_custodial_poll: provider %s not found (404)", provider_id
        )
        return {"status": "skipped", "reason": "provider_not_found"}

    if resp.status_code != 200:
        logger.warning(
            "one_shot_custodial_poll: unexpected %d for provider %s: %s",
            resp.status_code,
            provider_id,
            resp.text[:200],
        )
        raise RuntimeError(
            f"poll-cycle returned {resp.status_code} for provider {provider_id}"
        )

    result = resp.json()
    logger.debug(
        "one_shot_custodial_poll: cycle completed for provider %s: %s", provider_id, result
    )
    return {"status": "ok", "result": result}


__all__ = ["one_shot_custodial_poll"]
