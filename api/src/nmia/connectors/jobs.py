"""
Connector job execution service.

Dispatches connector jobs to the appropriate executor based on connector type,
creates findings from collected data, and triggers the normalization pipeline.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from nmia.core.models import ConnectorInstance, ConnectorType, Finding, Job
from nmia.ingestion.normalize import normalize_findings
from nmia.ingestion.correlate import correlate_identities
from nmia.ingestion.risk import score_risks

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# AD / LDAP Executor
# ---------------------------------------------------------------------------

def execute_ad_ldap_job(
    db: Session,
    job: Job,
    connector: ConnectorInstance,
) -> None:
    """Execute an Active Directory LDAP connector job.

    Connects to the configured LDAP server, searches for service-account
    objects, and creates a Finding for each entry found.
    """
    config: dict[str, Any] = connector.config or {}
    server = config.get("server", "localhost")
    port = config.get("port", 389)
    use_ssl = config.get("use_ssl", False)
    bind_dn = config.get("bind_dn", "")
    bind_password = config.get("bind_password", "")
    search_base = config.get("search_base", "")
    search_filter = config.get(
        "search_filter",
        "(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))",
    )

    # Attributes we want back from the directory
    attributes = [
        "sAMAccountName",
        "cn",
        "distinguishedName",
        "objectSid",
        "servicePrincipalName",
        "userAccountControl",
        "pwdLastSet",
        "lastLogonTimestamp",
    ]

    try:
        # Import ldap3 inside the function so the rest of the module does not
        # hard-depend on it (useful for testing / environments without ldap3).
        import ldap3  # type: ignore[import-untyped]
        from ldap3 import ALL_ATTRIBUTES, Connection, Server, SUBTREE  # type: ignore[import-untyped]

        ldap_server = Server(server, port=int(port), use_ssl=use_ssl, get_info=ldap3.ALL)
        conn = Connection(
            ldap_server,
            user=bind_dn,
            password=bind_password,
            auto_bind=True,
            read_only=True,
            receive_timeout=30,
        )

        logger.info(
            "execute_ad_ldap_job: connected to %s:%s (ssl=%s) for job=%s",
            server,
            port,
            use_ssl,
            job.id,
        )

        conn.search(
            search_base=search_base,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=attributes,
        )

        entries = conn.entries
        job.records_found = len(entries)
        ingested = 0

        for entry in entries:
            try:
                # Convert ldap3 Entry to a plain dict
                entry_dict: dict[str, Any] = {}
                for attr_name in attributes:
                    raw_val = getattr(entry, attr_name, None)
                    if raw_val is not None:
                        val = raw_val.value
                        # Lists with a single element can be unwound for
                        # simple scalar fields, but keep lists for multi-value.
                        if isinstance(val, list) and len(val) == 1 and attr_name != "servicePrincipalName":
                            val = val[0]
                        entry_dict[attr_name] = val

                # Derive enabled flag from userAccountControl bitmask
                uac = entry_dict.pop("userAccountControl", None)
                if uac is not None:
                    try:
                        uac_int = int(uac)
                        # Bit 0x0002 = ACCOUNTDISABLE
                        entry_dict["userAccountControl_enabled"] = not bool(uac_int & 0x0002)
                    except (ValueError, TypeError):
                        entry_dict["userAccountControl_enabled"] = True
                else:
                    entry_dict["userAccountControl_enabled"] = True

                # Convert non-serialisable types to strings
                for k, v in entry_dict.items():
                    if isinstance(v, bytes):
                        entry_dict[k] = v.hex()
                    elif isinstance(v, datetime):
                        entry_dict[k] = v.isoformat()

                object_sid = str(entry_dict.get("objectSid", ""))
                if not object_sid:
                    logger.warning(
                        "execute_ad_ldap_job: skipping entry without objectSid"
                    )
                    continue

                finding = Finding(
                    job_id=job.id,
                    connector_instance_id=connector.id,
                    enclave_id=connector.enclave_id,
                    source_type="ad_svc_acct",
                    raw_data=entry_dict,
                    fingerprint=object_sid,
                )
                db.add(finding)
                ingested += 1

            except Exception as entry_err:
                logger.error(
                    "execute_ad_ldap_job: failed to process entry: %s",
                    entry_err,
                    exc_info=True,
                )

        job.records_ingested = ingested
        job.status = "completed"
        db.flush()

        conn.unbind()

        logger.info(
            "execute_ad_ldap_job: job=%s completed. found=%d ingested=%d",
            job.id,
            job.records_found,
            ingested,
        )

    except Exception as exc:
        logger.error(
            "execute_ad_ldap_job: job=%s failed: %s", job.id, exc, exc_info=True
        )
        job.status = "failed"
        job.error_message = str(exc)
        db.flush()


# ---------------------------------------------------------------------------
# ADCS File Executor
# ---------------------------------------------------------------------------

def execute_adcs_file_job(
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
        # Count findings already attached to this job (created by the ingest
        # endpoint before the job was dispatched).
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
            "execute_adcs_file_job: job=%s completed with %d findings",
            job.id,
            finding_count,
        )

    except Exception as exc:
        logger.error(
            "execute_adcs_file_job: job=%s failed: %s", job.id, exc, exc_info=True
        )
        job.status = "failed"
        job.error_message = str(exc)
        db.flush()


# ---------------------------------------------------------------------------
# Executor Dispatch Table
# ---------------------------------------------------------------------------

_EXECUTORS: dict[str, Any] = {
    "ad_ldap": execute_ad_ldap_job,
    "adcs_file": execute_adcs_file_job,
}


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def _run_normalization_pipeline(db: Session, enclave_id: UUID) -> dict[str, Any]:
    """Run the full normalization -> correlation -> risk-scoring pipeline.

    Returns a summary dict with counts from each stage.
    """
    logger.info("run_normalization_pipeline: starting (enclave=%s)", enclave_id)

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
    logger.info("run_normalization_pipeline: completed %s", summary)
    return summary


def execute_job(db: Session, job_id: UUID) -> None:
    """Load a Job by ID, dispatch to the correct executor, and run the
    normalization pipeline on completion.

    This is the primary entry point called by the scheduler / worker.
    """
    job: Job | None = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        logger.error("execute_job: job=%s not found", job_id)
        return

    connector: ConnectorInstance | None = (
        db.query(ConnectorInstance)
        .filter(ConnectorInstance.id == job.connector_instance_id)
        .first()
    )
    if connector is None:
        logger.error(
            "execute_job: connector_instance=%s not found for job=%s",
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
            "execute_job: connector_type=%s not found for connector=%s",
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
            "execute_job: no executor registered for connector_type code=%s",
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
        "execute_job: starting job=%s type=%s connector=%s enclave=%s",
        job.id,
        type_code,
        connector.id,
        connector.enclave_id,
    )

    # Dispatch
    try:
        executor(db, job, connector)
    except Exception as exc:
        logger.error(
            "execute_job: unhandled exception in executor for job=%s: %s",
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

    # Run normalization pipeline regardless of job success/failure -- partial
    # data may still have been ingested.
    try:
        _run_normalization_pipeline(db, enclave_id=connector.enclave_id)
    except Exception as norm_exc:
        logger.error(
            "execute_job: normalization pipeline failed for enclave=%s: %s",
            connector.enclave_id,
            norm_exc,
            exc_info=True,
        )
