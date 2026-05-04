"""Unit tests for ChainEventAdapter.

We avoid spinning up a real ZMQ socket here — those run in the integration
suite under `test_chain_listener_live.py`. Instead we stub out the pyzmq
socket the adapter uses, so we can prove:

  - subscribe() opens a socket, applies receive timeout + HWM, joins topics
  - iter_messages() decodes bitcoind's 3-frame multipart correctly
  - ChainNotification.hash_hex reverses the byte order to match RPC display
  - close() unblocks the loop on the next iteration
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.unit


class _FakeSocket:
    """Stand-in for zmq.Socket. Records subscribe calls and serves multipart
    frames out of an in-memory queue."""

    def __init__(self, frames: list[list[bytes]]) -> None:
        self._frames = list(frames)
        self.sock_options: list[tuple[int, object]] = []
        self.subscribed_topics: list[bytes] = []
        self.connected_to: str | None = None
        self.closed = False

    def setsockopt(self, opt: int, value: object) -> None:
        if opt == _FakeZmq.SUBSCRIBE:
            assert isinstance(value, bytes)
            self.subscribed_topics.append(value)
        else:
            self.sock_options.append((opt, value))

    def connect(self, endpoint: str) -> None:
        self.connected_to = endpoint

    def recv_multipart(self) -> list[bytes]:
        if not self._frames:
            raise _FakeZmq.Again("no more frames")
        return self._frames.pop(0)

    def close(self, linger: int = 0) -> None:
        self.closed = True


class _FakeContext:
    SUB = "SUB"

    def __init__(self) -> None:
        self.sockets: list[_FakeSocket] = []
        self._next_socket: _FakeSocket | None = None

    def queue_socket(self, socket: _FakeSocket) -> None:
        self._next_socket = socket

    def socket(self, kind: object) -> _FakeSocket:
        if self._next_socket is None:
            raise AssertionError("no socket queued for the fake context")
        sock = self._next_socket
        self._next_socket = None
        self.sockets.append(sock)
        return sock


class _FakeZmq:
    SUB = "SUB"
    SUBSCRIBE = 6
    RCVHWM = 24
    RCVTIMEO = 27

    class Again(Exception):
        pass

    class ContextTerminated(Exception):
        pass

    Context = type("Context", (), {})


def _patch_zmq(monkeypatch: pytest.MonkeyPatch, context: _FakeContext) -> None:
    """Install the fake pyzmq into sys.modules so the adapter's lazy import
    picks it up. The adapter calls `zmq.Context.instance()`, so we need to
    expose `instance` returning our fake context."""
    import sys
    import types

    fake_module = types.ModuleType("zmq")
    fake_module.SUB = _FakeZmq.SUB  # type: ignore[attr-defined]
    fake_module.SUBSCRIBE = _FakeZmq.SUBSCRIBE  # type: ignore[attr-defined]
    fake_module.RCVHWM = _FakeZmq.RCVHWM  # type: ignore[attr-defined]
    fake_module.RCVTIMEO = _FakeZmq.RCVTIMEO  # type: ignore[attr-defined]
    fake_module.Again = _FakeZmq.Again  # type: ignore[attr-defined]
    fake_module.ContextTerminated = _FakeZmq.ContextTerminated  # type: ignore[attr-defined]

    class _Ctx:
        @staticmethod
        def instance() -> _FakeContext:
            return context

    fake_module.Context = _Ctx  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "zmq", fake_module)


def _hash_payload(hex_string: str) -> bytes:
    """Build the payload bitcoind ZMQ would emit for a hash.

    bitcoind's zmqpublishnotifier.cpp byte-reverses the hash before publishing,
    so the wire payload is already in display order (matches `getblockhash`).
    """
    return bytes.fromhex(hex_string)


def test_subscribe_applies_socket_options_and_topics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    fake_ctx = _FakeContext()
    fake_socket = _FakeSocket(frames=[])
    fake_ctx.queue_socket(fake_socket)
    _patch_zmq(monkeypatch, fake_ctx)

    adapter = ChainEventAdapter("tcp://bitcoind:28332", receive_timeout_ms=250)
    adapter.subscribe()

    assert fake_socket.connected_to == "tcp://bitcoind:28332"
    assert (_FakeZmq.RCVHWM, 1000) in fake_socket.sock_options
    assert (_FakeZmq.RCVTIMEO, 250) in fake_socket.sock_options
    assert b"hashblock" in fake_socket.subscribed_topics
    assert b"hashtx" in fake_socket.subscribed_topics


def test_iter_messages_decodes_multipart_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each ZMQ message is [topic, payload, sequence-LE-uint32]."""
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    block_hash_display = (
        "00000000000000000000abcdef0000000000000000000000000000000000abcd"
    )
    tx_hash_display = (
        "1111111111111111111111111111111111111111111111111111111111111111"
    )
    assert len(block_hash_display) == 64
    assert len(tx_hash_display) == 64

    frames = [
        [b"hashblock", _hash_payload(block_hash_display), (7).to_bytes(4, "little")],
        [b"hashtx", _hash_payload(tx_hash_display), (8).to_bytes(4, "little")],
    ]
    fake_ctx = _FakeContext()
    fake_ctx.queue_socket(_FakeSocket(frames=frames))
    _patch_zmq(monkeypatch, fake_ctx)

    adapter = ChainEventAdapter("tcp://bitcoind:28332")
    adapter.subscribe()

    out = []
    for n in adapter.iter_messages():
        out.append(n)
        if len(out) == 2:
            adapter.close()
            break

    assert out[0].kind == "hashblock"
    assert out[0].sequence == 7
    assert out[0].hash_hex == block_hash_display
    assert out[1].kind == "hashtx"
    assert out[1].sequence == 8
    assert out[1].hash_hex == tx_hash_display


def test_iter_messages_ignores_short_multiparts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    frames = [
        [b"hashblock"],  # corrupt — no payload
        [b"hashtx", _hash_payload("a" * 64), (1).to_bytes(4, "little")],
    ]
    fake_ctx = _FakeContext()
    fake_ctx.queue_socket(_FakeSocket(frames=frames))
    _patch_zmq(monkeypatch, fake_ctx)

    adapter = ChainEventAdapter("tcp://bitcoind:28332")
    adapter.subscribe()
    out = []
    for n in adapter.iter_messages():
        out.append(n)
        adapter.close()

    assert len(out) == 1
    assert out[0].kind == "hashtx"


def test_iter_messages_returns_when_socket_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling close() from another conceptual thread must unblock the loop on
    the next recv (here simulated with an Again that lets the loop notice
    `_closed`)."""
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    fake_ctx = _FakeContext()
    socket = _FakeSocket(frames=[])  # always raises Again
    fake_ctx.queue_socket(socket)
    _patch_zmq(monkeypatch, fake_ctx)

    adapter = ChainEventAdapter("tcp://bitcoind:28332")
    adapter.subscribe()
    adapter.close()

    out = list(adapter.iter_messages())
    assert out == []
    assert socket.closed is True


def test_subscribe_required_before_iter(monkeypatch: pytest.MonkeyPatch) -> None:
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    adapter = ChainEventAdapter("tcp://bitcoind:28332")
    with pytest.raises(RuntimeError):
        next(iter(adapter.iter_messages()))


def test_subscribe_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    from tallykeep.adapters.chain_event_adapter import ChainEventAdapter

    fake_ctx = _FakeContext()
    fake_ctx.queue_socket(_FakeSocket(frames=[]))
    _patch_zmq(monkeypatch, fake_ctx)

    adapter = ChainEventAdapter("tcp://bitcoind:28332")
    adapter.subscribe()
    # Second call must not need a second queued socket.
    adapter.subscribe()
    assert len(fake_ctx.sockets) == 1
