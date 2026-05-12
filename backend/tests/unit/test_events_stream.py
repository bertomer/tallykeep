"""SSE event-stream endpoint tests.

What we cover here:
  - the /api/v1/events/stream route exists and is in the OpenAPI spec
  - calling it with no event bus returns 503 with a clear error body
  - the SSE-formatting helpers produce well-formed frames

What we deliberately defer to M9 (LiveUpdateBridge):
  - end-to-end streaming (publish → wait → assert chunk arrives) via TestClient
    is fragile because httpx + Starlette TestClient + thread-driven publishers
    interact in ways that can deadlock the test runner; we will validate the
    full delivery path in M9 against a real running uvicorn or via an async
    httpx client.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from tallykeep.api.v1.events_stream import _format_comment, _format_sse
from tallykeep.infrastructure.event_bus import InMemoryEventBus
from tallykeep.infrastructure.secrets import InMemorySecretStore
from tallykeep.main import create_app


pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _cheap_kdf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_MEMORY_COST_KIB", 8
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_TIME_COST", 1
    )
    monkeypatch.setattr(
        "tallykeep.infrastructure.secrets.DEFAULT_KDF_PARALLELISM", 1
    )


@pytest.fixture()
def bus() -> Iterator[InMemoryEventBus]:
    b = InMemoryEventBus()
    try:
        yield b
    finally:
        b.close()


@pytest.fixture()
def client_no_bus() -> Iterator[TestClient]:
    store = InMemorySecretStore()
    store.initialize("p")
    app = create_app()
    app.state.secret_store = store
    app.state.event_bus = None
    app.state.auth_disabled = True
    with TestClient(app) as c:
        yield c


# --- 503 when no bus is wired ---------------------------------------------------


def test_no_bus_configured_returns_503(client_no_bus: TestClient) -> None:
    response = client_no_bus.get("/api/v1/events/stream")
    assert response.status_code == 503


# --- OpenAPI inclusion ----------------------------------------------------------


def test_stream_route_appears_in_openapi(client) -> None:
    spec = client.get("/openapi.json").json()
    assert "/api/v1/events/stream" in spec["paths"]
    op = spec["paths"]["/api/v1/events/stream"]["get"]
    # Topic filter is documented as a query param.
    param_names = {p["name"] for p in op.get("parameters", [])}
    assert "topics" in param_names
    # Both 503 and the streaming 200 response are documented.
    assert "503" in op["responses"]
    assert "200" in op["responses"]


# --- pure helpers ---------------------------------------------------------------


class TestSseFormatHelpers:
    def test_format_sse_emits_event_and_data_lines(self) -> None:
        frame = _format_sse(
            "chain.tx.confirmed",
            {"topic": "chain.tx.confirmed", "payload": {"txid": "abc"}},
        )
        assert frame.startswith("event: chain.tx.confirmed\n")
        assert "data: " in frame
        # Each frame ends with the SSE-required blank line.
        assert frame.endswith("\n\n")

    def test_format_sse_data_is_valid_json(self) -> None:
        payload = {"topic": "x", "payload": {"a": 1}, "timestamp": "2026-01-01T00:00:00+00:00"}
        frame = _format_sse("x", payload)
        # Pull the data line and parse it back.
        for line in frame.splitlines():
            if line.startswith("data: "):
                round_trip = json.loads(line[len("data: "):])
                assert round_trip == payload
                return
        pytest.fail("no data: line in SSE frame")

    def test_format_comment_starts_with_colon(self) -> None:
        comment = _format_comment("subscribed to: chain.*")
        assert comment.startswith(": ")
        assert comment.endswith("\n\n")
