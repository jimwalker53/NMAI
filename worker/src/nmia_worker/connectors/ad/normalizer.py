"""
Active Directory service-account normalizer.

Converts raw LDAP attribute dicts (as returned by ``collector.connect_and_collect``)
into a normalized representation suitable for Identity records.
"""

from __future__ import annotations

from typing import Any


def normalize_ad_finding(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Extract key fields from a raw AD service-account entry into a
    normalized format.

    Parameters
    ----------
    raw_data:
        Raw attribute dict from LDAP collection.  Expected keys include
        ``sAMAccountName``, ``distinguishedName``, ``objectSid``,
        ``servicePrincipalName``, ``userAccountControl_enabled``,
        ``pwdLastSet``, and ``lastLogonTimestamp``.

    Returns
    -------
    dict[str, Any]
        Normalized dict with the following structure::

            {
                "fingerprint": "<objectSid>",
                "identity_type": "svc_acct",
                "display_name": "<sAMAccountName or cn>",
                "normalized_data": {
                    "sam_account_name": ...,
                    "dn": ...,
                    "object_sid": ...,
                    "spn": [...],
                    "enabled": ...,
                    "password_last_set": ...,
                    "last_logon": ...,
                },
            }
    """
    sam = raw_data.get("sAMAccountName") or raw_data.get("cn", "Unknown")
    return {
        "fingerprint": raw_data.get("objectSid", ""),
        "identity_type": "svc_acct",
        "display_name": sam,
        "normalized_data": {
            "sam_account_name": raw_data.get("sAMAccountName"),
            "dn": raw_data.get("distinguishedName"),
            "object_sid": raw_data.get("objectSid"),
            "spn": raw_data.get("servicePrincipalName", []),
            "enabled": raw_data.get("userAccountControl_enabled", True),
            "password_last_set": raw_data.get("pwdLastSet"),
            "last_logon": raw_data.get("lastLogonTimestamp"),
        },
    }


def compute_fingerprint(raw_data: dict[str, Any]) -> str:
    """Compute the unique fingerprint for an AD service-account entry.

    The fingerprint is the ``objectSid`` attribute value, which uniquely
    identifies the security principal within the AD forest.

    Parameters
    ----------
    raw_data:
        Raw attribute dict from LDAP collection.

    Returns
    -------
    str
        The objectSid value, or an empty string if not present.
    """
    return str(raw_data.get("objectSid", ""))
