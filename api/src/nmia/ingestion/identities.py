"""Identity management endpoints (enclave-scoped)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import Identity
from nmia.auth.models import User
from nmia.auth.rbac import (
    get_current_user,
    get_user_enclaves,
    require_enclave_access,
    require_enclave_role,
)
from nmia.ingestion.identity_schemas import IdentityOut, IdentityUpdate

router = APIRouter(prefix="/api/v1/identities", tags=["identities"])


@router.get("/", response_model=list[IdentityOut])
def list_identities(
    enclave_id: UUID | None = Query(default=None),
    identity_type: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    linked_system: str | None = Query(default=None),
    search: str | None = Query(default=None),
    min_risk: float | None = Query(default=None),
    max_risk: float | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Identity]:
    """List identities visible to the current user.

    Results are restricted to enclaves the caller has access to and can be
    further narrowed with optional query filters.
    """
    accessible_enclaves = get_user_enclaves(current_user, db)
    if not accessible_enclaves:
        return []

    query = db.query(Identity).filter(Identity.enclave_id.in_(accessible_enclaves))

    if enclave_id is not None:
        if enclave_id not in accessible_enclaves:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this enclave",
            )
        query = query.filter(Identity.enclave_id == enclave_id)

    if identity_type is not None:
        query = query.filter(Identity.identity_type == identity_type)

    if owner is not None:
        query = query.filter(Identity.owner == owner)

    if linked_system is not None:
        query = query.filter(Identity.linked_system == linked_system)

    if search is not None:
        query = query.filter(Identity.display_name.ilike(f"%{search}%"))

    if min_risk is not None:
        query = query.filter(Identity.risk_score >= min_risk)

    if max_risk is not None:
        query = query.filter(Identity.risk_score <= max_risk)

    return query.order_by(Identity.display_name).all()


@router.get("/{identity_id}", response_model=IdentityOut)
def get_identity(
    identity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Identity:
    """Get a single identity by ID (checks enclave access)."""
    identity = db.query(Identity).filter(Identity.id == identity_id).first()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not found",
        )

    require_enclave_access(identity.enclave_id, current_user, db)
    return identity


@router.put("/{identity_id}", response_model=IdentityOut)
def update_identity(
    identity_id: UUID,
    body: IdentityUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Identity:
    """Update an identity (assign owner, link system).

    Requires ``operator`` or ``admin`` role in the identity's enclave.
    """
    identity = db.query(Identity).filter(Identity.id == identity_id).first()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Identity not found",
        )

    require_enclave_role(identity.enclave_id, current_user, db, "operator", "admin")

    if body.owner is not None:
        identity.owner = body.owner
    if body.linked_system is not None:
        identity.linked_system = body.linked_system

    db.commit()
    db.refresh(identity)
    return identity
