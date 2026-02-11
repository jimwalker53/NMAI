"""
NMIA Worker entry point.

Starts the APScheduler-based worker process and blocks until a shutdown
signal (SIGINT / SIGTERM) is received.

Usage::

    python -m nmia_worker.main
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)

# Graceful-shutdown flag
_shutdown_requested = False


def _handle_signal(signum: int, frame: Any) -> None:
    """Signal handler for SIGINT / SIGTERM -- request graceful shutdown."""
    global _shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s -- shutting down gracefully...", sig_name)
    _shutdown_requested = True


def main() -> None:
    """Entry point for the NMIA worker process.

    Sets up logging, starts the scheduler, and blocks until a shutdown
    signal is received.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    logger.info("NMIA Worker starting...")

    # Register signal handlers
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Start the scheduler (import here so logging is configured first)
    from nmia_worker.scheduler import start_scheduler

    scheduler = start_scheduler()

    # Block until shutdown is requested
    try:
        while not _shutdown_requested:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupted -- shutting down...")
    finally:
        scheduler.shutdown(wait=True)
        logger.info("NMIA Worker stopped.")


if __name__ == "__main__":
    main()
