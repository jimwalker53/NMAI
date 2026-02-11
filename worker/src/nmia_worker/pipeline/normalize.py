"""
Normalization pipeline: Finding (raw) -> Identity (normalized).

Identity fingerprint rules:
- AD svc_acct: objectSid from raw_data
- ADCS cert: issuer_dn + "|" + serial_number from raw_data

Process:
1. Query un-processed findings (findings whose id is not yet in any
   Identity.finding_ids)
2. For each finding, compute fingerprint and normalize
3. Upsert Identity: if fingerprint+enclave exists, update last_seen and
   append finding_id; else create new
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from nmia_worker.connectors.ad.normalizer import normalize_ad_finding
from nmia_worker.connectors.adcs.normalizer import normalize_cert_finding

# Import shared models (sys.path is set up by scheduler.py at import time)
from nmia.core.models import Finding, Identity  # noqa: E402

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Source-type dispatchers
# ---------------------------------------------------------------------------

_SOURCE_TYPE_BUILDERS: dict[str, Any] = {
    "ad_svc_acct": normalize_ad_finding,
    "adcs_cert": normalize_cert_finding,
}


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------

def normalize_findings(
    db: Session,
    enclave_id: UUID | None = None,
) -> int:
    """Normalize raw Findings into Identities.

    Parameters
    ----------
    db:
        An active SQLAlchemy session.
    enclave_id:
        If provided, only process findings scoped to this enclave.

    Returns
    -------
    int
        The number of identities created or updated.
    """
    # ------------------------------------------------------------------
    # 1. Load all findings, optionally scoped to an enclave
    # ------------------------------------------------------------------
    query = db.query(Finding)
    if enclave_id is not None:
        query = query.filter(Finding.enclave_id == enclave_id)
    findings: list[Finding] = query.all()

    if not findings:
        logger.info(
            "normalize_findings: no findings to process (enclave=%s)", enclave_id
        )
        return 0

    # ------------------------------------------------------------------
    # 2. Build a set of finding IDs already tracked by identities so we
    #    can skip findings that have already been ingested.
    # ------------------------------------------------------------------
    identity_query = db.query(Identity)
    if enclave_id is not None:
        identity_query = identity_query.filter(Identity.enclave_id == enclave_id)
    existing_identities: list[Identity] = identity_query.all()

    already_processed_ids: set[str] = set()
    for ident in existing_identities:
        if ident.finding_ids:
            for fid in ident.finding_ids:
                already_processed_ids.add(str(fid))

    # ------------------------------------------------------------------
    # 3. Process each un-processed finding
    # ------------------------------------------------------------------
    upserted_count = 0
    now = _utcnow()

    for finding in findings:
        finding_id_str = str(finding.id)
        if finding_id_str in already_processed_ids:
            continue

        builder = _SOURCE_TYPE_BUILDERS.get(finding.source_type)
        if builder is None:
            logger.warning(
                "normalize_findings: unsupported source_type=%s for finding=%s",
                finding.source_type,
                finding.id,
            )
            continue

        raw_data: dict[str, Any] = finding.raw_data or {}
        identity_info = builder(raw_data)
        fp = identity_info["fingerprint"]
        if not fp:
            logger.warning(
                "normalize_findings: empty fingerprint for finding=%s", finding.id
            )
            continue

        # Upsert
        existing: Identity | None = (
            db.query(Identity)
            .filter(
                and_(
                    Identity.fingerprint == fp,
                    Identity.enclave_id == finding.enclave_id,
                )
            )
            .first()
        )

        if existing is not None:
            # Update existing identity
            existing.last_seen = now
            existing.display_name = identity_info["display_name"]

            # Merge normalized_data: new values overwrite old keys
            merged = dict(existing.normalized_data or {})
            for key, value in identity_info["normalized_data"].items():
                if value is not None:
                    merged[key] = value
            existing.normalized_data = merged

            # Append finding id
            current_fids = list(existing.finding_ids or [])
            if finding_id_str not in [str(f) for f in current_fids]:
                current_fids.append(finding_id_str)
                existing.finding_ids = current_fids

            logger.debug(
                "normalize_findings: updated identity=%s fingerprint=%s",
                existing.id,
                fp,
            )
        else:
            # Create new identity
            new_identity = Identity(
                enclave_id=finding.enclave_id,
                identity_type=identity_info["identity_type"],
                display_name=identity_info["display_name"],
                fingerprint=fp,
                normalized_data=identity_info["normalized_data"],
                first_seen=now,
                last_seen=now,
                finding_ids=[finding_id_str],
                risk_score=0.0,
            )
            db.add(new_identity)
            logger.debug(
                "normalize_findings: created identity fingerprint=%s enclave=%s",
                fp,
                finding.enclave_id,
            )

        upserted_count += 1

    db.flush()
    logger.info(
        "normalize_findings: upserted %d identities (enclave=%s)",
        upserted_count,
        enclave_id,
    )
    return upserted_count
