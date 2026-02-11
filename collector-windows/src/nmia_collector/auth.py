"""
NMIA Windows Collector - Authentication

Handles authentication between the collector and the NMIA server,
and (in future) validation of incoming requests to the collector API.
"""

from __future__ import annotations

from nmia_collector.settings import settings


def get_auth_headers() -> dict[str, str]:
    """
    Return HTTP headers for authenticating outbound requests to the NMIA
    server.

    If an API key is configured, it is sent as an ``X-API-Key`` header.
    Returns an empty dict when no key is set so callers can always unpack
    the result into their headers.
    """
    api_key = settings.NMIA_API_KEY
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


async def validate_request(request) -> bool:
    """
    Validate an incoming request to the collector API.

    TODO: Implement proper authentication for incoming requests.
    For MVP this always returns True (open access). Future options:
      - Shared secret / bearer token between NMIA server and collector
      - mTLS client certificate validation
      - IP allowlist

    Args:
        request: The incoming FastAPI Request object.

    Returns:
        True if the request is authorised, False otherwise.
    """
    # TODO: Implement request validation
    return True
