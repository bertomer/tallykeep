"""Worker entry point.

Spec module 01: a single Python codebase with two entry points (backend, worker).
The worker runs three kinds of components: listeners, schedulers, subscribers.

This module is a stub for M0 — it stays alive so the Compose service is healthy and
later milestones can register components without changing the entry point.
"""

from __future__ import annotations

import signal
import sys
import time
from types import FrameType


_running = True


def _handle_signal(signum: int, frame: FrameType | None) -> None:
    global _running
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # Component registry placeholder — listeners, schedulers, subscribers register here
    # in subsequent milestones (M2 onwards).
    print("tallykeep worker: starting (M0 stub — no components registered)", flush=True)

    while _running:
        time.sleep(1)

    print("tallykeep worker: shutting down", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
