"""Connector management endpoints (enclave-scoped)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from nmia.core.db import get_db
from nmia.core.models import ConnectorInstance, ConnectorType, Job
from nmia.auth.models import User
from nmia.auth.rbac import (
    get_current_user,
    get_user_enclaves,
    require_enclave_access,
    require_enclave_role,
    require_role,
)
from nmia.connectors.schemas import (
    ConnectorInstanceCreate,
    ConnectorInstanceOut,
    ConnectorInstanceUpdate,
    ConnectorTypeOut,
    JobOut,
)

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


# -- Connector Types ----------------------------------------------------------

@router.get("/types", response_model=list[ConnectorTypeOut])
def list_connector_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConnectorType]:
    """Return all registered connector types."""
    return db.query(ConnectorType).order_by(ConnectorType.code).all()


# -- Connector Instances ------------------------------------------------------

@router.get("/", response_model=list[ConnectorInstanceOut])
def list_connectors(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConnectorInstance]:
    """List connector instances the caller has access to (filtered by enclave
    membership).
    """
    enclave_ids = get_user_enclaves(current_user, db)
    if not enclave_ids:
        return []
    return (
        db.query(ConnectorInstance)
        .filter(ConnectorInstance.enclave_id.in_(enclave_ids))
        .order_by(ConnectorInstance.name)
        .all()
    )


@router.post("/", response_model=ConnectorInstanceOut, status_code=status.HTTP_201_CREATED)
def create_connector(
    body: ConnectorInstanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectorInstance:
    """Create a connector instance.  Requires ``operator`` or ``admin`` role in
    the target enclave.
    """
    require_enclave_role(body.enclave_id, current_user, db, "operator", "admin")

    connector_type = (
        db.query(ConnectorType)
        .filter(ConnectorType.code == body.connector_type_code)
        .first()
    )
    if connector_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector type '{body.connector_type_code}' not found",
        )

    instance = ConnectorInstance(
        connector_type_id=connector_type.id,
        enclave_id=body.enclave_id,
        name=body.name,
        config=body.config,
        cron_expression=body.cron_expression,
        created_by=current_user.id,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.get("/{connector_id}", response_model=ConnectorInstanceOut)
def get_connector(
    connector_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectorInstance:
    """Get a connector instance by ID (checks enclave access)."""
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_access(instance.enclave_id, current_user, db)
    return instance


@router.put("/{connector_id}", response_model=ConnectorInstanceOut)
def update_connector(
    connector_id: UUID,
    body: ConnectorInstanceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectorInstance:
    """Update a connector instance.  Requires ``operator`` or ``admin`` in the
    connector's enclave.
    """
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_role(instance.enclave_id, current_user, db, "operator", "admin")

    if body.name is not None:
        instance.name = body.name
    if body.config is not None:
        instance.config = body.config
    if body.cron_expression is not None:
        instance.cron_expression = body.cron_expression
    if body.is_enabled is not None:
        instance.is_enabled = body.is_enabled

    db.commit()
    db.refresh(instance)
    return instance


@router.delete("/{connector_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_connector(
    connector_id: UUID,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Response:
    """Delete a connector instance (admin only)."""
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    db.delete(instance)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- Test / Run / Jobs --------------------------------------------------------

@router.post("/{connector_id}/test")
def test_connector(
    connector_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Test connectivity for a connector instance.

    * **ad_ldap** -- attempts a real LDAP bind using ``ldap3``.
    * **adcs_file** / **adcs_remote** -- performs basic config validation only.
    """
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_access(instance.enclave_id, current_user, db)

    connector_type = (
        db.query(ConnectorType)
        .filter(ConnectorType.id == instance.connector_type_id)
        .first()
    )
    type_code = connector_type.code if connector_type else ""

    if type_code == "ad_ldap":
        return _test_ldap(instance.config)
    elif type_code in ("adcs_file", "adcs_remote"):
        return _test_adcs(instance.config, type_code)
    else:
        return {"status": "error", "message": f"Unknown connector type: {type_code}"}


def _test_ldap(config: dict) -> dict:
    """Attempt an LDAP bind with the configuration provided."""
    server_url = config.get("server", "")
    bind_dn = config.get("bind_dn", "")
    bind_password = config.get("bind_password", "")

    if not server_url:
        return {"status": "error", "message": "Missing 'server' in connector config"}

    try:
        import ldap3

        server = ldap3.Server(server_url, get_info=ldap3.NONE, connect_timeout=10)
        conn = ldap3.Connection(
            server,
            user=bind_dn,
            password=bind_password,
            auto_bind=False,
            raise_exceptions=True,
            receive_timeout=10,
        )
        conn.bind()
        conn.unbind()
        return {"status": "ok", "message": "LDAP bind successful"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _test_adcs(config: dict, type_code: str) -> dict:
    """Basic validation for ADCS connector configuration."""
    if type_code == "adcs_file":
        if not config.get("file_path") and not config.get("watch_directory"):
            return {
                "status": "error",
                "message": "Config must specify 'file_path' or 'watch_directory'",
            }
    elif type_code == "adcs_remote":
        if not config.get("ca_host"):
            return {
                "status": "error",
                "message": "Config must specify 'ca_host' for remote ADCS",
            }

    return {"status": "ok", "message": "Configuration valid"}


@router.post("/{connector_id}/run", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def run_connector(
    connector_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Job:
    """Trigger a manual run for a connector instance.

    Creates a ``Job`` record with ``status=pending`` and
    ``triggered_by=manual``.  The actual execution is handled asynchronously
    by the worker service.
    """
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_role(instance.enclave_id, current_user, db, "operator", "admin")

    job = Job(
        connector_instance_id=instance.id,
        status="pending",
        triggered_by="manual",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/{connector_id}/jobs", response_model=list[JobOut])
def list_connector_jobs(
    connector_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Job]:
    """List jobs for a specific connector instance (checks enclave access)."""
    instance = db.query(ConnectorInstance).filter(ConnectorInstance.id == connector_id).first()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector instance not found",
        )

    require_enclave_access(instance.enclave_id, current_user, db)

    return (
        db.query(Job)
        .filter(Job.connector_instance_id == connector_id)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
