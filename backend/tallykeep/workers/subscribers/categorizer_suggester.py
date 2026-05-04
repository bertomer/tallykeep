"""CategorizerSuggester — spec module 05.

Subscribes to `ledger_entry.requires_categorization` events. For each
event, runs the heuristic categorizer (services/categorizer_service.py)
and, if a suggestion is produced, persists it as
`ledger_entry.suggested_category`. The user's binding `category` is
never touched here; that only changes via the explicit PATCH endpoint.

Re-emits `ledger_entry.requires_categorization` after writing the
suggestion so the LiveUpdateBridge (M9) can push the updated entry to
the SSE clients without polling.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from tallykeep.infrastructure.event_bus import Event, EventBus, Subscription
from tallykeep.services.categorizer_service import suggest_category


logger = logging.getLogger(__name__)


class CategorizerSuggester:
    def __init__(
        self,
        *,
        bus: EventBus,
        session_factory: sessionmaker[Session],
    ) -> None:
        self._bus = bus
        self._session_factory = session_factory
        self._subscription: Subscription | None = None

    def start(self) -> None:
        if self._subscription is not None:
            return
        self._subscription = self._bus.subscribe(
            ["ledger_entry.requires_categorization"],
            self._on_event,
        )
        logger.info("CategorizerSuggester: subscribed")

    def stop(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None
        logger.info("CategorizerSuggester: unsubscribed")

    def _on_event(self, event: Event) -> None:
        entry_id_raw = event.payload.get("ledger_entry_id")
        if entry_id_raw is None:
            return
        try:
            entry_id = UUID(str(entry_id_raw))
        except (TypeError, ValueError):
            logger.warning(
                "CategorizerSuggester: ignoring event with bad ledger_entry_id=%r",
                entry_id_raw,
            )
            return

        suggestion = None
        try:
            with self._session_factory() as session:
                suggestion = suggest_category(session, entry_id)
                session.commit()
        except Exception:  # noqa: BLE001 — one bad entry can't kill the loop
            logger.exception(
                "CategorizerSuggester: suggest_category failed for %s", entry_id
            )
            return

        if suggestion is not None:
            # Re-fire the same topic with the suggestion populated so the
            # LiveUpdateBridge / SSE pickups the refresh. No new topic so
            # the same UI listener handles both states.
            self._bus.publish(
                "ledger_entry.requires_categorization",
                {
                    "ledger_entry_id": str(entry_id),
                    "suggested_category": suggestion.value,
                },
            )


__all__ = ["CategorizerSuggester"]
