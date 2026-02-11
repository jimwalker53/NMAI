"""Password hashing and JWT token utilities."""

from datetime import datetime, timedelta, timezone
from importlib.util import find_spec

from jose import JWTError, jwt
from passlib.context import CryptContext

from nmia.settings import settings

_has_argon2 = find_spec("argon2") is not None
_hash_schemes = ["argon2", "bcrypt"] if _has_argon2 else ["bcrypt"]

pwd_context = CryptContext(schemes=_hash_schemes, deprecated="auto")


def hash_password(plain: str) -> str:
    """Return the hash of *plain* (argon2 preferred, bcrypt fallback)."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches the stored *hashed* value."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Create a signed JWT that expires after ``JWT_EXPIRE_MINUTES``.

    Parameters
    ----------
    data:
        Arbitrary claims to embed in the token (typically ``{"sub": username}``).

    Returns
    -------
    str
        Encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT.

    Parameters
    ----------
    token:
        The encoded JWT string.

    Returns
    -------
    dict
        The decoded payload claims.

    Raises
    ------
    jose.JWTError
        If the token is expired, malformed, or the signature is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise
