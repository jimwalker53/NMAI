"""Shared pytest fixtures for NMIA backend tests.

Uses an in-memory SQLite database so that tests never touch the real
PostgreSQL instance.  The PostgreSQL-specific ``UUID`` column type is
transparently replaced with a ``CHAR(32)`` representation so that the
same ORM models work on both dialects.
"""

from __future__ import annotations

import uuid
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from nmia.core.db import Base, get_db
from nmia.auth.security import create_access_token, hash_password
from nmia.main import app
from nmia.auth.models import Role, User, UserRoleEnclave
from nmia.core.models import ConnectorType, Enclave


# ---------------------------------------------------------------------------
# SQLite engine with UUID support
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine.

    Enables WAL mode and foreign keys for proper constraint enforcement.
    """
    _engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )

    # Enable foreign key enforcement in SQLite
    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Register a UUID-to-bytes adapter so SQLite can store UUID columns that
    # the PostgreSQL dialect defines as ``UUID(as_uuid=True)``.
    import sqlite3

    sqlite3.register_adapter(uuid.UUID, lambda u: u.hex)
    sqlite3.register_converter("UUID", lambda b: uuid.UUID(hex=b.decode()))
    sqlite3.register_converter("CHAR", lambda b: b.decode())

    # Create all tables
    Base.metadata.create_all(bind=_engine)
    yield _engine
    Base.metadata.drop_all(bind=_engine)
    _engine.dispose()


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    """Provide a transactional database session that is rolled back after
    every test so that test isolation is guaranteed.
    """
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB override
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Return a ``TestClient`` that uses the test database session."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

@pytest.fixture()
def seed_data(db_session: Session) -> dict:
    """Populate the test database with baseline data.

    Returns a dict containing references to every created object so that
    tests can use their IDs without additional queries.
    """
    # --- Roles ---
    roles = {}
    for role_name in ("admin", "operator", "viewer", "auditor"):
        role = Role(name=role_name, description=f"{role_name} role")
        db_session.add(role)
        roles[role_name] = role

    db_session.flush()

    # --- Connector types ---
    connector_types = {}
    for code, name in [
        ("ad_ldap", "Active Directory LDAP"),
        ("adcs_file", "ADCS File Ingest"),
        ("adcs_remote", "ADCS Remote"),
    ]:
        ct = ConnectorType(code=code, name=name, description=f"{name} connector")
        db_session.add(ct)
        connector_types[code] = ct

    db_session.flush()

    # --- Enclave ---
    enclave = Enclave(name="test-enclave", description="Test enclave")
    db_session.add(enclave)
    db_session.flush()

    # --- Users ---
    admin_user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        email="admin@test.local",
    )
    operator_user = User(
        username="operator",
        password_hash=hash_password("operator123"),
        email="operator@test.local",
    )
    viewer_user = User(
        username="viewer",
        password_hash=hash_password("viewer123"),
        email="viewer@test.local",
    )
    db_session.add_all([admin_user, operator_user, viewer_user])
    db_session.flush()

    # --- Role assignments ---
    ure_admin = UserRoleEnclave(
        user_id=admin_user.id,
        role_id=roles["admin"].id,
        enclave_id=enclave.id,
    )
    ure_operator = UserRoleEnclave(
        user_id=operator_user.id,
        role_id=roles["operator"].id,
        enclave_id=enclave.id,
    )
    ure_viewer = UserRoleEnclave(
        user_id=viewer_user.id,
        role_id=roles["viewer"].id,
        enclave_id=enclave.id,
    )
    db_session.add_all([ure_admin, ure_operator, ure_viewer])
    db_session.flush()

    return {
        "roles": roles,
        "connector_types": connector_types,
        "enclave": enclave,
        "admin_user": admin_user,
        "operator_user": operator_user,
        "viewer_user": viewer_user,
        "ure_admin": ure_admin,
        "ure_operator": ure_operator,
        "ure_viewer": ure_viewer,
    }


# ---------------------------------------------------------------------------
# Auth tokens
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin_token(seed_data: dict) -> str:
    """Return a valid JWT for the admin user."""
    return create_access_token({"sub": seed_data["admin_user"].username})


@pytest.fixture()
def operator_token(seed_data: dict) -> str:
    """Return a valid JWT for the operator user."""
    return create_access_token({"sub": seed_data["operator_user"].username})


@pytest.fixture()
def viewer_token(seed_data: dict) -> str:
    """Return a valid JWT for the viewer user."""
    return create_access_token({"sub": seed_data["viewer_user"].username})


@pytest.fixture()
def auth_headers(admin_token: str) -> dict[str, str]:
    """Return Authorization headers using the admin token."""
    return {"Authorization": f"Bearer {admin_token}"}
