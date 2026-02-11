"""
NMIA Windows Collector - SAN Parsing

Extracts Subject Alternative Name (SAN) entries from X.509 certificate
bytes using the ``cryptography`` library.
"""

from __future__ import annotations

import ipaddress
import logging

from cryptography import x509
from cryptography.x509.oid import ExtensionOID

logger = logging.getLogger("nmia.collector.adcs.parse_san")


def parse_san_from_cert_bytes(cert_bytes: bytes) -> list[dict]:
    """
    Extract Subject Alternative Name entries from certificate bytes.

    Attempts to load the certificate as DER first, then PEM.  Extracts
    ``dnsName``, ``iPAddress``, and ``rfc822Name`` entries from the SAN
    extension.

    Args:
        cert_bytes: Raw certificate bytes in DER or PEM encoding.

    Returns:
        List of dicts with keys ``type`` and ``value``, e.g.::

            [{"type": "dnsName", "value": "www.example.com"},
             {"type": "iPAddress", "value": "10.0.0.1"}]

        Returns an empty list if no SAN extension is present.
    """
    cert = _load_certificate(cert_bytes)
    if cert is None:
        return []

    try:
        san_ext = cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME
        )
    except x509.ExtensionNotFound:
        return []

    san_value: x509.SubjectAlternativeName = san_ext.value
    results: list[dict] = []

    # DNS names
    for dns_name in san_value.get_values_for_type(x509.DNSName):
        results.append({"type": "dnsName", "value": dns_name})

    # IP addresses
    for ip_addr in san_value.get_values_for_type(x509.IPAddress):
        # ip_addr can be IPv4Address, IPv6Address, IPv4Network, or IPv6Network
        results.append({"type": "iPAddress", "value": str(ip_addr)})

    # RFC 822 (email) names
    for email in san_value.get_values_for_type(x509.RFC822Name):
        results.append({"type": "rfc822Name", "value": email})

    return results


def parse_san_from_pem(pem_str: str) -> list[dict]:
    """
    Parse SAN entries from a PEM-encoded certificate string.

    This is a convenience wrapper around :func:`parse_san_from_cert_bytes`
    for callers that already have the certificate as a PEM string rather
    than raw bytes.

    Args:
        pem_str: PEM-encoded certificate string (including the
            ``-----BEGIN CERTIFICATE-----`` and
            ``-----END CERTIFICATE-----`` markers).

    Returns:
        List of SAN entry dicts (same format as
        :func:`parse_san_from_cert_bytes`).
    """
    return parse_san_from_cert_bytes(pem_str.encode("ascii"))


# -------------------------------------------------------------------------
# Private helpers
# -------------------------------------------------------------------------


def _load_certificate(cert_bytes: bytes) -> x509.Certificate | None:
    """Try loading a certificate as DER, then PEM. Return None on failure."""
    # Try DER first (binary format)
    try:
        return x509.load_der_x509_certificate(cert_bytes)
    except Exception:
        pass

    # Try PEM (text format)
    try:
        return x509.load_pem_x509_certificate(cert_bytes)
    except Exception:
        pass

    logger.warning("Failed to parse certificate bytes as DER or PEM")
    return None
