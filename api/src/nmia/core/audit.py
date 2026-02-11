"""Audit logging utility for recording user actions."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from nmia.core.models import AuditLog


def log_action(
    db: Session,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an audit log entry and commit it to the database.

    Parameters
    ----------
    db:
        Active database session.
    user_id:
        The ID of the user performing the action, or ``None`` for system actions.
    action:
        A short description of the action (e.g. ``"create"``, ``"update"``,
        ``"delete"``, ``"login"``).
    resource_type:
        The type of resource affected (e.g. ``"enclave"``, ``"connector"``,
        ``"user"``).
    resource_id:
        The unique identifier (usually a UUID string) of the affected resource.
    details:
        Optional JSON-serialisable dict with extra context about the action.

    Returns
    -------
    AuditLog
        The newly created audit log entry.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=details,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
