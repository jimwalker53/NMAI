"""Authentication endpoints (login / token issuance)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.schemas import LoginRequest, TokenResponse
from nmia.auth.security import create_access_token, verify_password
from nmia.auth.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate with username and password, returning a signed JWT."""
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=access_token, token_type="bearer")
