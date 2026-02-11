"""Pydantic v2 schemas for reporting endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ExpiringCertReport(BaseModel):
    identity_id: UUID
    display_name: str
    enclave_id: UUID
    not_after: datetime
    days_remaining: int
    risk_score: float


class OrphanedIdentityReport(BaseModel):
    identity_id: UUID
    display_name: str
    enclave_id: UUID
    identity_type: str
    owner: str | None
    linked_system: str | None
    risk_score: float
