"""bitcoind ZeroMQ adapter — spec module 01 / 05.

Anti-corruption layer for live chain events. The ChainListener (workers/) drives
this adapter; the adapter does no domain work, just translates ZMQ frames into
typed `ChainNotification` records.

bitcoind's ZMQ topics relevant to v1:
  - `hashblock`   — 32-byte block hash on each new block
  - `hashtx`      — 32-byte tx hash on each mempool acceptance / block-confirmed tx
  - `rawblock`    — full block bytes (we don't decode here; we'd refetch via RPC)
  - `rawtx`       — full transaction bytes (same — refetch via RPC for the decoded view)

We subscribe to the *hash* topics by default. The hash is enough to drive the
listener: the listener fetches the decoded form via NodeAdapter.get_raw_transaction
or get_block, which gives us a richer, well-typed view than parsing the raw
bytes by hand and keeps this adapter tiny.

The adapter exposes a blocking `iter_messages()` generator. The caller polls it
on a worker thread; calling `close()` (or letting the context manager exit)
unblocks the generator and shuts the socket down.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChainNotification:
    """One ZMQ message from bitcoind, translated into our shape.

    `kind` is the bitcoind topic name (`hashblock`, `hashtx`, `rawblock`,
    `rawtx`). `payload` is the bytes of the first frame after the topic; for
    the hash topics this is the 32-byte big-endian hash, for the raw topics
    it's the serialized object.

    `sequence` is bitcoind's per-topic monotonic counter (final 4-byte LE
    frame). It lets a listener detect dropped messages — bitcoind sends every
    update to every subscriber, so a gap means our reader couldn't keep up.
    """

    kind: str
    payload: bytes
    sequence: int

    @property
    def hash_hex(self) -> str:
        """For hashblock/hashtx, the payload as a hex string in display order
        (matching what `getblockhash` / `getrawtransaction` return).

        bitcoind's zmqpublishnotifier.cpp already byte-reverses the hash before
        publishing (so the ZMQ payload is in display / big-endian order).
        We just .hex() it directly — no further reversal.
        """
        if len(self.payload) != 32:
            raise ValueError(
                f"hash_hex requires a 32-byte payload, got {len(self.payload)}"
            )
        return self.payload.hex()


class ChainEventAdapter:
    """Subscribes to bitcoind ZeroMQ topics.

    Lifecycle: `subscribe()` opens the socket and joins each topic. `iter_messages()`
    yields notifications until `close()` is called from another thread. The adapter
    is designed for a single reader; multiple concurrent iter_messages() calls are
    not supported.

    pyzmq is imported lazily so unit tests that don't touch ZMQ don't pay the
    import cost.
    """

    _DEFAULT_TOPICS: tuple[str, ...] = ("hashblock", "hashtx")

    def __init__(
        self,
        endpoint: str,
        *,
        topics: tuple[str, ...] | None = None,
        receive_timeout_ms: int = 1000,
    ) -> None:
        if not endpoint:
            raise ValueError("endpoint is required")
        self._endpoint = endpoint
        self._topics = tuple(topics) if topics else self._DEFAULT_TOPICS
        self._receive_timeout_ms = receive_timeout_ms
        self._context: Any = None
        self._socket: Any = None
        self._closed = False

    def subscribe(self) -> None:
        """Open the ZMQ socket and subscribe to the configured topics.

        Idempotent within a single instance: a second call is a no-op.
        """
        if self._socket is not None:
            return

        import zmq

        self._context = zmq.Context.instance()
        self._socket = self._context.socket(zmq.SUB)
        # bitcoind only ever has a few subscribers and emits at modest rates;
        # a small high-water mark (1k messages) is more than enough and avoids
        # unbounded memory growth if the consumer stalls.
        self._socket.setsockopt(zmq.RCVHWM, 1000)
        # RCVTIMEO lets recv() return EAGAIN periodically so the read loop
        # can check its shutdown flag without blocking forever.
        self._socket.setsockopt(zmq.RCVTIMEO, self._receive_timeout_ms)
        # Connect AFTER setting socket opts (RCVTIMEO must be set pre-connect
        # on some pyzmq versions to take effect on the first recv).
        self._socket.connect(self._endpoint)
        for topic in self._topics:
            self._socket.setsockopt(zmq.SUBSCRIBE, topic.encode("ascii"))
        logger.info(
            "ChainEventAdapter: subscribed to %s on %s",
            ",".join(self._topics),
            self._endpoint,
        )

    def iter_messages(self) -> Iterator[ChainNotification]:
        """Yield notifications until the adapter is closed.

        Each ZMQ message from bitcoind is a 3-frame multipart:
          [topic_bytes, payload_bytes, 4-byte LE sequence]

        Receive failures other than timeout are logged and swallowed; the
        loop continues until close() is called. This matches Redis-bus
        semantics where one bad message can't kill the subscriber.

        The socket is closed *inside this generator's finally* — pyzmq sockets
        are not thread-safe and closing one from another thread while it is
        blocked in recv aborts the process. close() only sets the flag; we
        do the actual teardown here on the read thread.
        """
        if self._socket is None:
            raise RuntimeError("subscribe() must be called before iter_messages()")

        import zmq

        try:
            if self._closed:
                # Honour close()-before-iterate so the socket still gets torn
                # down via the finally below.
                return
            while not self._closed:
                socket = self._socket
                if socket is None:
                    return
                try:
                    frames = socket.recv_multipart()
                except zmq.Again:
                    # No message within RCVTIMEO — loop back to check _closed.
                    continue
                except zmq.ContextTerminated:
                    return
                except Exception:  # noqa: BLE001
                    logger.exception("ChainEventAdapter: recv_multipart failed")
                    continue

                if len(frames) < 2:
                    logger.warning(
                        "ChainEventAdapter: dropping message with %d frames",
                        len(frames),
                    )
                    continue

                topic = frames[0].decode("ascii", errors="replace")
                payload = frames[1]
                sequence = (
                    int.from_bytes(frames[2], "little") if len(frames) > 2 else 0
                )
                yield ChainNotification(
                    kind=topic, payload=payload, sequence=sequence
                )
        finally:
            self._teardown_socket()

    def close(self) -> None:
        """Signal the read loop to stop.

        Safe to call from any thread. The socket is closed inside the read
        thread's finally clause — closing pyzmq sockets cross-thread aborts.
        """
        self._closed = True

    def _teardown_socket(self) -> None:
        socket = self._socket
        self._socket = None
        if socket is not None:
            try:
                socket.close(linger=0)
            except Exception:  # noqa: BLE001 — best-effort during shutdown
                pass

    def __enter__(self) -> "ChainEventAdapter":
        self.subscribe()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


__all__ = ["ChainEventAdapter", "ChainNotification"]
