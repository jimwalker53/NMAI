"""
NMIA Windows Collector - ADCS Certificate Inventory Export

Executes certutil to enumerate issued certificates from the local
Certificate Authority database and parses the CSV output.  Falls
back to mock data when certutil is unavailable (e.g. during
development on Linux / macOS).
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import logging
import random
import subprocess
import uuid
from datetime import datetime, timedelta, timezone

from nmia_collector.settings import settings

logger = logging.getLogger("nmia.collector.adcs.export_inventory")

# -------------------------------------------------------------------------
# certutil CSV column mapping
# -------------------------------------------------------------------------

# Column names emitted by certutil -view ... -out ... csv
# These map to the -out fields we request:
#   SerialNumber, CommonName, NotBefore, NotAfter,
#   CertificateTemplate, CertificateHash, RequesterName
_CERTUTIL_COLUMNS = [
    "serial_number",
    "common_name",
    "not_before",
    "not_after",
    "template_name",
    "thumbprint",
    "requester_name",
]

# -------------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------------


async def run_certutil_export(since_days: int, max_records: int) -> str:
    """
    Run ``certutil -view`` to enumerate issued certificates.

    Args:
        since_days: Only include certs whose NotAfter is within this many
            days from now.
        max_records: Maximum number of records to return (informational;
            the actual truncation is done by the caller).

    Returns:
        Raw CSV text from certutil stdout.

    Raises:
        FileNotFoundError: certutil is not available on the system.
        RuntimeError: certutil exited with a non-zero return code.
    """
    since_date = datetime.now(timezone.utc) - timedelta(days=since_days)
    since_str = since_date.strftime("%m/%d/%Y")

    cmd = [
        settings.CERTUTIL_PATH,
        "-view",
        "-restrict",
        f"NotAfter>={since_str},Disposition=20",
        "-out",
        "SerialNumber,CommonName,NotBefore,NotAfter,"
        "CertificateTemplate,CertificateHash,RequesterName",
        "csv",
    ]

    logger.info("Running: %s", " ".join(cmd))

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        ),
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        logger.warning("certutil exited %d: %s", result.returncode, stderr)
        raise RuntimeError(
            f"certutil failed (exit {result.returncode}): {stderr}"
        )

    logger.info("certutil produced %d bytes of output", len(result.stdout))
    return result.stdout


def parse_certutil_output(csv_text: str) -> list[dict]:
    """
    Parse CSV text produced by ``certutil -view ... csv``.

    certutil emits a header row with quoted column names followed by data
    rows.  Each row is mapped to a normalised dict suitable for pushing to
    the NMIA ingest API.

    Args:
        csv_text: Raw CSV text from certutil stdout.

    Returns:
        List of certificate record dicts.
    """
    records: list[dict] = []
    reader = csv.reader(io.StringIO(csv_text))

    # The first row is the header; we skip it and use our own mapping.
    header = next(reader, None)
    if header is None:
        return records

    for row in reader:
        if not row or len(row) < len(_CERTUTIL_COLUMNS):
            continue

        rec: dict = {}
        for idx, col_name in enumerate(_CERTUTIL_COLUMNS):
            value = row[idx].strip().strip('"')
            rec[col_name] = value

        # Parse dates into ISO-8601 strings
        rec["not_before"] = _parse_certutil_date(rec.get("not_before", ""))
        rec["not_after"] = _parse_certutil_date(rec.get("not_after", ""))

        # Compute a subject_dn from common_name (certutil -view does not
        # directly output full subject DN in CSV mode)
        cn = rec.get("common_name", "")
        rec["subject_dn"] = f"CN={cn}" if cn else ""

        # Placeholder issuer_dn - in production the CA name would be known
        # from the certutil connection or from configuration
        rec["issuer_dn"] = "CN=Enterprise-CA,DC=corp,DC=local"

        # Normalise thumbprint (remove spaces, lowercase)
        thumbprint = rec.get("thumbprint", "")
        rec["thumbprint"] = thumbprint.replace(" ", "").replace(":", "").lower()

        records.append(rec)

    return records


def generate_mock_inventory(count: int = 50, include_san: bool = False) -> list[dict]:
    """
    Generate mock certificate inventory records for testing.

    Produces a realistic distribution:
      - ~20 % expired certificates
      - ~15 % expiring within 30 days
      - ~15 % expiring within 90 days
      - ~50 % valid for longer periods

    Args:
        count: Number of mock records to generate.
        include_san: If True, add a ``san`` field with mock SAN entries.

    Returns:
        List of certificate record dicts.
    """
    import string

    now = datetime.now(timezone.utc)
    records: list[dict] = []

    for i in range(count):
        domain = random.choice(_MOCK_DOMAINS)
        hostname = random.choice(_MOCK_HOSTNAMES)
        cn = f"{hostname}.{domain}"
        template = random.choice(_MOCK_TEMPLATES)
        requester = f"{domain.split('.')[0]}\\svc-autoenroll"

        # Determine validity window based on distribution bucket
        bucket = random.random()
        if bucket < 0.20:
            # Expired
            not_before = now - timedelta(days=random.randint(400, 800))
            not_after = now - timedelta(days=random.randint(1, 60))
        elif bucket < 0.35:
            # Expiring within 30 days
            not_before = now - timedelta(days=random.randint(335, 365))
            not_after = now + timedelta(days=random.randint(1, 30))
        elif bucket < 0.50:
            # Expiring within 90 days
            not_before = now - timedelta(days=random.randint(275, 335))
            not_after = now + timedelta(days=random.randint(31, 90))
        else:
            # Valid for a longer period
            not_before = now - timedelta(days=random.randint(30, 300))
            not_after = now + timedelta(days=random.randint(91, 730))

        serial = uuid.uuid4().hex[:16].upper()
        thumbprint = hashlib.sha1(
            f"{serial}-{cn}-{i}".encode()
        ).hexdigest().lower()

        rec = {
            "serial_number": serial,
            "common_name": cn,
            "subject_dn": f"CN={cn}",
            "issuer_dn": f"CN=Enterprise-CA,DC={domain.replace('.', ',DC=')}",
            "not_before": not_before.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "not_after": not_after.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "template_name": template,
            "thumbprint": thumbprint,
            "requester_name": requester,
        }

        if include_san:
            rec["san"] = _generate_mock_san(hostname, domain)

        records.append(rec)

    return records


# -------------------------------------------------------------------------
# Private helpers
# -------------------------------------------------------------------------


def _parse_certutil_date(date_str: str) -> str:
    """
    Parse a date string from certutil output into ISO-8601 format.

    certutil uses the system locale for dates.  Common formats:
      - ``1/15/2025 3:30 PM``  (US locale)
      - ``2025-01-15 15:30``   (ISO-ish)

    Returns the original string if parsing fails.
    """
    formats = [
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return date_str


# -------------------------------------------------------------------------
# Mock data constants
# -------------------------------------------------------------------------

_MOCK_TEMPLATES = [
    "WebServer",
    "Computer",
    "User",
    "DomainController",
    "CodeSigning",
    "EFSRecovery",
    "IPSECIntermediateOffline",
    "SmartcardLogon",
    "WorkstationAuthentication",
    "ServerAuthentication",
]

_MOCK_DOMAINS = [
    "corp.local",
    "internal.example.com",
    "ad.contoso.com",
    "pki.fabrikam.net",
]

_MOCK_HOSTNAMES = [
    "web01",
    "web02",
    "app-server",
    "dc01",
    "dc02",
    "exchange",
    "sql-prod",
    "fileserver",
    "vpn-gw",
    "radius",
    "ldap-proxy",
    "citrix01",
    "print-srv",
    "backup-srv",
    "monitoring",
    "jenkins",
    "gitlab",
    "nexus",
    "vault",
    "k8s-node01",
]


def _generate_mock_san(hostname: str, domain: str) -> list[dict]:
    """Generate a realistic set of SAN entries for a mock certificate."""
    import string

    san_entries: list[dict] = []

    # Always include the FQDN
    san_entries.append({"type": "dnsName", "value": f"{hostname}.{domain}"})

    # Sometimes include a short name
    if random.random() < 0.5:
        san_entries.append({"type": "dnsName", "value": hostname})

    # Sometimes include a wildcard
    if random.random() < 0.2:
        san_entries.append({"type": "dnsName", "value": f"*.{domain}"})

    # Sometimes include an IP address
    if random.random() < 0.4:
        ip = f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        san_entries.append({"type": "iPAddress", "value": ip})

    # Sometimes include an email (mostly for User template certs)
    if random.random() < 0.15:
        user = "".join(random.choices(string.ascii_lowercase, k=6))
        san_entries.append(
            {"type": "rfc822Name", "value": f"{user}@{domain}"}
        )

    return san_entries
