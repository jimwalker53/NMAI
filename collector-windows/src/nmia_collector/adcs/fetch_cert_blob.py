"""
NMIA Windows Collector - Certificate Blob Fetching

Fetches individual certificate blobs (DER / PEM) from the local
Certificate Authority using certutil.  Falls back gracefully when
certutil is unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess

from nmia_collector.settings import settings

logger = logging.getLogger("nmia.collector.adcs.fetch_cert_blob")


async def fetch_cert_blob(serial_number: str) -> bytes | None:
    """
    Fetch the binary certificate blob for a given serial number using
    ``certutil -view``.

    The command outputs the certificate in PEM format (with
    ``-----BEGIN CERTIFICATE-----`` / ``-----END CERTIFICATE-----``
    markers).  If PEM markers are not found the raw stdout bytes are
    returned (which may be DER-encoded).

    Args:
        serial_number: The certificate serial number to look up.

    Returns:
        Certificate bytes (PEM or DER), or ``None`` if certutil is not
        available or the lookup failed.
    """
    cmd = [
        settings.CERTUTIL_PATH,
        "-view",
        "-restrict",
        f"SerialNumber={serial_number}",
        "-out",
        "RawCertificate",
    ]

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
            ),
        )

        if result.returncode != 0:
            logger.debug(
                "certutil returned %d for serial %s",
                result.returncode,
                serial_number,
            )
            return None

        # certutil outputs the certificate in a text format with
        # -----BEGIN CERTIFICATE----- / -----END CERTIFICATE----- markers.
        # We extract the PEM block.
        stdout_text = result.stdout.decode("utf-8", errors="replace")
        pem_start = stdout_text.find("-----BEGIN CERTIFICATE-----")
        pem_end = stdout_text.find("-----END CERTIFICATE-----")

        if pem_start >= 0 and pem_end >= 0:
            pem_block = stdout_text[
                pem_start : pem_end + len("-----END CERTIFICATE-----")
            ]
            return pem_block.encode("ascii")

        # If no PEM markers, return raw bytes (might be DER)
        return result.stdout if result.stdout else None

    except FileNotFoundError:
        logger.debug("certutil not found; cannot fetch cert blob")
        return None
    except subprocess.TimeoutExpired:
        logger.warning(
            "certutil timed out fetching serial %s", serial_number
        )
        return None


async def fetch_cert_blobs_batch(
    serial_numbers: list[str],
    max_fetch: int = 500,
) -> dict[str, bytes]:
    """
    Fetch certificate blobs for multiple serial numbers.

    Fetches up to *max_fetch* certificates sequentially (certutil does
    not support batch retrieval).

    Args:
        serial_numbers: List of serial numbers to look up.
        max_fetch: Maximum number of blobs to retrieve.

    Returns:
        Dict mapping serial number to certificate bytes.  Entries that
        could not be fetched are omitted.
    """
    results: dict[str, bytes] = {}
    fetched = 0

    for serial in serial_numbers:
        if fetched >= max_fetch:
            break

        blob = await fetch_cert_blob(serial)
        if blob is not None:
            results[serial] = blob
            fetched += 1

        # Log progress periodically
        if (fetched % 100) == 0 and fetched > 0:
            logger.info(
                "Fetched %d / %d cert blobs", fetched, len(serial_numbers)
            )

    logger.info(
        "Batch fetch complete: %d of %d serials retrieved",
        len(results),
        len(serial_numbers),
    )
    return results
