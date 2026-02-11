"""Ingest endpoints for importing findings from connectors."""

from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import ConnectorInstance, Finding, Job
from nmia.auth.models import User
from nmia.auth.rbac import get_current_user, require_enclave_access
from nmia.ingestion.schemas import ADCSIngestPayload

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])


@router.post("/adcs/{connector_id}")
async def ingest_adcs(
    connector_id: UUID,
    request: Request,
    job_id: UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Ingest ADCS certificate data for a connector instance.

    Accepts either:
    * **JSON body** -- an ``ADCSIngestPayload`` with ``connector_instance_id``
      and a ``records`` list.
    * **multipart/form-data** -- a CSV ``UploadFile``.  Each row becomes one
      record dict keyed by the CSV header columns.

    For every record the fingerprint is computed as
    ``"{issuer_dn}|{serial_number}"``.  A ``Finding`` is created or updated
    (de-duplicated on ``(enclave_id, source_type, fingerprint)``).

    If ``job_id`` is provided (query param or payload body), the corresponding
    ``Job`` record is updated with ``records_found`` and
    ``records_ingested`` counts.
    """
    # Look up the connector instance
    instance = (
        db.query(ConnectorInstance)
        .filter(ConnectorInstance.id == connector_id)
        .first()
    )
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_access(instance.enclave_id, current_user, db)

    # Determine content type and parse records
    content_type = request.headers.get("content-type", "")
    records: list[dict] = []
    payload_job_id: UUID | None = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        file_field = form.get("file")
        if file_field is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file field found in multipart form data",
            )
        upload: UploadFile = file_field  # type: ignore[assignment]
        raw_bytes = await upload.read()
        text = raw_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            records.append(dict(row))
    else:
        # Assume JSON body
        body = await request.json()
        payload = ADCSIngestPayload(**body)
        records = payload.records
        payload_job_id = payload.connector_instance_id  # fall-through; job_id from query wins

    # Resolve job_id -- query param takes precedence
    effective_job_id = job_id or payload_job_id

    enclave_id = instance.enclave_id
    ingested_count = 0
    duplicate_count = 0

    for record in records:
        issuer_dn = str(record.get("issuer_dn", "")).strip()
        serial_number = str(record.get("serial_number", "")).strip()
        fingerprint = f"{issuer_dn}|{serial_number}"

        existing = (
            db.query(Finding)
            .filter(
                Finding.enclave_id == enclave_id,
                Finding.source_type == "adcs_cert",
                Finding.fingerprint == fingerprint,
            )
            .first()
        )

        if existing is not None:
            # Update raw_data on the existing finding
            existing.raw_data = record
            if effective_job_id is not None:
                existing.job_id = effective_job_id
            duplicate_count += 1
        else:
            finding = Finding(
                enclave_id=enclave_id,
                connector_instance_id=instance.id,
                job_id=effective_job_id,
                source_type="adcs_cert",
                fingerprint=fingerprint,
                raw_data=record,
            )
            db.add(finding)
            ingested_count += 1

    db.flush()

    # Update Job record if we have one
    if effective_job_id is not None:
        job = db.query(Job).filter(Job.id == effective_job_id).first()
        if job is not None:
            job.records_found = len(records)
            job.records_ingested = ingested_count

    db.commit()

    return {"ingested": ingested_count, "duplicates": duplicate_count}
