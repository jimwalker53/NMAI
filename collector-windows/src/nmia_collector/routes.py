"""
NMIA Windows Collector - API Routes

Endpoints for triggering ADCS certificate collection jobs, monitoring
their progress, and retrieving results.
"""

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from nmia_collector.jobs.runner import run_collection_job
from nmia_collector.jobs.store import job_store

logger = logging.getLogger("nmia.collector.routes")

router = APIRouter(prefix="/collector/v1", tags=["collector"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    """Request body for POST /adcs/run."""

    mode: str = "inventory"  # "inventory" or "inventory_san"
    since_days: int = 30
    max_records: int = 10000
    max_san_fetch: int = 500
    callback_url: str | None = None  # NMIA ingest endpoint URL override


class RunResponse(BaseModel):
    job_id: str
    status: str


# ---------------------------------------------------------------------------
# Route: Trigger a collection job
# ---------------------------------------------------------------------------


@router.post("/adcs/run", response_model=RunResponse)
async def run_adcs_collection(request: RunRequest):
    """
    Start an ADCS certificate collection job.

    This launches a background task that:
      1. Runs certutil to enumerate certificates (or uses mock data)
      2. Optionally fetches SANs from individual certs
      3. Pushes results to the NMIA server
    """
    job = job_store.create_job(mode=request.mode)
    job_store.add_log(
        job.job_id,
        f"Job created: mode={request.mode}, since_days={request.since_days}",
    )

    # Launch background collection task
    asyncio.create_task(
        run_collection_job(
            job_id=job.job_id,
            mode=request.mode,
            since_days=request.since_days,
            max_records=request.max_records,
            max_san_fetch=request.max_san_fetch,
            callback_url=request.callback_url,
        )
    )

    return RunResponse(job_id=job.job_id, status="started")


# ---------------------------------------------------------------------------
# Route: Job status
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Return the current status of a collection job."""
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_status_dict()


# ---------------------------------------------------------------------------
# Route: Job logs
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/logs")
async def get_job_logs(job_id: str):
    """Return the log entries for a collection job."""
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "logs": job_store.get_logs(job_id)}


# ---------------------------------------------------------------------------
# Route: Job result (collected records)
# ---------------------------------------------------------------------------


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Return collected certificate records if the job is completed."""
    job = job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("completed", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"Job is still {job.status}; results not yet available",
        )
    return {
        "job_id": job_id,
        "status": job.status,
        "records_found": job.records_found,
        "records": job.result,
    }
