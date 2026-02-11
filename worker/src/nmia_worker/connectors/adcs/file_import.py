"""
ADCS CSV file import handler.

Parses certificate records from CSV content (as uploaded via the API ingest
endpoint) and provides fingerprint computation.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_csv(content: str | bytes) -> list[dict[str, Any]]:
    """Parse CSV content into a list of certificate record dicts.

    Parameters
    ----------
    content:
        Raw CSV data as a string or bytes.  The first row must be a header
        row.  Expected columns (case-insensitive) include:
        ``subject_dn``, ``issuer_dn``, ``serial_number``, ``not_before``,
        ``not_after``, ``template_name``, ``san``, ``thumbprint``.

    Returns
    -------
    list[dict[str, Any]]
        One dict per CSV row with keys lowered and stripped.
    """
    if isinstance(content, bytes):
        content = content.decode("utf-8-sig")  # handle BOM if present

    reader = csv.DictReader(io.StringIO(content))
    records: list[dict[str, Any]] = []

    for row_num, row in enumerate(reader, start=2):  # data rows start at line 2
        try:
            # Normalize keys: strip whitespace and lowercase
            normalized: dict[str, Any] = {}
            for key, value in row.items():
                if key is None:
                    continue
                clean_key = key.strip().lower().replace(" ", "_")
                normalized[clean_key] = value.strip() if value else ""

            # Skip entirely empty rows
            if not any(normalized.values()):
                continue

            # SAN may be a semicolon-delimited list in the CSV
            san_raw = normalized.get("san", "")
            if san_raw:
                normalized["san"] = [
                    s.strip() for s in san_raw.split(";") if s.strip()
                ]
            else:
                normalized["san"] = []

            records.append(normalized)

        except Exception as exc:
            logger.warning(
                "parse_csv: skipping row %d due to error: %s", row_num, exc
            )

    logger.info("parse_csv: parsed %d certificate records from CSV", len(records))
    return records


def compute_fingerprint(record: dict[str, Any]) -> str:
    """Compute a unique fingerprint for an ADCS certificate record.

    The fingerprint is ``"{issuer_dn}|{serial_number}"``, which uniquely
    identifies a certificate within a given CA.

    Parameters
    ----------
    record:
        A certificate record dict (as returned by :func:`parse_csv`).

    Returns
    -------
    str
        The composite fingerprint string.
    """
    issuer_dn = record.get("issuer_dn", "")
    serial_number = record.get("serial_number", "")
    return f"{issuer_dn}|{serial_number}"
