"""CustodialPoller — pure HTTP orchestrator for custodial poll cycles.

Subscribes to three event topics:

    treasury.custodial.poll_tick  — dispatch one POST poll-cycle for the named provider.
    system.unlocked               — catch-up burst: dispatch N parallel poll-cycles for
                                    all active providers (asyncio.gather-style via thread pool).
    system.locked                 — stop dispatching new cycles until next system.unlocked.

This component has NO ccxt dependency, NO adapter import, NO secret-store reference.
Its only outbound dependency is an httpx.Client that talks to the backend's
internal endpoint. The backend handles credential decryption and the ccxt calls.

On 423 Locked:  drop the cycle, log at DEBUG.
On 404:         log at INFO (provider was archived between tick and dispatch).
On other non-2xx: log at WARNING, continue.
On 200:         log at DEBUG.
"""

from __future__ import annotations

import concurrent.futures
import logging
import threading
from uuid import UUID

import httpx

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import Event, EventBus, Subscription
from tallykeep.repositories import custodial_provider as cp_repo


logger = logging.getLogger(__name__)


class CustodialPoller:
    """Worker-side orchestrator: dispatches HTTP calls to the backend poll-cycle endpoint."""

    def __init__(
        self,
        *,
        bus: EventBus,
        session_factory: sessionmaker[Session],
        backend_url: str,
    ) -> None:
        self._bus = bus
        self._session_factory = session_factory
        self._backend_url = backend_url.rstrip("/")
        self._http = httpx.Client(timeout=30.0)
        self._subscription: Subscription | None = None
        self._is_running = False
        # Threading event: set = dispatch enabled, clear = locked (dispatch suspended).
        self._dispatch_enabled = threading.Event()
        self._dispatch_enabled.set()

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        if self._is_running:
            return
        self._subscription = self._bus.subscribe(
            [
                "treasury.custodial.poll_tick",
                "system.unlocked",
                "system.locked",
            ],
            self._on_event,
        )
        self._is_running = True
        logger.info("CustodialPoller: started (orchestrator, no ccxt/secrets)")

    def stop(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None
        try:
            self._http.close()
        except Exception:  # noqa: BLE001
            pass
        self._is_running = False
        logger.info("CustodialPoller: stopped")

    # --- event dispatch -----------------------------------------------------------

    def _on_event(self, event: Event) -> None:
        topic = event.topic
        if topic == "system.locked":
            self._dispatch_enabled.clear()
            logger.info("CustodialPoller: dispatch suspended (system.locked)")
        elif topic == "system.unlocked":
            self._dispatch_enabled.set()
            logger.info("CustodialPoller: dispatch resumed — starting catch-up burst")
            threading.Thread(
                target=self._catch_up_burst,
                name="CustodialPoller-CatchupBurst",
                daemon=True,
            ).start()
        elif topic == "treasury.custodial.poll_tick":
            if not self._dispatch_enabled.is_set():
                return
            provider_id_raw = event.payload.get("provider_id")
            if provider_id_raw:
                threading.Thread(
                    target=self._dispatch_cycle,
                    args=(str(provider_id_raw),),
                    name=f"CustodialPoller-Tick-{str(provider_id_raw)[:8]}",
                    daemon=True,
                ).start()

    # --- catch-up burst -----------------------------------------------------------

    def _catch_up_burst(self) -> None:
        try:
            with self._session_factory() as session:
                providers = cp_repo.list_active(session)
        except Exception:  # noqa: BLE001
            logger.exception("CustodialPoller: catch-up burst failed to list providers")
            return

        if not providers:
            return

        logger.info(
            "CustodialPoller: catch-up burst dispatching %d provider(s)", len(providers)
        )
        provider_ids = [str(p.id) for p in providers]

        max_workers = max(1, len(provider_ids))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._dispatch_cycle, pid): pid for pid in provider_ids
            }
            concurrent.futures.wait(futures, timeout=60.0)

    # --- single cycle dispatch ---------------------------------------------------

    def _dispatch_cycle(self, provider_id: str) -> None:
        url = f"{self._backend_url}/api/v1/internal/custodial/{provider_id}/poll-cycle"
        try:
            resp = self._http.post(url)
        except httpx.RequestError as exc:
            logger.warning(
                "CustodialPoller: HTTP request failed for provider %s: %s", provider_id, exc
            )
            return

        if resp.status_code == 423:
            logger.debug(
                "CustodialPoller: backend locked for provider %s (423)", provider_id
            )
        elif resp.status_code == 404:
            logger.info(
                "CustodialPoller: provider %s not found or archived (404)", provider_id
            )
        elif resp.status_code != 200:
            logger.warning(
                "CustodialPoller: unexpected %d for provider %s",
                resp.status_code,
                provider_id,
            )
        else:
            logger.debug("CustodialPoller: cycle completed for provider %s", provider_id)


__all__ = ["CustodialPoller"]
