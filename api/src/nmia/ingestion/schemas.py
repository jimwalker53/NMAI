"""Pydantic v2 schemas for ingestion endpoints."""

from uuid import UUID

from pydantic import BaseModel


class ADCSIngestPayload(BaseModel):
    connector_instance_id: UUID
    records: list[dict]
