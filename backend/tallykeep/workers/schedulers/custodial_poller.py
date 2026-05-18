"""CustodialPoller — pure interval scheduler for custodial provider polls.

Publishes system.custodial.poll_requested for each active provider whose
polling interval has elapsed. The actual poll cycle (ccxt calls, DB writes,
SSE events) runs in the backend's CustodialPollHandler which subscribes to
those events.
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import EventBus
from tallykeep.repositories import custodial_provider as cp_repo


logger = logging.getLogger(__name__)


class CustodialPoller:
    """Background thread that publishes poll requests for each active provider."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        bus: EventBus,
        interval_seconds: int = 60,
    ) -> None:
        self._session_factory = session_factory
        self._bus = bus
        self._interval = interval_seconds
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="CustodialPoller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
            self._thread = None

    def _run(self) -> None:
        logger.info("CustodialPoller: started (interval=%ds)", self._interval)
        while not self._stop_event.is_set():
            try:
                self._poll_once()
            except Exception:  # noqa: BLE001
                logger.exception("CustodialPoller: poll_once failed")
            self._stop_event.wait(timeout=self._interval)
        logger.info("CustodialPoller: stopped")

    def _poll_once(self) -> None:
        with self._session_factory() as session:
            providers = cp_repo.list_active(session)

        now = datetime.now(UTC)
        for provider in providers:
            if provider.last_polled_at is not None:
                elapsed = (now - provider.last_polled_at).total_seconds()
                if elapsed < provider.polling_interval_seconds:
                    continue
            self._bus.publish(
                "system.custodial.poll_requested",
                {"provider_id": str(provider.id)},
            )
            logger.info("CustodialPoller: requested poll for provider %s", provider.id)


__all__ = ["CustodialPoller"]
