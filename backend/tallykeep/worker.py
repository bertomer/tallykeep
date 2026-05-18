"""Worker entry point.

Spec module 01: a single Python codebase with two entry points (backend, worker).
The worker runs three kinds of components: listeners, schedulers, subscribers.

Components and their lock-state behavior:
  - ChainListener          — always on; lock-independent.
  - AuditReconciler        — always on; lock-independent.
  - CategorizerSuggester   — always on; lock-independent.
  - SweepEngine            — always on; lock-independent.
  - CustodialReconciler    — always on; lock-independent.
  - SelfCustodyPoller      — always on; lock-independent.
  - CustodialPollScheduler — always on; emits poll_tick, no lock check.
  - CustodialPoller        — always on; dispatches HTTP to backend; drops 423 silently.
  - RQ worker thread       — executes one_shot_custodial_poll jobs from the queue.
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from datetime import timedelta
from types import FrameType

from tallykeep.adapters.node_adapter import NodeAdapter
from tallykeep.configuration import get_settings
from tallykeep.infrastructure.database import get_session_factory
from tallykeep.infrastructure.event_bus import EventBus, RedisEventBus
from tallykeep.infrastructure.event_emission import AuditReconciler
from tallykeep.workers.listeners.chain_listener import ChainListener
from tallykeep.workers.schedulers.custodial_poll_scheduler import CustodialPollScheduler
from tallykeep.workers.schedulers.self_custody_poller import SelfCustodyPoller
from tallykeep.workers.subscribers.categorizer_suggester import CategorizerSuggester
from tallykeep.workers.subscribers.custodial_poller import CustodialPoller
from tallykeep.workers.subscribers.custodial_reconciler import CustodialReconciler
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


def _start_rq_worker_thread(redis_url: str) -> threading.Thread | None:
    """Start a SimpleWorker thread that consumes the tallykeep RQ queue."""
    try:
        import redis as redis_lib
        from rq import Queue as RQQueue, SimpleWorker

        class _NoDeathPenalty:
            # SIGALRM-based timeout enforcer; not usable outside the main thread.
            def __init__(self, *args: object, **kwargs: object) -> None: pass
            def __enter__(self) -> "_NoDeathPenalty": return self
            def __exit__(self, *args: object) -> None: pass

        class _DaemonSimpleWorker(SimpleWorker):
            death_penalty_class = _NoDeathPenalty  # type: ignore[assignment]

            def _install_signal_handlers(self) -> None:
                pass

        rq_redis = redis_lib.Redis.from_url(redis_url, decode_responses=False)
        rq_queue = RQQueue(name="tallykeep", connection=rq_redis)

        def _worker_loop() -> None:
            worker = _DaemonSimpleWorker([rq_queue], connection=rq_redis)
            # burst=False: run forever, processing jobs as they arrive.
            worker.work(burst=False, with_scheduler=False)

        thread = threading.Thread(target=_worker_loop, name="RQWorker", daemon=True)
        thread.start()
        logger.info("worker: RQWorker thread started (queue=tallykeep)")
        return thread
    except Exception:  # noqa: BLE001
        logger.exception("worker: failed to start RQWorker thread")
        return None


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    settings = get_settings()

    bus: EventBus | None = None
    reconciler: AuditReconciler | None = None
    chain_listener: ChainListener | None = None
    categorizer: CategorizerSuggester | None = None
    sweep_engine: SweepEngine | None = None
    custodial_reconciler: CustodialReconciler | None = None
    self_custody_poller: SelfCustodyPoller | None = None
    custodial_scheduler: CustodialPollScheduler | None = None
    custodial_poller: CustodialPoller | None = None
    node: NodeAdapter | None = None
    reconciler_interval_seconds = 30  # how often to scan for unacked events

    # Best-effort start. Workers tolerate degraded environments.
    if settings.redis_url:
        try:
            bus = RedisEventBus(settings.redis_url)
            logger.info("worker: connected to Redis at %s", settings.redis_url)
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to connect to Redis")

    if bus is not None and settings.database_url:
        try:
            session_factory = get_session_factory()
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
            custodial_reconciler = CustodialReconciler(
                bus=bus, session_factory=get_session_factory()
            )
            custodial_reconciler.start()
            logger.info("worker: CustodialReconciler registered")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start CustodialReconciler")
            custodial_reconciler = None

    if bus is not None and settings.database_url:
        try:
            custodial_scheduler = CustodialPollScheduler(
                session_factory=get_session_factory(),
                bus=bus,
            )
            custodial_scheduler.start()
            logger.info("worker: CustodialPollScheduler started")
        except Exception:  # noqa: BLE001
            logger.exception("worker: failed to start CustodialPollScheduler")
            custodial_scheduler = None

    if bus is not None and settings.database_url and settings.backend_url:
        try:
            custodial_poller = CustodialPoller(
                bus=bus,
                session_factory=get_session_factory(),
                backend_url=settings.backend_url,
            )
            custodial_poller.start()
            logger.info(
                "worker: CustodialPoller started (orchestrator, backend=%s)",
                settings.backend_url,
            )
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

    # RQ worker thread — executes one_shot_custodial_poll jobs from the queue.
    if settings.redis_url:
        _start_rq_worker_thread(settings.redis_url)

    last_reconcile = 0.0
    logger.info(
        "worker: started (bus=%s, reconciler=%s, chain_listener=%s, categorizer=%s, "
        "sweep_engine=%s, custodial_reconciler=%s, self_custody_poller=%s, "
        "custodial_scheduler=%s, custodial_poller=%s)",
        "redis" if bus else "none",
        "on" if reconciler else "off",
        "on" if chain_listener else "off",
        "on" if categorizer else "off",
        "on" if sweep_engine else "off",
        "on" if custodial_reconciler else "off",
        "on" if self_custody_poller else "off",
        "on" if custodial_scheduler else "off",
        "on" if custodial_poller else "off",
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

    if custodial_poller is not None:
        try:
            custodial_poller.stop()
        except Exception:  # noqa: BLE001
            pass

    if custodial_scheduler is not None:
        try:
            custodial_scheduler.stop()
        except Exception:  # noqa: BLE001
            pass

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

    if custodial_reconciler is not None:
        try:
            custodial_reconciler.stop()
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
