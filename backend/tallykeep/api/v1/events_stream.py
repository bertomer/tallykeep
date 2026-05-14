"""Server-Sent Events stream — spec module 04.

GET /api/v1/events/stream
  Query: ?topics=chain.*,holding.*,banking.*,treasury.*,...
         (default: all topics)
  Response: text/event-stream

Each event arrives as:
  event: <topic>
  data: { "topic": ..., "payload": ..., "timestamp": ... }

The endpoint subscribes to the EventBus with the requested patterns. As events
arrive they are forwarded to the connected client. When the client disconnects,
the subscription is removed.

Backpressure: per-client async Queue capped at `_QUEUE_MAX` events. If the
client falls behind, the oldest events are dropped (spec module 04: "drop the
oldest if a client falls behind"). A diagnostic SSE comment is emitted on drops
so the client can detect missed events and refetch.

This is a working scaffold. The full LiveUpdateBridge (filtering by holding,
authentication-equivalent gating once that lands, reconnect tokens) is M9.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from tallykeep.api.dependencies import get_event_bus
from tallykeep.infrastructure.event_bus import Event, EventBus


logger = logging.getLogger(__name__)


router = APIRouter(tags=["events"])


_QUEUE_MAX = 1000  # per-connection backlog cap before drop-oldest kicks in


def _format_sse(event_name: str, data: dict[str, Any]) -> str:
    """Format a single event per the SSE spec."""
    serialized = json.dumps(data, separators=(",", ":"), default=str)
    return f"event: {event_name}\ndata: {serialized}\n\n"


def _format_comment(text: str) -> str:
    """SSE comments start with `:` and are useful for keepalives and diagnostics."""
    return f": {text}\n\n"


async def _stream_events(
    request: Request,
    bus: EventBus,
    patterns: list[str],
) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Event] | tuple[str, None]] = asyncio.Queue(
        maxsize=_QUEUE_MAX
    )
    dropped_since_last: int = 0

    def _on_bus_event(event: Event) -> None:
        # Bus handler runs on the bus's thread (Redis background reader, or the
        # publisher's thread for the in-memory bus). Marshal back into the event
        # loop's thread before touching the asyncio queue.
        nonlocal dropped_since_last

        def _enqueue() -> None:
            nonlocal dropped_since_last
            try:
                queue.put_nowait(("event", event))
            except asyncio.QueueFull:
                # Drop oldest and try again — preserves liveness over backlog.
                with contextlib.suppress(asyncio.QueueEmpty):
                    queue.get_nowait()
                dropped_since_last += 1
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait(("event", event))

        loop.call_soon_threadsafe(_enqueue)

    subscription = bus.subscribe(patterns, _on_bus_event)

    # Initial handshake comment so the client knows the stream is live and what
    # patterns are subscribed.
    yield _format_comment(f"subscribed to: {', '.join(patterns)}")

    try:
        while True:
            # Cancellation-safe wait for the next event. If the client
            # disconnects, FastAPI cancels the generator and we land in
            # `finally`.
            kind, event = await queue.get()
            if event is None:
                continue
            if dropped_since_last:
                # Inform the client that they missed N events so they can
                # refetch state via the regular GET endpoints.
                yield _format_comment(
                    f"dropped {dropped_since_last} event(s) due to backlog"
                )
                dropped_since_last = 0
            yield _format_sse(
                event.topic,
                {
                    "id": str(event.id),
                    "topic": event.topic,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat(),
                },
            )
    except asyncio.CancelledError:  # pragma: no cover — exercised by client disconnect
        pass
    finally:
        subscription.unsubscribe()


@router.get(
    "/events/stream",
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {}},
        },
        503: {
            "description": "Event bus not configured (TALLYKEEP_REDIS_URL unset)",
        },
    },
)
async def events_stream(
    request: Request,
    topics: str = "*",
    bus: EventBus | None = Depends(get_event_bus),
) -> StreamingResponse:
    if bus is None:
        # Caller asked to subscribe but no bus is wired — explicit error so the
        # frontend can surface a clear message rather than waiting forever.
        raise HTTPException(
            status_code=503,
            detail="Event bus not configured",
        )

    patterns = [p.strip() for p in topics.split(",") if p.strip()] or ["*"]

    return StreamingResponse(
        _stream_events(request, bus, patterns),
        media_type="text/event-stream",
        headers={
            # Tell intermediaries (nginx) not to buffer.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
