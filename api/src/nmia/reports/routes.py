"""Reporting endpoints for certificate expiry and orphaned identities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import Identity
from nmia.auth.models import User
from nmia.auth.rbac import get_current_user, get_user_enclaves
from nmia.reports.schemas import ExpiringCertReport, OrphanedIdentityReport

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/expiring", response_model=list[ExpiringCertReport])
def expiring_certificates(
    days: int = Query(default=90, ge=1, le=3650),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return certificates expiring within the specified number of *days*.

    Only identities of type ``cert`` whose ``normalized_data.not_after``
    falls within the window are returned.  Results are sorted ascending by
    ``days_remaining`` (i.e. soonest-to-expire first).
    """
    accessible_enclaves = get_user_enclaves(current_user, db)
    if not accessible_enclaves:
        return []

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=days)

    identities = (
        db.query(Identity)
        .filter(
            Identity.enclave_id.in_(accessible_enclaves),
            Identity.identity_type == "cert",
        )
        .all()
    )

    results: list[dict] = []
    for ident in identities:
        normalized = ident.normalized_data or {}
        not_after_raw = normalized.get("not_after")
        if not_after_raw is None:
            continue

        # Parse the not_after timestamp
        try:
            if isinstance(not_after_raw, str):
                # Handle ISO format and common variants
                not_after_str = not_after_raw.replace("Z", "+00:00")
                not_after = datetime.fromisoformat(not_after_str)
            elif isinstance(not_after_raw, (int, float)):
                not_after = datetime.fromtimestamp(not_after_raw, tz=timezone.utc)
            else:
                continue
        except (ValueError, TypeError, OSError):
            continue

        # Ensure timezone-aware
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)

        # Only include certs expiring within the window
        if not_after > cutoff:
            continue

        days_remaining = max(0, (not_after - now).days)

        results.append(
            {
                "identity_id": ident.id,
                "display_name": ident.display_name,
                "enclave_id": ident.enclave_id,
                "not_after": not_after,
                "days_remaining": days_remaining,
                "risk_score": ident.risk_score,
            }
        )

    # Sort by days_remaining ascending (soonest expiry first)
    results.sort(key=lambda r: r["days_remaining"])
    return results


@router.get("/orphaned", response_model=list[OrphanedIdentityReport])
def orphaned_identities(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Return identities that have no ``owner`` or no ``linked_system``.

    Results are filtered by the caller's enclave access and ordered by
    ``risk_score`` descending (highest risk first).
    """
    accessible_enclaves = get_user_enclaves(current_user, db)
    if not accessible_enclaves:
        return []

    from sqlalchemy import or_

    identities = (
        db.query(Identity)
        .filter(
            Identity.enclave_id.in_(accessible_enclaves),
            or_(
                Identity.owner.is_(None),
                Identity.owner == "",
                Identity.linked_system.is_(None),
                Identity.linked_system == "",
            ),
        )
        .order_by(Identity.risk_score.desc())
        .all()
    )

    results: list[dict] = []
    for ident in identities:
        results.append(
            {
                "identity_id": ident.id,
                "display_name": ident.display_name,
                "enclave_id": ident.enclave_id,
                "identity_type": ident.identity_type,
                "owner": ident.owner,
                "linked_system": ident.linked_system,
                "risk_score": ident.risk_score,
            }
        )

    return results
