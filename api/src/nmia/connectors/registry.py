"""Connector type registry.

Provides a static registry of known connector types, their metadata, and
required configuration fields.  This registry is used for validation and
documentation purposes; the canonical connector type records live in the
database (``connector_types`` table).
"""

from __future__ import annotations

from typing import Any

CONNECTOR_TYPES: dict[str, dict[str, Any]] = {
    "ad_ldap": {
        "code": "ad_ldap",
        "name": "Active Directory (LDAP)",
        "description": "Connects to Active Directory via LDAP to discover service accounts and other non-human identities.",
        "required_config": ["server", "bind_dn", "bind_password", "search_base"],
        "optional_config": ["port", "use_ssl", "search_filter"],
    },
    "adcs_file": {
        "code": "adcs_file",
        "name": "AD Certificate Services (File)",
        "description": "Ingests certificate data from exported CSV / JSON files produced by ADCS.",
        "required_config": [],
        "optional_config": ["file_path", "watch_directory"],
    },
    "adcs_remote": {
        "code": "adcs_remote",
        "name": "AD Certificate Services (Remote)",
        "description": "Connects to a remote ADCS CA to enumerate issued certificates.",
        "required_config": ["ca_host"],
        "optional_config": ["ca_port", "use_ssl", "auth_method"],
    },
    "keyfactor": {
        "code": "keyfactor",
        "name": "Keyfactor Command",
        "description": "Integrates with Keyfactor Command for certificate lifecycle management. (Placeholder -- not yet implemented.)",
        "required_config": ["api_url", "api_key"],
        "optional_config": ["verify_ssl"],
    },
    "ejbca": {
        "code": "ejbca",
        "name": "EJBCA",
        "description": "Integrates with EJBCA Enterprise for certificate authority operations. (Placeholder -- not yet implemented.)",
        "required_config": ["api_url", "client_cert", "client_key"],
        "optional_config": ["ca_name", "verify_ssl"],
    },
    "vault": {
        "code": "vault",
        "name": "HashiCorp Vault",
        "description": "Integrates with HashiCorp Vault PKI secrets engine. (Placeholder -- not yet implemented.)",
        "required_config": ["vault_addr", "vault_token"],
        "optional_config": ["pki_mount", "verify_ssl"],
    },
}


def get_connector_type(code: str) -> dict[str, Any] | None:
    """Return the registry entry for the given connector type code, or ``None``
    if the code is not registered.
    """
    return CONNECTOR_TYPES.get(code)


def list_connector_types() -> list[dict[str, Any]]:
    """Return all registered connector types as a list of dicts."""
    return list(CONNECTOR_TYPES.values())
