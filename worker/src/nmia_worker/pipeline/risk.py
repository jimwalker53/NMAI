"""
Risk scoring pipeline.

Scores each Identity based on a set of heuristic rules that reflect
security hygiene and operational risk.

Scoring rules:
- No owner: +25
- No linked_system: +15
- Cert expired: +40, expiring < 30 d: +30, < 90 d: +15
- Cert missing SAN: +10
- Svc acct disabled: +10
- Svc acct password > 365 days old or never set: +20
- Cap at 100.0
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

# Import shared models (sys.path is set up by scheduler.py at import time)
from nmia.core.models import Identity  # noqa: E402

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def _parse_datetime(value: Any) -> datetime | None:
    """Best-effort parse of a datetime value from normalized_data.

    Supports ISO-format strings and already-parsed datetime objects.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Handle common ISO formats (replace trailing Z with UTC offset)
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except (ValueError, TypeError):
            pass
    return None


def score_risks(
    db: Session,
    enclave_id: UUID | None = None,
) -> int:
    """Score risk for each Identity.

    Parameters
    ----------
    db:
        An active SQLAlchemy session.
    enclave_id:
        If provided, only process identities scoped to this enclave.

    Returns
    -------
    int
        The number of identities whose risk score was changed.
    """
    query = db.query(Identity)
    if enclave_id is not None:
        query = query.filter(Identity.enclave_id == enclave_id)
    identities: list[Identity] = query.all()

    now = _utcnow()
    scored = 0

    for identity in identities:
        score = 0.0
        nd: dict[str, Any] = identity.normalized_data or {}

        # -- Common checks --
        if not identity.owner:
            score += 25.0
        if not identity.linked_system:
            score += 15.0

        # -- Cert-specific checks --
        if identity.identity_type == "cert":
            not_after = _parse_datetime(nd.get("not_after"))
            if not_after is not None:
                if not_after.tzinfo is None:
                    not_after = not_after.replace(tzinfo=timezone.utc)
                if not_after < now:
                    score += 40.0  # expired
                elif not_after < now + timedelta(days=30):
                    score += 30.0  # expiring within 30 days
                elif not_after < now + timedelta(days=90):
                    score += 15.0  # expiring within 90 days

            san_list = nd.get("san", [])
            if not san_list:
                score += 10.0

        # -- Service-account-specific checks --
        elif identity.identity_type == "svc_acct":
            enabled = nd.get("enabled", True)
            if not enabled:
                score += 10.0

            pwd_last_set = _parse_datetime(nd.get("password_last_set"))
            if pwd_last_set is None:
                # Password never set or unknown
                score += 20.0
            else:
                if pwd_last_set.tzinfo is None:
                    pwd_last_set = pwd_last_set.replace(tzinfo=timezone.utc)
                if pwd_last_set < now - timedelta(days=365):
                    score += 20.0

        # Cap at 100
        score = min(score, 100.0)

        if score != identity.risk_score:
            identity.risk_score = score
            scored += 1
            logger.debug(
                "score_risks: identity=%s risk_score=%.1f", identity.id, score
            )

    db.flush()
    logger.info(
        "score_risks: scored %d identities (enclave=%s)", scored, enclave_id
    )
    return scored
