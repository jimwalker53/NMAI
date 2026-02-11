"""Cron schedule management for connector instances.

Provides validation, parsing, and next-run-time computation for standard
5-field cron expressions (minute hour day_of_month month day_of_week).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Each field allows: *, digits, ranges (1-5), steps (*/5), lists (1,3,5)
_CRON_FIELD_RE = re.compile(
    r"^(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?(,(\*|[0-9]+(-[0-9]+)?)(/[0-9]+)?)*$"
)

_FIELD_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day": (1, 31),
    "month": (1, 12),
    "day_of_week": (0, 6),
}


def validate_cron(expression: str) -> bool:
    """Return ``True`` if *expression* is a valid 5-field cron expression.

    Does basic structural and range validation.
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        return False

    field_names = ["minute", "hour", "day", "month", "day_of_week"]
    for part, field_name in zip(parts, field_names):
        if not _CRON_FIELD_RE.match(part):
            return False

        min_val, max_val = _FIELD_RANGES[field_name]
        # Extract all numeric values for range checking
        for segment in part.split(","):
            # Strip step suffix (e.g. "*/5" -> "*", "1-5/2" -> "1-5")
            base = segment.split("/")[0]
            if base == "*":
                continue
            if "-" in base:
                try:
                    lo, hi = base.split("-", 1)
                    lo_int, hi_int = int(lo), int(hi)
                    if lo_int < min_val or hi_int > max_val or lo_int > hi_int:
                        return False
                except ValueError:
                    return False
            else:
                try:
                    val = int(base)
                    if val < min_val or val > max_val:
                        return False
                except ValueError:
                    return False

    return True


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_cron_parts(expression: str) -> dict[str, str]:
    """Parse a 5-field cron expression into a dict suitable for APScheduler's
    ``CronTrigger``.

    Returns a dict with keys: ``minute``, ``hour``, ``day``, ``month``,
    ``day_of_week``.

    Raises
    ------
    ValueError
        If the expression does not have exactly 5 fields.
    """
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression '{expression}': expected 5 fields, got {len(parts)}"
        )
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


# ---------------------------------------------------------------------------
# Next Run Time
# ---------------------------------------------------------------------------

def next_run_time(expression: str) -> datetime:
    """Compute the next run time for the given cron expression relative to now.

    Uses APScheduler's ``CronTrigger`` internally to compute an accurate
    next-fire time.

    Raises
    ------
    ValueError
        If the expression is invalid or APScheduler cannot compute a next fire
        time.
    """
    from apscheduler.triggers.cron import CronTrigger

    cron_kwargs = parse_cron_parts(expression)
    trigger = CronTrigger(**cron_kwargs, timezone="UTC")
    now = datetime.now(timezone.utc)
    next_time = trigger.get_next_fire_time(None, now)
    if next_time is None:
        raise ValueError(
            f"Cannot compute next run time for cron expression '{expression}'"
        )
    return next_time
