"""Worker entry point.

Spec module 01: a single Python codebase with two entry points (backend, worker).
The worker runs three kinds of components: listeners, schedulers, subscribers.

M2 wires the EventBus and the AuditReconciler scheduler. Listeners and the
domain-specific subscribers (CustodialPoller, SweepEngine, CategorizerSuggester,
ChainListener, LiveUpdateBridge) land with their owning milestones (M5+).
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import timedelta
from types import FrameType

from tallykeep.adapters.node_adapter import NodeAdapter
from tallykeep.configuration import get_settings
from tallykeep.infrastructure.database import get_session_factory
from tallykeep.infrastructure.event_bus import EventBus, RedisEventBus
from tallykeep.infrastructure.event_emission import AuditReconciler
from tallykeep.infrastructure.secrets import EncryptedDatabaseSecretStore
from tallykeep.workers.listeners.chain_listener import ChainListener
from tallykeep.workers.schedulers.custodial_poller import CustodialPoller
from tallykeep.workers.schedulers.self_custody_poller import SelfCustodyPoller
from tallykeep.workers.subscribers.categorizer_suggester import CategorizerSuggester
from tallykeep.workers.subscribers.sweep_engine import SweepEngine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger("tallykeep.worker")


_running = True


def _handle_signal(signum: int, frame: FrameType | None) -> None:
    global _running
    logger.info("worker: received signal %d, shutting down", signum)
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    settings = get_settings()

    bus: EventBus | None = None
    reconciler: AuditReconciler | None = None
    chain_listener: ChainListener | None = None
    categorizer: CategorizerSuggester | None = None
    sweep_engine: SweepEngine | None = None
    custodial_poller: CustodialPoller | None = None
    self_custody_poller: SelfCustodyPoller | None = None
    node: NodeAdapter | None = None
    reconciler_interval_seconds = 30  # how often to scan for unacked events

    # Best-effort start. Workers tolerate degraded environments — the audit
    # reconciler simply runs no-ops when its dependencies are missing.
    if settings.redis_url:
        try:
            bus = RedisEventBus(settings.redis_url)
            logger.info("worker: connected to Redis at %s", settings.redis_url)
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to connect to Redis")

    if bus is not None and settings.database_url:
        try:
            session_factory = get_session_factory()
            # Conservative grace period in production: events older than 5 min
            # without acknowledgement are considered lost. Tunable later via
            # runtime_configuration.
            reconciler = AuditReconciler(
                bus=bus,
                session_factory=session_factory,
                grace_period=timedelta(minutes=5),
            )
            logger.info("worker: AuditReconciler registered")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to set up AuditReconciler")

    if bus is not None and settings.database_url:
        try:
            categorizer = CategorizerSuggester(
                bus=bus, session_factory=get_session_factory()
            )
            categorizer.start()
            logger.info("worker: CategorizerSuggester registered")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start CategorizerSuggester")
            categorizer = None

    if bus is not None and settings.database_url:
        try:
            sweep_engine = SweepEngine(bus=bus, session_factory=get_session_factory())
            sweep_engine.start()
            logger.info("worker: SweepEngine registered")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start SweepEngine")
            sweep_engine = None

    if bus is not None and settings.database_url:
        try:
            secret_store = EncryptedDatabaseSecretStore(get_session_factory())
            custodial_poller = CustodialPoller(
                session_factory=get_session_factory(),
                secret_store=secret_store,
                bus=bus,
                interval_seconds=300,
            )
            custodial_poller.start()
            logger.info("worker: CustodialPoller started (interval=300s)")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start CustodialPoller")
            custodial_poller = None

    if (
        bus is not None
        and settings.database_url
        and settings.bitcoind_rpc_url
    ):
        try:
            node = NodeAdapter(settings.bitcoind_rpc_url, timeout_seconds=30.0)
            self_custody_poller = SelfCustodyPoller(
                session_factory=get_session_factory(),
                node=node,
                bus=bus,
                interval_seconds=900,
            )
            self_custody_poller.start()
            logger.info("worker: SelfCustodyPoller started (interval=900s)")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start SelfCustodyPoller")
            self_custody_poller = None

    if (
        bus is not None
        and settings.database_url
        and settings.bitcoind_zmq_endpoint
        and settings.bitcoind_rpc_url
    ):
        try:
            if node is None:
                node = NodeAdapter(settings.bitcoind_rpc_url, timeout_seconds=30.0)
            session_factory = get_session_factory()
            chain_listener = ChainListener(
                zmq_endpoint=settings.bitcoind_zmq_endpoint,
                node=node,
                bus=bus,
                session_factory=session_factory,
            )
            chain_listener.start()
            logger.info(
                "worker: ChainListener started on %s", settings.bitcoind_zmq_endpoint
            )
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start ChainListener")
            chain_listener = None

    last_reconcile = 0.0
    logger.info(
        "worker: started (bus=%s, reconciler=%s, chain_listener=%s, categorizer=%s, "
        "sweep_engine=%s, custodial_poller=%s, self_custody_poller=%s)",
        "redis" if bus else "none",
        "on" if reconciler else "off",
        "on" if chain_listener else "off",
        "on" if categorizer else "off",
        "on" if sweep_engine else "off",
        "on" if custodial_poller else "off",
        "on" if self_custody_poller else "off",
    )

    while _running:
        now = time.time()
        if reconciler is not None and now - last_reconcile >= reconciler_interval_seconds:
            try:
                count = reconciler.run_once()
                if count:
                    logger.info("worker: AuditReconciler re-emitted %d event(s)", count)
            except Exception:  # noqa: BLE001
                logger.exception("worker: AuditReconciler failed")
            last_reconcile = now
        time.sleep(1)

    if categorizer is not None:
        try:
            categorizer.stop()
        except Exception:  # noqa: BLE001
            pass

    if sweep_engine is not None:
        try:
            sweep_engine.stop()
        except Exception:  # noqa: BLE001
            pass

    if custodial_poller is not None:
        try:
            custodial_poller.stop()
        except Exception:  # noqa: BLE001
            pass

    if self_custody_poller is not None:
        try:
            self_custody_poller.stop()
        except Exception:  # noqa: BLE001
            pass

    if chain_listener is not None:
        try:
            chain_listener.stop()
        except Exception:  # noqa: BLE001
            pass

    if node is not None:
        try:
            node.close()
        except Exception:  # noqa: BLE001
            pass

    if bus is not None:
        try:
            bus.close()
        except Exception:  # noqa: BLE001
            pass

    logger.info("worker: shut down cleanly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
