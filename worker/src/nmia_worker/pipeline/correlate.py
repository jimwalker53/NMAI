"""
Identity correlation pipeline.

Correlates identities to systems based on SANs (Subject Alternative Names),
SPNs (Service Principal Names), and naming patterns.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

# Import shared models (sys.path is set up by scheduler.py at import time)
from nmia.core.models import Identity  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_dns_from_san(san_list: list[Any]) -> list[str]:
    """Pull DNS names from a SAN list.

    SAN entries may be plain strings (assumed DNS) or dicts like
    ``{"type": "dnsName", "value": "host.example.com"}``.
    """
    dns_names: list[str] = []
    for entry in san_list:
        if isinstance(entry, dict):
            entry_type = entry.get("type", "").lower()
            if entry_type in ("dnsname", "dns", "ipaddress", "ip"):
                value = entry.get("value", "")
                if value:
                    dns_names.append(value)
        elif isinstance(entry, str) and entry:
            dns_names.append(entry)
    return dns_names


def _extract_host_from_spn(spn: str) -> str | None:
    """Extract the host portion from an SPN string (format: ``service/host``).

    Strips port suffixes if present (``service/host:port``).
    """
    if "/" in spn:
        parts = spn.split("/", 1)
        host = parts[1]
        # Strip port if present
        if ":" in host:
            host = host.split(":")[0]
        return host.strip() if host.strip() else None
    return None


# ---------------------------------------------------------------------------
# Correlate
# ---------------------------------------------------------------------------

def correlate_identities(
    db: Session,
    enclave_id: UUID | None = None,
) -> int:
    """Correlate identities to systems based on SANs, SPNs, and naming
    patterns.

    Parameters
    ----------
    db:
        An active SQLAlchemy session.
    enclave_id:
        If provided, only process identities scoped to this enclave.

    Returns
    -------
    int
        The number of identities correlated (i.e. whose ``linked_system``
        was set or changed).
    """
    query = db.query(Identity)
    if enclave_id is not None:
        query = query.filter(Identity.enclave_id == enclave_id)
    identities: list[Identity] = query.all()

    correlated = 0

    for identity in identities:
        nd: dict[str, Any] = identity.normalized_data or {}
        linked: str | None = None

        if identity.identity_type == "cert":
            # Try SAN DNS names first
            san_list = nd.get("san", [])
            dns_names = _extract_dns_from_san(san_list)
            if dns_names:
                linked = dns_names[0]
            else:
                # Fallback: parse CN from subject_dn for hostname.domain pattern
                subject_dn = nd.get("subject_dn", "")
                if subject_dn:
                    # subject_dn is typically "CN=hostname.domain.com,OU=..."
                    for part in subject_dn.split(","):
                        part = part.strip()
                        if part.upper().startswith("CN="):
                            cn_value = part[3:].strip()
                            # Check for hostname.domain pattern (at least one dot)
                            if "." in cn_value:
                                linked = cn_value
                            break

        elif identity.identity_type == "svc_acct":
            spn_list = nd.get("spn", [])
            if isinstance(spn_list, list) and spn_list:
                # Extract host from the first SPN
                first_spn = (
                    spn_list[0] if isinstance(spn_list[0], str) else str(spn_list[0])
                )
                host = _extract_host_from_spn(first_spn)
                if host:
                    linked = host

        if linked and linked != identity.linked_system:
            identity.linked_system = linked
            correlated += 1
            logger.debug(
                "correlate_identities: identity=%s linked_system=%s",
                identity.id,
                linked,
            )

    db.flush()
    logger.info(
        "correlate_identities: correlated %d identities (enclave=%s)",
        correlated,
        enclave_id,
    )
    return correlated
