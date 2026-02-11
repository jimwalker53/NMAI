"""
Task definitions that the scheduler calls.

Provides the main dispatch logic for executing pending jobs and creating
scheduled jobs for connector instances.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from nmia_worker.scheduler import SessionLocal
from nmia_worker.connectors.ad.collector import connect_and_collect
from nmia_worker.connectors.ad.normalizer import (
    compute_fingerprint as ad_fingerprint,
    normalize_ad_finding,
)
from nmia_worker.connectors.adcs.normalizer import (
    compute_fingerprint as adcs_fingerprint,
    normalize_cert_finding,
)
from nmia_worker.pipeline.normalize import normalize_findings
from nmia_worker.pipeline.correlate import correlate_identities
from nmia_worker.pipeline.risk import score_risks

# Import shared models via the scheduler's sys.path setup
from nmia.core.models import (  # noqa: E402
    ConnectorInstance,
    ConnectorType,
    Finding,
    Job,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# AD LDAP Executor
# ---------------------------------------------------------------------------

def _execute_ad_ldap_job(
    db: Session,
    job: Job,
    connector: ConnectorInstance,
) -> None:
    """Execute an Active Directory LDAP connector job.

    Connects to the configured LDAP server, searches for service-account
    objects, and creates a Finding for each entry found.
    """
    config: dict[str, Any] = connector.config or {}

    try:
        raw_entries = connect_and_collect(config)
        job.records_found = len(raw_entries)
        ingested = 0

        for entry_dict in raw_entries:
            try:
                fingerprint = ad_fingerprint(entry_dict)
                if not fingerprint:
                    logger.warning(
                        "_execute_ad_ldap_job: skipping entry without objectSid"
                    )
                    continue

                finding = Finding(
                    job_id=job.id,
                    connector_instance_id=connector.id,
                    enclave_id=connector.enclave_id,
                    source_type="ad_svc_acct",
                    raw_data=entry_dict,
                    fingerprint=fingerprint,
                )
                db.add(finding)
                ingested += 1

            except Exception as entry_err:
                logger.error(
                    "_execute_ad_ldap_job: failed to process entry: %s",
                    entry_err,
                    exc_info=True,
                )

        job.records_ingested = ingested
        job.status = "completed"
        db.flush()

        logger.info(
            "_execute_ad_ldap_job: job=%s completed. found=%d ingested=%d",
            job.id,
            job.records_found,
            ingested,
        )

    except Exception as exc:
        logger.error(
            "_execute_ad_ldap_job: job=%s failed: %s", job.id, exc, exc_info=True
        )
        job.status = "failed"
        job.error_message = str(exc)
        db.flush()


# ---------------------------------------------------------------------------
# ADCS File Executor
# ---------------------------------------------------------------------------

def _execute_adcs_file_job(
    db: Session,
    job: Job,
    connector: ConnectorInstance,
) -> None:
    """Execute an ADCS file-upload connector job.

    For file-upload connectors the actual data ingestion happens at the
    API/ingest endpoint that creates findings directly.  This executor simply
    marks the job as completed and triggers normalization.
    """
    try:
        finding_count = (
            db.query(Finding)
            .filter(Finding.job_id == job.id)
            .count()
        )
        job.records_found = finding_count
        job.records_ingested = finding_count
        job.status = "completed"
        db.flush()

        logger.info(
            "_execute_adcs_file_job: job=%s completed with %d findings",
            job.id,
            finding_count,
        )

    except Exception as exc:
        logger.error(
            "_execute_adcs_file_job: job=%s failed: %s", job.id, exc, exc_info=True
        )
        job.status = "failed"
        job.error_message = str(exc)
        db.flush()


# ---------------------------------------------------------------------------
# Executor Dispatch Table
# ---------------------------------------------------------------------------

_EXECUTORS: dict[str, Any] = {
    "ad_ldap": _execute_ad_ldap_job,
    "adcs_file": _execute_adcs_file_job,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def execute_pending_job(job_id: UUID) -> None:
    """Load a Job by ID, dispatch to the correct executor, and run the
    normalization pipeline on completion.

    This is the primary entry point called by the scheduler / poller.
    """
    db: Session = SessionLocal()
    try:
        job: Job | None = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            logger.error("execute_pending_job: job=%s not found", job_id)
            return

        connector: ConnectorInstance | None = (
            db.query(ConnectorInstance)
            .filter(ConnectorInstance.id == job.connector_instance_id)
            .first()
        )
        if connector is None:
            logger.error(
                "execute_pending_job: connector_instance=%s not found for job=%s",
                job.connector_instance_id,
                job_id,
            )
            job.status = "failed"
            job.error_message = "ConnectorInstance not found"
            job.finished_at = _utcnow()
            db.commit()
            return

        # Resolve the connector_type code
        connector_type: ConnectorType | None = (
            db.query(ConnectorType)
            .filter(ConnectorType.id == connector.connector_type_id)
            .first()
        )
        if connector_type is None:
            logger.error(
                "execute_pending_job: connector_type=%s not found for connector=%s",
                connector.connector_type_id,
                connector.id,
            )
            job.status = "failed"
            job.error_message = "ConnectorType not found"
            job.finished_at = _utcnow()
            db.commit()
            return

        type_code = connector_type.code
        executor = _EXECUTORS.get(type_code)
        if executor is None:
            logger.error(
                "execute_pending_job: no executor registered for connector_type code=%s",
                type_code,
            )
            job.status = "failed"
            job.error_message = f"Unsupported connector type: {type_code}"
            job.finished_at = _utcnow()
            db.commit()
            return

        # Mark as running
        job.status = "running"
        job.started_at = _utcnow()
        db.flush()

        logger.info(
            "execute_pending_job: starting job=%s type=%s connector=%s enclave=%s",
            job.id,
            type_code,
            connector.id,
            connector.enclave_id,
        )

        # Dispatch to the type-specific executor
        try:
            executor(db, job, connector)
        except Exception as exc:
            logger.error(
                "execute_pending_job: unhandled exception in executor for job=%s: %s",
                job.id,
                exc,
                exc_info=True,
            )
            job.status = "failed"
            job.error_message = str(exc)

        # Finalize
        job.finished_at = _utcnow()
        connector.last_run_at = _utcnow()
        db.commit()

        # Run normalization pipeline regardless of job success/failure --
        # partial data may still have been ingested.
        try:
            _run_normalization_pipeline(db, enclave_id=connector.enclave_id)
        except Exception as norm_exc:
            logger.error(
                "execute_pending_job: normalization pipeline failed for enclave=%s: %s",
                connector.enclave_id,
                norm_exc,
                exc_info=True,
            )

    except Exception as exc:
        logger.error(
            "execute_pending_job: unexpected error for job=%s: %s",
            job_id,
            exc,
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()


def create_scheduled_job(connector_instance_id: UUID) -> None:
    """Create a new Job record with triggered_by='schedule' for the given
    connector instance, then execute it.
    """
    db: Session = SessionLocal()
    try:
        connector: ConnectorInstance | None = (
            db.query(ConnectorInstance)
            .filter(ConnectorInstance.id == connector_instance_id)
            .first()
        )
        if connector is None:
            logger.error(
                "create_scheduled_job: connector=%s not found",
                connector_instance_id,
            )
            return

        if not connector.is_enabled:
            logger.info(
                "create_scheduled_job: connector=%s is disabled, skipping",
                connector_instance_id,
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
            "create_scheduled_job: created job=%s for connector=%s (%s)",
            job.id,
            connector.id,
            connector.name,
        )

        execute_pending_job(job.id)

    except Exception as exc:
        logger.error(
            "create_scheduled_job: error for connector=%s: %s",
            connector_instance_id,
            exc,
            exc_info=True,
        )
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Internal pipeline orchestration
# ---------------------------------------------------------------------------

def _run_normalization_pipeline(
    db: Session,
    enclave_id: UUID | None = None,
) -> dict[str, Any]:
    """Run the full normalization -> correlation -> risk-scoring pipeline.

    Returns a summary dict with counts from each stage.
    """
    logger.info("normalization_pipeline: starting (enclave=%s)", enclave_id)

    normalized_count = normalize_findings(db, enclave_id=enclave_id)
    correlated_count = correlate_identities(db, enclave_id=enclave_id)
    scored_count = score_risks(db, enclave_id=enclave_id)

    db.commit()

    summary = {
        "enclave_id": str(enclave_id) if enclave_id else None,
        "identities_normalized": normalized_count,
        "identities_correlated": correlated_count,
        "identities_scored": scored_count,
    }
    logger.info("normalization_pipeline: completed %s", summary)
    return summary
