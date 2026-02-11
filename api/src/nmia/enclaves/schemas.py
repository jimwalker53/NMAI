"""Pydantic v2 schemas for enclave endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnclaveCreate(BaseModel):
    name: str
    description: str | None = None


class EnclaveUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class EnclaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
