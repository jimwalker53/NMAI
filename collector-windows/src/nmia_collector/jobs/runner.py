"""
NMIA Windows Collector - Job Runner

Orchestrates the full collection pipeline as a background task:
  1. Export certificate inventory (certutil or mock)
  2. Optionally fetch individual cert blobs and parse SANs
  3. Push results to the NMIA server
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from nmia_collector.adcs.export_inventory import (
    generate_mock_inventory,
    parse_certutil_output,
    run_certutil_export,
)
from nmia_collector.adcs.fetch_cert_blob import fetch_cert_blob
from nmia_collector.adcs.parse_san import parse_san_from_cert_bytes
from nmia_collector.adcs.push_to_nmia import push_results
from nmia_collector.jobs.store import Job, job_store

logger = logging.getLogger("nmia.collector.jobs.runner")


async def run_collection_job(
    job_id: str,
    mode: str = "inventory",
    since_days: int = 30,
    max_records: int = 10000,
    max_san_fetch: int = 500,
    callback_url: str | None = None,
) -> None:
    """
    Main background task that performs the full collection pipeline.

    This function is meant to be launched via ``asyncio.create_task`` so
    that it runs concurrently with request handling.

    Args:
        job_id: The job ID (must already exist in the job store).
        mode: ``"inventory"`` or ``"inventory_san"``.
        since_days: How many days back to query certificates.
        max_records: Maximum number of records to return.
        max_san_fetch: Maximum number of certs to enrich with SAN data.
        callback_url: Optional override URL for the NMIA ingest endpoint.
    """
    job = job_store.get_job(job_id)
    if job is None:
        logger.error("Job %s not found in store", job_id)
        return

    try:
        job.status = "running"
        job_store.add_log(job_id, "Collection started")

        # Step 1: Get certificate inventory
        records = await _collect_certificates(job, mode, since_days, max_records)
        job.records_found = len(records)
        job_store.add_log(job_id, f"Collected {len(records)} certificate records")

        # Enforce max_records limit
        if len(records) > max_records:
            job_store.add_log(
                job_id,
                f"Truncating from {len(records)} to {max_records} records",
            )
            records = records[:max_records]

        # Step 2: Enrich with SAN data if requested
        if mode == "inventory_san":
            records = await _enrich_with_san(job, records, max_san_fetch)

        job.result = records

        # Step 3: Push to NMIA server
        push_result = await push_results(
            records=records,
            nmia_url=callback_url,
            job_id=job_id,
        )

        if push_result["error"]:
            job_store.add_log(job_id, f"Push note: {push_result['error']}")
        else:
            job.records_pushed = push_result["pushed"]
            job_store.add_log(
                job_id,
                f"Successfully pushed {push_result['pushed']} records "
                f"(HTTP {push_result['status_code']})",
            )

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job_store.add_log(job_id, "Collection completed successfully")

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.now(timezone.utc).isoformat()
        job_store.add_log(job_id, f"Collection failed: {exc}")
        logger.exception("Job %s failed", job_id[:8])


# -------------------------------------------------------------------------
# Private helpers
# -------------------------------------------------------------------------


async def _collect_certificates(
    job: Job,
    mode: str,
    since_days: int,
    max_records: int,
) -> list[dict]:
    """
    Collect certificate records via certutil or fall back to mock data.

    On a real Windows CA server, ``certutil -view`` is used.  When
    certutil is not available (e.g. during development on Linux/macOS),
    mock data is generated instead.
    """
    try:
        csv_text = await run_certutil_export(since_days, max_records)
        records = parse_certutil_output(csv_text)
        if records:
            return records
        job_store.add_log(
            job.job_id,
            "certutil returned no records; falling back to mock data",
        )
    except FileNotFoundError:
        job_store.add_log(
            job.job_id, "certutil not found; using mock data for testing"
        )
    except Exception as exc:
        job_store.add_log(
            job.job_id,
            f"certutil failed ({exc}); using mock data for testing",
        )

    # Mock fallback
    include_san = mode == "inventory_san"
    records = generate_mock_inventory(
        count=min(max_records, 50), include_san=include_san
    )
    job_store.add_log(
        job.job_id, f"Generated {len(records)} mock certificate records"
    )
    return records


async def _enrich_with_san(
    job: Job,
    records: list[dict],
    max_san_fetch: int,
) -> list[dict]:
    """
    For each certificate (up to *max_san_fetch*), fetch the full cert
    blob and extract SAN entries.

    Records that already have a ``san`` field (e.g. from mock data) are
    left as-is.
    """
    job_store.add_log(
        job.job_id,
        f"Enriching SANs for up to {max_san_fetch} of {len(records)} certs",
    )
    enriched_count = 0

    for i, rec in enumerate(records):
        if enriched_count >= max_san_fetch:
            break

        # Skip if already has SAN data (e.g. from mock generation)
        if "san" in rec and rec["san"]:
            enriched_count += 1
            continue

        serial = rec.get("serial_number", "")
        if not serial:
            continue

        try:
            cert_bytes = await fetch_cert_blob(serial)
            if cert_bytes:
                san_entries = parse_san_from_cert_bytes(cert_bytes)
                rec["san"] = san_entries
                enriched_count += 1
        except Exception as exc:
            job_store.add_log(
                job.job_id,
                f"Failed to fetch SAN for serial {serial}: {exc}",
            )

        # Log progress periodically
        if (i + 1) % 100 == 0:
            job_store.add_log(
                job.job_id,
                f"SAN enrichment progress: {i + 1}/{len(records)}",
            )

    job_store.add_log(
        job.job_id,
        f"SAN enrichment complete: {enriched_count} certs enriched",
    )
    return records
