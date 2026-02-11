"""
ADCS certificate normalizer.

Converts raw certificate record dicts into a normalized representation
suitable for Identity records.
"""

from __future__ import annotations

from typing import Any


def normalize_cert_finding(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw ADCS certificate record into a
    normalized format.

    Parameters
    ----------
    raw_data:
        Raw certificate record dict.  Expected keys include
        ``subject_dn``, ``issuer_dn``, ``serial_number``, ``not_before``,
        ``not_after``, ``template_name``, ``san``, ``thumbprint``.

    Returns
    -------
    dict[str, Any]
        Normalized dict with the following structure::

            {
                "fingerprint": "<issuer_dn>|<serial_number>",
                "identity_type": "cert",
                "display_name": "<subject_dn or common_name>",
                "normalized_data": {
                    "subject_dn": ...,
                    "issuer_dn": ...,
                    "serial_number": ...,
                    "not_before": ...,
                    "not_after": ...,
                    "template_name": ...,
                    "san": [...],
                    "thumbprint": ...,
                },
            }
    """
    issuer_dn = raw_data.get("issuer_dn", "")
    serial_number = raw_data.get("serial_number", "")
    display = raw_data.get("subject_dn") or raw_data.get("common_name", "Unknown Cert")

    return {
        "fingerprint": f"{issuer_dn}|{serial_number}",
        "identity_type": "cert",
        "display_name": display,
        "normalized_data": {
            "subject_dn": raw_data.get("subject_dn"),
            "issuer_dn": issuer_dn,
            "serial_number": serial_number,
            "not_before": raw_data.get("not_before"),
            "not_after": raw_data.get("not_after"),
            "template_name": raw_data.get("template_name"),
            "san": raw_data.get("san", []),
            "thumbprint": raw_data.get("thumbprint"),
        },
    }


def compute_fingerprint(raw_data: dict[str, Any]) -> str:
    """Compute a unique fingerprint for an ADCS certificate record.

    The fingerprint is ``"{issuer_dn}|{serial_number}"``, which uniquely
    identifies a certificate within a given CA.

    Parameters
    ----------
    raw_data:
        Raw certificate record dict.

    Returns
    -------
    str
        The composite fingerprint string.
    """
    issuer_dn = raw_data.get("issuer_dn", "")
    serial_number = raw_data.get("serial_number", "")
    return f"{issuer_dn}|{serial_number}"
