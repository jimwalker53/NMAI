"""
NMIA Windows Collector - In-Memory Job Store

Provides thread-safe, in-memory storage for collection job state.
Jobs are lost on process restart; this is acceptable because the
collector is a stateless worker whose results are pushed to the
NMIA server.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class Job:
    """Tracks the state of a single collection job."""

    def __init__(self, job_id: str, mode: str) -> None:
        self.job_id: str = job_id
        self.mode: str = mode
        self.status: str = "started"
        self.records_found: int = 0
        self.records_pushed: int = 0
        self.started_at: str = datetime.now(timezone.utc).isoformat()
        self.finished_at: str | None = None
        self.error: str | None = None
        self.logs: list[str] = []
        self.result: list[dict] = []

    def to_status_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable status summary."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "mode": self.mode,
            "records_found": self.records_found,
            "records_pushed": self.records_pushed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
        }


class JobStore:
    """
    In-memory store for collection jobs.

    All operations are synchronous because the dict is only mutated from
    the main asyncio thread.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def create_job(self, mode: str = "inventory") -> Job:
        """Create a new job and return it."""
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, mode=mode)
        self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        """Return the job with the given ID, or ``None``."""
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **kwargs: Any) -> None:
        """Update arbitrary fields on a job."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

    def add_log(self, job_id: str, message: str) -> None:
        """Append a timestamped log entry to the job."""
        job = self._jobs.get(job_id)
        if job is None:
            return
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        job.logs.append(f"[{ts}] {message}")

    def get_logs(self, job_id: str) -> list[str]:
        """Return the log entries for a job."""
        job = self._jobs.get(job_id)
        if job is None:
            return []
        return list(job.logs)


# Global singleton used across the application
job_store = JobStore()
