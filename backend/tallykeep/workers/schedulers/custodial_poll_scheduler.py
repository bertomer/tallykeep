"""CustodialPollScheduler — heartbeat timer that emits poll ticks per active provider.

Runs on a configurable interval (default 600 s, range 60-3600 s) read from
`runtime_configuration.custodial_polling.interval_seconds`. On each tick it
iterates every active provider and publishes a `treasury.custodial.poll_tick`
event on the bus.

No lock-state check here: the gate is at the backend's internal endpoint, which
returns 423 when the secret store is locked and the worker's CustodialPoller
silently drops those 423 responses.

Topics emitted:
    treasury.custodial.poll_tick  — payload: { "provider_id": "<uuid>" }
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.repositories import custodial_provider as cp_repo


logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 600
_MIN_INTERVAL = 60
_MAX_INTERVAL = 3600


class CustodialPollScheduler:
    """Background thread that emits poll ticks for each active custodial provider."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        bus: EventBus,
    ) -> None:
        self._session_factory = session_factory
        self._bus = bus
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="CustodialPollScheduler", daemon=True
        )
        self._thread.start()
        logger.info("CustodialPollScheduler: started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("CustodialPollScheduler: stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            interval = self._read_interval()
            try:
                self._tick()
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPollScheduler: tick failed")
            self._stop_event.wait(timeout=interval)

    def _read_interval(self) -> int:
        try:
            from tallykeep.repositories.runtime_configuration import list_all

            with self._session_factory() as session:
                config = list_all(session)
            raw = config.get("custodial_polling.interval_seconds", _DEFAULT_INTERVAL)
            value = int(raw)
            return max(_MIN_INTERVAL, min(_MAX_INTERVAL, value))
        except Exception:  # noqa: BLE001
            return _DEFAULT_INTERVAL

    def _tick(self) -> None:
        with self._session_factory() as session:
            providers = cp_repo.list_active(session)

        for provider in providers:
            try:
                self._bus.publish(
                    "treasury.custodial.poll_tick",
                    {"provider_id": str(provider.id)},
                )
                logger.debug(
                    "CustodialPollScheduler: emitted poll_tick for provider %s", provider.id
                )
            except Exception:  # noqa: BLE001
                logger.warning(
                    "CustodialPollScheduler: failed to emit tick for provider %s", provider.id
                )


__all__ = ["CustodialPollScheduler"]
