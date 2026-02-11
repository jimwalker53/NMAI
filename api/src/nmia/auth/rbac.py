"""FastAPI dependencies for authentication, RBAC, and enclave scoping."""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import Enclave
from nmia.auth.security import decode_access_token
from nmia.auth.models import Role, User, UserRoleEnclave

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT from the Authorization Bearer header and return the
    corresponding active ``User``, or raise 401.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str | None = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def _user_has_role(user: User, role_name: str) -> bool:
    """Return True if *user* holds *role_name* in any enclave."""
    for assignment in user.role_assignments:
        if assignment.role.name == role_name:
            return True
    return False


def _user_is_admin(user: User) -> bool:
    """Return True if the user holds the admin role in any enclave."""
    return _user_has_role(user, "admin")


def require_role(*allowed_roles: str) -> Callable:
    """Return a FastAPI dependency that raises 403 unless the current user
    holds at least one of *allowed_roles* in some enclave.
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        for assignment in current_user.role_assignments:
            if assignment.role.name in allowed_roles:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"One of the following roles is required: {', '.join(allowed_roles)}",
        )

    return _dependency


def get_user_enclaves(
    current_user: User,
    db: Session,
    role: str | None = None,
) -> list[UUID]:
    """Return a list of enclave IDs the *current_user* has access to.

    * If *role* is provided only enclaves where the user holds that specific
      role are returned.
    * Users with the ``admin`` role (in any enclave) get access to **all**
      enclaves.
    """
    if _user_is_admin(current_user):
        return [e.id for e in db.query(Enclave).all()]

    enclave_ids: list[UUID] = []
    for assignment in current_user.role_assignments:
        if role is None or assignment.role.name == role:
            enclave_ids.append(assignment.enclave_id)
    return list(set(enclave_ids))


def require_enclave_access(
    enclave_id: UUID,
    current_user: User,
    db: Session,
) -> None:
    """Raise 403 if *current_user* has no role in the enclave identified by
    *enclave_id*.  Admins are exempt.
    """
    if _user_is_admin(current_user):
        return

    has_access = any(
        str(assignment.enclave_id) == str(enclave_id)
        for assignment in current_user.role_assignments
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this enclave",
        )


def require_enclave_role(
    enclave_id: UUID,
    current_user: User,
    db: Session,
    *allowed_roles: str,
) -> None:
    """Raise 403 unless the user holds one of *allowed_roles* specifically in
    the given enclave.  Admins are always allowed.
    """
    if _user_is_admin(current_user):
        return

    for assignment in current_user.role_assignments:
        if (
            str(assignment.enclave_id) == str(enclave_id)
            and assignment.role.name in allowed_roles
        ):
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Requires one of [{', '.join(allowed_roles)}] in this enclave",
    )
