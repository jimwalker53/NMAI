"""Convenience re-exports of connector-related ORM models.

The canonical model definitions live in ``nmia.core.models``.  This module
re-exports them so that code within the ``connectors`` package can use
short imports such as::

    from nmia.connectors.models import ConnectorInstance, Job
"""

from nmia.core.models import ConnectorInstance, ConnectorType, Job

__all__ = [
    "ConnectorInstance",
    "ConnectorType",
    "Job",
]
