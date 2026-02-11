"""Pydantic v2 schemas for connector management endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConnectorInstanceCreate(BaseModel):
    connector_type_code: str
    enclave_id: UUID
    name: str
    config: dict
    cron_expression: str | None = None


class ConnectorInstanceUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    cron_expression: str | None = None
    is_enabled: bool | None = None


class ConnectorInstanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_type_id: UUID
    enclave_id: UUID
    name: str
    config: dict
    cron_expression: str | None
    is_enabled: bool
    last_run_at: datetime | None
    created_at: datetime


class ConnectorTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    created_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_instance_id: UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    records_found: int
    records_ingested: int
    error_message: str | None
    triggered_by: str
    created_at: datetime
