"""FastAPI application entry point for the NMIA backend."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from nmia.settings import settings
from nmia.core.db import SessionLocal
from nmia.core.models import ConnectorType, Enclave
from nmia.auth.security import hash_password
from nmia.auth.models import Role, User, UserRoleEnclave


def _seed_connector_types() -> None:
    """Ensure the default connector types exist in the database."""
    db = SessionLocal()
    try:
        defaults = [
            {
                "code": "ad_ldap",
                "name": "Active Directory (LDAP)",
                "description": "Connects to Active Directory via LDAP to discover service accounts and other non-human identities.",
            },
            {
                "code": "adcs_file",
                "name": "AD Certificate Services (File)",
                "description": "Ingests certificate data from exported CSV / JSON files produced by ADCS.",
            },
            {
                "code": "adcs_remote",
                "name": "AD Certificate Services (Remote)",
                "description": "Connects to a remote ADCS CA to enumerate issued certificates.",
            },
        ]
        for ct in defaults:
            existing = db.query(ConnectorType).filter(ConnectorType.code == ct["code"]).first()
            if existing is None:
                db.add(ConnectorType(**ct))
        db.commit()
    finally:
        db.close()


def _seed_roles() -> None:
    """Ensure the default RBAC roles exist."""
    db = SessionLocal()
    try:
        default_roles = [
            {"name": "admin", "description": "Full administrative access across all enclaves."},
            {"name": "operator", "description": "Can manage connectors, run ingestion, and edit identities within assigned enclaves."},
            {"name": "viewer", "description": "Read-only access to data within assigned enclaves."},
            {"name": "auditor", "description": "Read-only access with visibility into audit logs and reports."},
        ]
        for r in default_roles:
            existing = db.query(Role).filter(Role.name == r["name"]).first()
            if existing is None:
                db.add(Role(**r))
        db.commit()
    finally:
        db.close()


def _seed_default_admin() -> None:
    """Create a default admin user (admin / admin) when the users table is
    empty.  This bootstrapping account should be changed immediately in
    production.
    """
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return

        # Create a default enclave for the admin
        default_enclave = db.query(Enclave).filter(Enclave.name == "Default").first()
        if default_enclave is None:
            default_enclave = Enclave(name="Default", description="Default enclave created during bootstrap.")
            db.add(default_enclave)
            db.flush()

        # Create the admin user
        admin_user = User(
            username="admin",
            password_hash=hash_password("admin"),
            email="admin@nmia.local",
        )
        db.add(admin_user)
        db.flush()

        # Assign the admin role in the default enclave
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is not None:
            assignment = UserRoleEnclave(
                user_id=admin_user.id,
                role_id=admin_role.id,
                enclave_id=default_enclave.id,
            )
            db.add(assignment)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler -- runs seed functions on startup."""
    _seed_connector_types()
    _seed_roles()
    _seed_default_admin()
    yield


app = FastAPI(
    title="NMIA - Non-Human Identity Authority",
    description="Central platform for discovering, inventorying, and managing non-human identities across the enterprise.",
    version="1.0.0",
    lifespan=lifespan,
)

# -- CORS ---------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Routers ------------------------------------------------------------------

from nmia.auth.routes import router as auth_router  # noqa: E402
from nmia.enclaves.routes import router as enclaves_router  # noqa: E402
from nmia.users.routes import router as users_router  # noqa: E402
from nmia.connectors.routes import router as connectors_router  # noqa: E402
from nmia.ingestion.routes import router as ingest_router  # noqa: E402
from nmia.ingestion.identities import router as identities_router  # noqa: E402
from nmia.reports.routes import router as reports_router  # noqa: E402

app.include_router(auth_router)
app.include_router(enclaves_router)
app.include_router(users_router)
app.include_router(connectors_router)
app.include_router(ingest_router)
app.include_router(identities_router)
app.include_router(reports_router)


# -- Health check -------------------------------------------------------------

@app.get("/health", tags=["health"])
def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "healthy"}


def run() -> None:
    """Entry point for the ``nmia`` console script."""
    import uvicorn

    uvicorn.run("nmia.main:app", host="0.0.0.0", port=8000, reload=True)
