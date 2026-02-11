"""Pydantic v2 schemas for identity endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IdentityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    enclave_id: UUID
    identity_type: str
    display_name: str
    fingerprint: str
    normalized_data: dict
    owner: str | None
    linked_system: str | None
    risk_score: float
    first_seen: datetime
    last_seen: datetime


class IdentityUpdate(BaseModel):
    owner: str | None = None
    linked_system: str | None = None
