"""Enclave management endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import Enclave
from nmia.auth.models import User
from nmia.auth.rbac import (
    get_current_user,
    get_user_enclaves,
    require_enclave_access,
    require_role,
)
from nmia.enclaves.schemas import EnclaveCreate, EnclaveOut, EnclaveUpdate

router = APIRouter(prefix="/api/v1/enclaves", tags=["enclaves"])


@router.get("/", response_model=list[EnclaveOut])
def list_enclaves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Enclave]:
    """Return the enclaves visible to the current user.

    Admins see every enclave; other users see only those they are assigned to.
    """
    enclave_ids = get_user_enclaves(current_user, db)
    if not enclave_ids:
        return []
    return db.query(Enclave).filter(Enclave.id.in_(enclave_ids)).order_by(Enclave.name).all()


@router.post("/", response_model=EnclaveOut, status_code=status.HTTP_201_CREATED)
def create_enclave(
    body: EnclaveCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Enclave:
    """Create a new enclave (admin only)."""
    existing = db.query(Enclave).filter(Enclave.name == body.name).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Enclave with name '{body.name}' already exists",
        )

    enclave = Enclave(name=body.name, description=body.description)
    db.add(enclave)
    db.commit()
    db.refresh(enclave)
    return enclave


@router.get("/{enclave_id}", response_model=EnclaveOut)
def get_enclave(
    enclave_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Enclave:
    """Get a single enclave's details (must have access)."""
    require_enclave_access(enclave_id, current_user, db)

    enclave = db.query(Enclave).filter(Enclave.id == enclave_id).first()
    if enclave is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enclave not found",
        )
    return enclave


@router.put("/{enclave_id}", response_model=EnclaveOut)
def update_enclave(
    enclave_id: UUID,
    body: EnclaveUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Enclave:
    """Update an enclave (admin only)."""
    enclave = db.query(Enclave).filter(Enclave.id == enclave_id).first()
    if enclave is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enclave not found",
        )

    if body.name is not None:
        duplicate = (
            db.query(Enclave)
            .filter(Enclave.name == body.name, Enclave.id != enclave_id)
            .first()
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Enclave with name '{body.name}' already exists",
            )
        enclave.name = body.name

    if body.description is not None:
        enclave.description = body.description

    db.commit()
    db.refresh(enclave)
    return enclave


@router.delete("/{enclave_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_enclave(
    enclave_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Response:
    """Delete an enclave (admin only)."""
    enclave = db.query(Enclave).filter(Enclave.id == enclave_id).first()
    if enclave is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enclave not found",
        )

    db.delete(enclave)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
