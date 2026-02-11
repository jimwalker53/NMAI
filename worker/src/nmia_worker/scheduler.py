"""
APScheduler setup for the NMIA worker.

Manages cron-based schedules for connector instances and a periodic poller
that picks up pending (manually-triggered) jobs from the Job table.

The worker shares the same PostgreSQL database as the API service.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# ---------------------------------------------------------------------------
# Database setup -- the worker connects to the SAME database as the API.
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://nmia:nmia@localhost:5432/nmia"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

# ---------------------------------------------------------------------------
# Import shared models from the API package (monorepo layout).
# In production you would share a common models package instead.
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../api/src"))
from nmia.core.models import (  # noqa: E402
    ConnectorInstance,
    ConnectorType,
    Enclave,
    Finding,
    Identity,
    Job,
)
from nmia.core.db import Base  # noqa: E402
from nmia.auth.models import Role, User, UserRoleEnclave  # noqa: E402

logger = logging.getLogger(__name__)

# Module-level scheduler instance
_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def _parse_cron_expression(cron_expr: str) -> dict[str, str]:
    """Parse a 5-field cron expression into APScheduler CronTrigger kwargs.

    Format: ``minute hour day_of_month month day_of_week``
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression '{cron_expr}': expected 5 fields, got {len(parts)}"
        )
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


# ---------------------------------------------------------------------------
# Scheduled Job Creator
# ---------------------------------------------------------------------------

def _create_and_run_scheduled_job(connector_id: UUID) -> None:
    """Create a new Job row for a scheduled connector and execute it.

    This function is invoked by APScheduler on each cron tick.
    """
    from nmia_worker.tasks import execute_pending_job

    db: Session = SessionLocal()
    try:
        connector: ConnectorInstance | None = (
            db.query(ConnectorInstance)
            .filter(ConnectorInstance.id == connector_id)
            .first()
        )
        if connector is None:
            logger.error(
                "scheduled_job: connector=%s no longer exists, skipping",
                connector_id,
            )
            return

        if not connector.is_enabled:
            logger.info(
                "scheduled_job: connector=%s is disabled, skipping",
                connector_id,
            )
            return

        job = Job(
            connector_instance_id=connector.id,
            status="pending",
            triggered_by="schedule",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(
            "scheduled_job: created job=%s for connector=%s (%s)",
            job.id,
            connector.id,
            connector.name,
        )

        execute_pending_job(job.id)

    except Exception as exc:
        logger.error(
            "scheduled_job: error for connector=%s: %s",
            connector_id,
            exc,
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Pending-Job Poller
# ---------------------------------------------------------------------------

def poll_pending_jobs() -> None:
    """Poll for pending jobs and execute them sequentially."""
    from nmia_worker.tasks import execute_pending_job

    db: Session = SessionLocal()
    try:
        pending_jobs: list[Job] = (
            db.query(Job)
            .filter(Job.status == "pending")
            .order_by(Job.created_at)
            .all()
        )

        if not pending_jobs:
            return

        logger.info("poll_pending_jobs: found %d pending job(s)", len(pending_jobs))

        for job in pending_jobs:
            try:
                logger.info("poll_pending_jobs: executing job=%s", job.id)
                execute_pending_job(job.id)
            except Exception as exc:
                logger.error(
                    "poll_pending_jobs: error executing job=%s: %s",
                    job.id,
                    exc,
                    exc_info=True,
                )

    except Exception as exc:
        logger.error("poll_pending_jobs: query error: %s", exc, exc_info=True)
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Schedule Management
# ---------------------------------------------------------------------------

def add_connector_schedule(connector: ConnectorInstance) -> None:
    """Add a cron-based schedule for a connector to the running scheduler.

    ``connector.cron_expression`` must be a valid 5-field cron string.
    """
    global _scheduler
    if _scheduler is None:
        logger.error("add_connector_schedule: scheduler not initialised")
        return

    if not connector.cron_expression:
        logger.warning(
            "add_connector_schedule: connector=%s has no cron_expression",
            connector.id,
        )
        return

    try:
        cron_kwargs = _parse_cron_expression(connector.cron_expression)
    except ValueError as exc:
        logger.error(
            "add_connector_schedule: invalid cron for connector=%s: %s",
            connector.id,
            exc,
        )
        return

    job_id = f"connector_{connector.id}"

    # Remove existing schedule if present (idempotent re-add)
    if _scheduler.get_job(job_id) is not None:
        _scheduler.remove_job(job_id)

    _scheduler.add_job(
        _create_and_run_scheduled_job,
        trigger=CronTrigger(**cron_kwargs),
        args=[connector.id],
        id=job_id,
        name=f"Scheduled: {connector.name}",
        replace_existing=True,
        misfire_grace_time=60,
    )

    logger.info(
        "add_connector_schedule: added schedule for connector=%s (%s) cron=%s",
        connector.id,
        connector.name,
        connector.cron_expression,
    )


def remove_connector_schedule(connector_id: UUID) -> None:
    """Remove a cron-based schedule for a connector from the running scheduler."""
    global _scheduler
    if _scheduler is None:
        return

    job_id = f"connector_{connector_id}"
    if _scheduler.get_job(job_id) is not None:
        _scheduler.remove_job(job_id)
        logger.info(
            "remove_connector_schedule: removed schedule for connector=%s",
            connector_id,
        )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def _load_existing_schedules() -> None:
    """Load all enabled ConnectorInstances that have a cron_expression and
    register them with the scheduler."""
    db: Session = SessionLocal()
    try:
        connectors: list[ConnectorInstance] = (
            db.query(ConnectorInstance)
            .filter(
                ConnectorInstance.is_enabled.is_(True),
                ConnectorInstance.cron_expression.isnot(None),
                ConnectorInstance.cron_expression != "",
            )
            .all()
        )

        logger.info(
            "_load_existing_schedules: found %d scheduled connector(s)",
            len(connectors),
        )

        for connector in connectors:
            add_connector_schedule(connector)

    except Exception as exc:
        logger.error(
            "_load_existing_schedules: failed to load schedules: %s",
            exc,
            exc_info=True,
        )
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the APScheduler BackgroundScheduler.

    Returns the running scheduler instance.
    """
    global _scheduler

    _scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60,
        },
        timezone="UTC",
    )

    # Add the pending-job poller (every 15 seconds)
    _scheduler.add_job(
        poll_pending_jobs,
        trigger=IntervalTrigger(seconds=15),
        id="poll_pending_jobs",
        name="Poll for pending jobs",
        replace_existing=True,
    )

    # Load cron schedules from the database
    _load_existing_schedules()

    _scheduler.start()
    logger.info("Scheduler started with %d job(s)", len(_scheduler.get_jobs()))

    return _scheduler
