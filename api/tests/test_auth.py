"""Tests for authentication endpoints and security utilities."""

from __future__ import annotations

import pytest
from jose import JWTError

from nmia.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Login endpoint tests
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    """POST /api/v1/auth/login"""

    def test_login_success(self, client, seed_data):
        """Valid credentials return 200 with an access_token."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        # The token should be decodable
        payload = decode_access_token(body["access_token"])
        assert payload["sub"] == "admin"

    def test_login_wrong_password(self, client, seed_data):
        """Wrong password returns 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self, client, seed_data):
        """Non-existent username returns 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"username": "no-such-user", "password": "whatever"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Security utility tests
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    """hash_password / verify_password round-trip."""

    def test_password_hashing(self):
        """hash_password produces a hash that verify_password accepts."""
        plain = "s3cret-p@ssword!"
        hashed = hash_password(plain)
        # Hash should not equal the plaintext
        assert hashed != plain
        # verify_password should return True for the correct plaintext
        assert verify_password(plain, hashed) is True
        # verify_password should return False for a wrong plaintext
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_for_same_password(self):
        """Two calls to hash_password with the same input produce different
        bcrypt hashes (different salts).
        """
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        # But both verify correctly
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


class TestJWT:
    """create_access_token / decode_access_token round-trip."""

    def test_jwt_create_and_decode(self):
        """A token created with create_access_token can be decoded back to
        its original claims.
        """
        data = {"sub": "testuser", "extra": "value"}
        token = create_access_token(data)
        assert isinstance(token, str)

        payload = decode_access_token(token)
        assert payload["sub"] == "testuser"
        assert payload["extra"] == "value"
        # An expiration claim should have been added
        assert "exp" in payload

    def test_decode_invalid_token_raises(self):
        """decode_access_token raises JWTError on a garbage token."""
        with pytest.raises(JWTError):
            decode_access_token("not-a-valid-token")


# ---------------------------------------------------------------------------
# Protected endpoint access tests
# ---------------------------------------------------------------------------

class TestProtectedEndpoints:
    """Verify that protected endpoints reject unauthenticated requests."""

    def test_protected_endpoint_no_token(self, client, seed_data):
        """GET /api/v1/enclaves without an Authorization header returns 401
        (or 403 from HTTPBearer).
        """
        resp = client.get("/api/v1/enclaves/")
        assert resp.status_code in (401, 403)

    def test_protected_endpoint_invalid_token(self, client, seed_data):
        """GET /api/v1/enclaves with a garbage Bearer token returns 401."""
        resp = client.get(
            "/api/v1/enclaves/",
            headers={"Authorization": "Bearer garbage-token-value"},
        )
        assert resp.status_code == 401
