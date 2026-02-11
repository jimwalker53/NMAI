"""
NMIA Windows Collector - Push Results to NMIA Server

Sends collected certificate records to the NMIA platform ingest API
using asynchronous HTTP calls via httpx.
"""

from __future__ import annotations

import logging

import httpx

from nmia_collector.auth import get_auth_headers
from nmia_collector.settings import settings

logger = logging.getLogger("nmia.collector.adcs.push_to_nmia")


async def push_results(
    records: list[dict],
    nmia_url: str | None = None,
    connector_id: str | None = None,
    job_id: str = "",
) -> dict:
    """
    POST collected certificate records to the NMIA ingest endpoint.

    Args:
        records: List of certificate record dicts to push.
        nmia_url: Full callback URL override.  When *None*, the URL is
            constructed from ``settings.NMIA_SERVER_URL`` and the
            *connector_id*.
        connector_id: Connector instance ID.  Falls back to the value
            from settings if not provided.
        job_id: The job ID to include as a query parameter.

    Returns:
        A dict summarising the result::

            {"pushed": <int>, "status_code": <int>, "error": <str|None>}
    """
    connector_id = connector_id or settings.CONNECTOR_INSTANCE_ID
    if not connector_id:
        msg = (
            "CONNECTOR_INSTANCE_ID not configured; skipping push to NMIA. "
            "Records are available via /jobs/{job_id}/result"
        )
        logger.warning(msg)
        return {"pushed": 0, "status_code": 0, "error": msg}

    # Determine the ingest URL
    if nmia_url:
        url = nmia_url
    else:
        base = settings.NMIA_SERVER_URL.rstrip("/")
        url = f"{base}/api/v1/ingest/adcs/{connector_id}?job_id={job_id}"

    payload = {
        "connector_instance_id": connector_id,
        "records": records,
    }

    headers: dict[str, str] = {"Content-Type": "application/json"}
    headers.update(get_auth_headers())

    logger.info("Pushing %d records to %s", len(records), url)

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)

        if response.status_code in (200, 201, 202):
            logger.info(
                "Successfully pushed %d records (HTTP %d)",
                len(records),
                response.status_code,
            )
            return {
                "pushed": len(records),
                "status_code": response.status_code,
                "error": None,
            }

        body = response.text[:500]
        msg = f"NMIA server returned HTTP {response.status_code}: {body}"
        logger.warning(msg)
        return {
            "pushed": 0,
            "status_code": response.status_code,
            "error": msg,
        }

    except httpx.ConnectError:
        msg = f"Cannot connect to NMIA server at {url}"
        logger.warning(msg)
        return {"pushed": 0, "status_code": 0, "error": msg}
    except Exception as exc:
        msg = f"Failed to push to NMIA: {exc}"
        logger.exception(msg)
        return {"pushed": 0, "status_code": 0, "error": msg}
