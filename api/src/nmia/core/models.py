"""SQLAlchemy ORM models for core domain objects.

Contains: Enclave, ConnectorType, ConnectorInstance, Job, Finding, Identity, AuditLog.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
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
# Enclave
# ---------------------------------------------------------------------------

class Enclave(Base):
    __tablename__ = "enclaves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    connectors = relationship("ConnectorInstance", back_populates="enclave", lazy="select")
    role_assignments = relationship("UserRoleEnclave", back_populates="enclave", lazy="select")
    findings = relationship("Finding", back_populates="enclave", lazy="select")
    identities = relationship("Identity", back_populates="enclave", lazy="select")


# ---------------------------------------------------------------------------
# ConnectorType
# ---------------------------------------------------------------------------

class ConnectorType(Base):
    __tablename__ = "connector_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    code = Column(String(50), unique=True, nullable=False)  # ad_ldap, adcs_file, adcs_remote
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    instances = relationship("ConnectorInstance", back_populates="connector_type", lazy="select")


# ---------------------------------------------------------------------------
# ConnectorInstance
# ---------------------------------------------------------------------------

class ConnectorInstance(Base):
    __tablename__ = "connector_instances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    connector_type_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connector_types.id", ondelete="CASCADE"),
        nullable=False,
    )
    enclave_id = Column(
        UUID(as_uuid=True),
        ForeignKey("enclaves.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    cron_expression = Column(String(100), nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    connector_type = relationship("ConnectorType", back_populates="instances", lazy="select")
    enclave = relationship("Enclave", back_populates="connectors", lazy="select")
    creator = relationship("User", back_populates="created_connectors", lazy="select")
    jobs = relationship("Job", back_populates="connector_instance", lazy="select")
    findings = relationship("Finding", back_populates="connector_instance", lazy="select")


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    connector_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connector_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    records_found = Column(Integer, default=0, nullable=False)
    records_ingested = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    triggered_by = Column(String(20), nullable=False)  # schedule, manual, collector
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    connector_instance = relationship("ConnectorInstance", back_populates="jobs", lazy="select")
    findings = relationship("Finding", back_populates="job", lazy="select")


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    connector_instance_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connector_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    enclave_id = Column(
        UUID(as_uuid=True),
        ForeignKey("enclaves.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type = Column(String(50), nullable=False)  # ad_svc_acct, adcs_cert
    raw_data = Column(JSON, nullable=False, default=dict)
    fingerprint = Column(String(512), nullable=False)
    ingested_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_finding_fingerprint_enclave", "fingerprint", "enclave_id"),
    )

    # Relationships
    job = relationship("Job", back_populates="findings", lazy="select")
    connector_instance = relationship("ConnectorInstance", back_populates="findings", lazy="select")
    enclave = relationship("Enclave", back_populates="findings", lazy="select")


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

class Identity(Base):
    __tablename__ = "identities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    enclave_id = Column(
        UUID(as_uuid=True),
        ForeignKey("enclaves.id", ondelete="CASCADE"),
        nullable=False,
    )
    identity_type = Column(String(50), nullable=False)  # svc_acct, cert
    display_name = Column(String(512), nullable=False)
    fingerprint = Column(String(512), nullable=False)
    normalized_data = Column(JSON, nullable=False, default=dict)
    owner = Column(String(255), nullable=True)
    linked_system = Column(String(255), nullable=True)
    risk_score = Column(Float, default=0.0, nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)
    finding_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("fingerprint", "enclave_id", name="uq_identity_fingerprint_enclave"),
    )

    # Relationships
    enclave = relationship("Enclave", back_populates="identities", lazy="select")


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=_new_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(String(255), nullable=False)
    resource_type = Column(String(255), nullable=False)
    resource_id = Column(String(255), nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs", lazy="select")
