"""Structured logging setup for the NMIA application.

Call ``setup_logging()`` once at application startup (e.g. in ``main.py`` or
the worker entry point) to configure the Python logging subsystem with a
consistent format and level.
"""

from __future__ import annotations

import logging
import sys


def setup_logging(
    level: int | str = logging.INFO,
    fmt: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
) -> None:
    """Configure the root logger with the given level and format.

    Parameters
    ----------
    level:
        Logging level (default ``INFO``).  Accepts both integer constants
        (``logging.DEBUG``) and string names (``"DEBUG"``).
    fmt:
        Format string for log messages.
    datefmt:
        Date/time format string.
    """
    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )

    # Quieten noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    A thin convenience wrapper so callers do not need to import the
    ``logging`` module directly::

        from nmia.util.logging import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(name)
