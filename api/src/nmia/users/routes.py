"""User management endpoints (admin only)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import Enclave
from nmia.auth.models import Role, User, UserRoleEnclave
from nmia.auth.rbac import require_role
from nmia.auth.security import hash_password
from nmia.users.schemas import (
    RoleAssignment,
    UserCreate,
    UserOut,
    UserRoleEnclaveOut,
    UserUpdate,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> list[User]:
    """Return all users (admin only)."""
    return db.query(User).order_by(User.username).all()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Create a new user with a hashed password (admin only)."""
    existing = db.query(User).filter(User.username == body.username).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{body.username}' is already taken",
        )

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        email=body.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Get a single user by ID (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> User:
    """Update user fields (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if body.email is not None:
        user.email = body.email
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Response:
    """Soft-delete a user by setting is_active=False (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{user_id}/roles", response_model=UserRoleEnclaveOut, status_code=status.HTTP_201_CREATED)
def assign_role(
    user_id: UUID,
    body: RoleAssignment,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> UserRoleEnclave:
    """Assign a role to a user within an enclave (admin only).

    The request body contains ``role_name`` and ``enclave_id``.  The
    corresponding ``Role`` and ``Enclave`` records are looked up by name / id.
    """
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Validate role exists
    role = db.query(Role).filter(Role.name == body.role_name).first()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{body.role_name}' not found",
        )

    # Validate enclave exists
    enclave = db.query(Enclave).filter(Enclave.id == body.enclave_id).first()
    if enclave is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enclave not found",
        )

    # Check for duplicate assignment
    existing = (
        db.query(UserRoleEnclave)
        .filter(
            UserRoleEnclave.user_id == user_id,
            UserRoleEnclave.role_id == role.id,
            UserRoleEnclave.enclave_id == body.enclave_id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role assignment already exists",
        )

    assignment = UserRoleEnclave(
        user_id=user_id,
        role_id=role.id,
        enclave_id=body.enclave_id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/{user_id}/roles/{role_enclave_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_role(
    user_id: UUID,
    role_enclave_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Response:
    """Remove a specific role assignment from a user (admin only)."""
    assignment = (
        db.query(UserRoleEnclave)
        .filter(
            UserRoleEnclave.id == role_enclave_id,
            UserRoleEnclave.user_id == user_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found",
        )

    db.delete(assignment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
