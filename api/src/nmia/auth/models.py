"""SQLAlchemy ORM models for authentication and RBAC.

Contains: User, Role, UserRoleEnclave.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from nmia.core.db import Base


def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> uuid.UUID:
    """Generate a new UUID4."""
    return uuid.uuid4()


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(50), unique=True, nullable=False)  # admin, operator, viewer, auditor
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    role_assignments = relationship("UserRoleEnclave", back_populates="role", lazy="select")


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    username = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    role_assignments = relationship("UserRoleEnclave", back_populates="user", lazy="select")
    created_connectors = relationship("ConnectorInstance", back_populates="creator", lazy="select")
    audit_logs = relationship("AuditLog", back_populates="user", lazy="select")


# ---------------------------------------------------------------------------
# UserRoleEnclave  (many-to-many: User <-> Role, scoped to Enclave)
# ---------------------------------------------------------------------------

class UserRoleEnclave(Base):
    __tablename__ = "user_role_enclaves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    enclave_id = Column(UUID(as_uuid=True), ForeignKey("enclaves.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", "enclave_id", name="uq_user_role_enclave"),
    )

    # Relationships
    user = relationship("User", back_populates="role_assignments", lazy="select")
    role = relationship("Role", back_populates="role_assignments", lazy="select")
    enclave = relationship("Enclave", back_populates="role_assignments", lazy="select")
