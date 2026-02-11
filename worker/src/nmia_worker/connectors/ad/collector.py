"""
Active Directory LDAP collection logic.

Connects to an AD domain controller via LDAP and retrieves service-account
objects with their key attributes.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Attributes requested from the directory
_LDAP_ATTRIBUTES = [
    "sAMAccountName",
    "cn",
    "distinguishedName",
    "objectSid",
    "servicePrincipalName",
    "userAccountControl",
    "pwdLastSet",
    "lastLogonTimestamp",
]


def connect_and_collect(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Connect to an LDAP server and search for service accounts.

    Parameters
    ----------
    config:
        Connector configuration dict containing:
        - server (str): LDAP host (default ``"localhost"``)
        - port (int): LDAP port (default ``389``)
        - use_ssl (bool): whether to use LDAPS (default ``False``)
        - bind_dn (str): bind distinguished name
        - bind_password (str): bind credential
        - search_base (str): base DN for the search
        - search_filter (str): LDAP search filter (optional; defaults to
          service-account filter)

    Returns
    -------
    list[dict[str, Any]]
        A list of raw attribute dicts, one per LDAP entry found.  Each dict
        has string keys matching the requested LDAP attribute names.  Binary
        values are hex-encoded and datetime values are ISO-formatted.  The
        ``userAccountControl`` bitmask is replaced with a boolean
        ``userAccountControl_enabled`` key.
    """
    server = config.get("server", "localhost")
    port = config.get("port", 389)
    use_ssl = config.get("use_ssl", False)
    bind_dn = config.get("bind_dn", "")
    bind_password = config.get("bind_password", "")
    search_base = config.get("search_base", "")
    search_filter = config.get(
        "search_filter",
        "(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))",
    )

    # Import ldap3 inside the function so the rest of the module does not
    # hard-depend on it (useful for testing / environments without ldap3).
    import ldap3  # type: ignore[import-untyped]
    from ldap3 import Connection, Server, SUBTREE  # type: ignore[import-untyped]

    ldap_server = Server(server, port=int(port), use_ssl=use_ssl, get_info=ldap3.ALL)
    conn = Connection(
        ldap_server,
        user=bind_dn,
        password=bind_password,
        auto_bind=True,
        read_only=True,
        receive_timeout=30,
    )

    logger.info(
        "connect_and_collect: connected to %s:%s (ssl=%s)",
        server,
        port,
        use_ssl,
    )

    conn.search(
        search_base=search_base,
        search_filter=search_filter,
        search_scope=SUBTREE,
        attributes=_LDAP_ATTRIBUTES,
    )

    entries = conn.entries
    results: list[dict[str, Any]] = []

    for entry in entries:
        try:
            entry_dict: dict[str, Any] = {}
            for attr_name in _LDAP_ATTRIBUTES:
                raw_val = getattr(entry, attr_name, None)
                if raw_val is not None:
                    val = raw_val.value
                    # Lists with a single element can be unwound for simple
                    # scalar fields, but keep lists for multi-value attrs.
                    if (
                        isinstance(val, list)
                        and len(val) == 1
                        and attr_name != "servicePrincipalName"
                    ):
                        val = val[0]
                    entry_dict[attr_name] = val

            # Derive enabled flag from userAccountControl bitmask
            uac = entry_dict.pop("userAccountControl", None)
            if uac is not None:
                try:
                    uac_int = int(uac)
                    # Bit 0x0002 = ACCOUNTDISABLE
                    entry_dict["userAccountControl_enabled"] = not bool(
                        uac_int & 0x0002
                    )
                except (ValueError, TypeError):
                    entry_dict["userAccountControl_enabled"] = True
            else:
                entry_dict["userAccountControl_enabled"] = True

            # Convert non-serialisable types to strings
            for k, v in entry_dict.items():
                if isinstance(v, bytes):
                    entry_dict[k] = v.hex()
                elif isinstance(v, datetime):
                    entry_dict[k] = v.isoformat()

            results.append(entry_dict)

        except Exception as exc:
            logger.error(
                "connect_and_collect: failed to process LDAP entry: %s",
                exc,
                exc_info=True,
            )

    conn.unbind()

    logger.info(
        "connect_and_collect: retrieved %d entries from %s",
        len(results),
        server,
    )
    return results
