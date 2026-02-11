"""Pydantic v2 schemas for user management endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None


class UserUpdate(BaseModel):
    email: str | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None
    is_active: bool
    created_at: datetime


class RoleAssignment(BaseModel):
    user_id: UUID
    role_name: str
    enclave_id: UUID


class UserRoleEnclaveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    role_id: UUID
    enclave_id: UUID
    created_at: datetime
