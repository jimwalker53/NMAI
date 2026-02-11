"""NMIA sample data seed CLI.

Interactive utility to create clearly tagged SAMPLE data for demos/testing.
Safe to run multiple times (idempotent).
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from nmia.auth.models import User
from nmia.core.db import SessionLocal
from nmia.core.models import ConnectorInstance, ConnectorType, Enclave, Finding, Identity, Job

SAMPLE_TAG = "SAMPLE"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ask_yes_no(prompt: str, default: str = "y") -> bool:
    choice = input(f"{prompt} [{default}]: ").strip().lower() or default
    return choice in {"y", "yes"}


def _get_or_create_lab_enclave(db) -> tuple[Enclave, bool]:
    enclave_name = f"{SAMPLE_TAG} Lab Enclave"
    enclave = db.query(Enclave).filter(Enclave.name == enclave_name).first()
    if enclave is not None:
        return enclave, False

    enclave = Enclave(
        name=enclave_name,
        description=f"{SAMPLE_TAG} enclave for demonstration and testing fake data.",
    )
    db.add(enclave)
    db.flush()
    return enclave, True


def _ensure_connector_type(db, code: str, name: str, description: str) -> ConnectorType:
    connector_type = db.query(ConnectorType).filter(ConnectorType.code == code).first()
    if connector_type is not None:
        return connector_type

    connector_type = ConnectorType(code=code, name=name, description=description)
    db.add(connector_type)
    db.flush()
    return connector_type


def _ensure_sample_connector(db, enclave_id, connector_code: str, connector_name: str, config: dict[str, Any]) -> ConnectorInstance:
    connector = (
        db.query(ConnectorInstance)
        .join(ConnectorType, ConnectorType.id == ConnectorInstance.connector_type_id)
        .filter(
            ConnectorInstance.enclave_id == enclave_id,
            ConnectorInstance.name == connector_name,
            ConnectorType.code == connector_code,
        )
        .first()
    )
    if connector is not None:
        return connector

    connector_type = _ensure_connector_type(
        db,
        code=connector_code,
        name=f"{SAMPLE_TAG} {connector_code}",
        description=f"{SAMPLE_TAG} connector type used by seed data.",
    )
    connector = ConnectorInstance(
        connector_type_id=connector_type.id,
        enclave_id=enclave_id,
        name=connector_name,
        config=config,
        is_enabled=True,
        last_run_at=_utcnow() - timedelta(minutes=5),
    )
    db.add(connector)
    db.flush()
    return connector


def _ensure_sample_job(db, connector: ConnectorInstance) -> Job:
    job = (
        db.query(Job)
        .filter(
            Job.connector_instance_id == connector.id,
            Job.status == "completed",
            Job.triggered_by == "manual",
            Job.error_message == f"{SAMPLE_TAG} seed job",
        )
        .first()
    )
    if job is not None:
        return job

    now = _utcnow()
    job = Job(
        connector_instance_id=connector.id,
        status="completed",
        started_at=now - timedelta(minutes=2),
        finished_at=now - timedelta(minutes=1),
        records_found=0,
        records_ingested=0,
        triggered_by="manual",
        error_message=f"{SAMPLE_TAG} seed job",
    )
    db.add(job)
    db.flush()
    return job


def _create_sample_identity_and_finding(
    db,
    *,
    enclave_id,
    connector: ConnectorInstance,
    job: Job,
    source_type: str,
    identity_type: str,
    display_name: str,
    fingerprint: str,
    owner: str | None,
    linked_system: str | None,
    risk_score: float,
    normalized_data: dict[str, Any],
) -> bool:
    existing_identity = (
        db.query(Identity)
        .filter(
            Identity.enclave_id == enclave_id,
            Identity.fingerprint == fingerprint,
        )
        .first()
    )
    if existing_identity is not None:
        return False

    existing_finding = (
        db.query(Finding)
        .filter(
            Finding.enclave_id == enclave_id,
            Finding.fingerprint == fingerprint,
            Finding.source_type == source_type,
        )
        .first()
    )
    if existing_finding is None:
        finding = Finding(
            job_id=job.id,
            connector_instance_id=connector.id,
            enclave_id=enclave_id,
            source_type=source_type,
            raw_data={
                "sample": True,
                "sample_tag": SAMPLE_TAG,
                "display_name": display_name,
                "fingerprint": fingerprint,
            },
            fingerprint=fingerprint,
        )
        db.add(finding)
        db.flush()
        finding_ids = [str(finding.id)]
    else:
        finding_ids = [str(existing_finding.id)]

    now = _utcnow()
    identity = Identity(
        enclave_id=enclave_id,
        identity_type=identity_type,
        display_name=display_name,
        fingerprint=fingerprint,
        normalized_data={
            "sample": True,
            "sample_tag": SAMPLE_TAG,
            **normalized_data,
        },
        owner=owner,
        linked_system=linked_system,
        risk_score=risk_score,
        first_seen=now - timedelta(days=30),
        last_seen=now,
        finding_ids=finding_ids,
    )
    db.add(identity)
    db.flush()
    return True


def main() -> None:
    print("\nNMIA SAMPLE seed\n")

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            print("ERROR: No users found. Run bootstrap first: python -m nmia.bootstrap")
            sys.exit(1)

        create_lab_enclave = _ask_yes_no("Create SAMPLE lab enclave?", default="y")
        create_sample_systems_owners = _ask_yes_no("Create SAMPLE systems/owners?", default="y")
        create_sample_identities = _ask_yes_no(
            "Create SAMPLE identities/findings (svc_acct + cert fake data)?",
            default="y",
        )

        enclave = db.query(Enclave).filter(Enclave.name == f"{SAMPLE_TAG} Lab Enclave").first()
        if create_lab_enclave or enclave is None:
            enclave, created = _get_or_create_lab_enclave(db)
            if created:
                print(f"+ Created enclave: {enclave.name}")
            else:
                print(f"- Reusing enclave: {enclave.name}")

        if enclave is None:
            print("ERROR: No enclave available. Create SAMPLE lab enclave first.")
            sys.exit(1)

        owners = {
            "platform": f"sample.platform.owner@nmia.local" if create_sample_systems_owners else None,
            "security": f"sample.security.owner@nmia.local" if create_sample_systems_owners else None,
        }
        systems = {
            "jenkins": f"sample-jenkins.nmia.local" if create_sample_systems_owners else None,
            "vault": f"sample-vault.nmia.local" if create_sample_systems_owners else None,
        }

        if create_sample_systems_owners:
            print("+ Prepared SAMPLE owners/systems metadata")
        else:
            print("- Skipping SAMPLE owners/systems metadata")

        created_items = 0
        if create_sample_identities:
            svc_connector = _ensure_sample_connector(
                db,
                enclave_id=enclave.id,
                connector_code="ad_ldap",
                connector_name=f"[{SAMPLE_TAG}] AD LDAP",
                config={"sample": True, "sample_tag": SAMPLE_TAG, "host": "sample-dc.nmia.local"},
            )
            cert_connector = _ensure_sample_connector(
                db,
                enclave_id=enclave.id,
                connector_code="adcs_file",
                connector_name=f"[{SAMPLE_TAG}] ADCS File",
                config={"sample": True, "sample_tag": SAMPLE_TAG, "path": "sample-adcs-export.json"},
            )
            svc_job = _ensure_sample_job(db, svc_connector)
            cert_job = _ensure_sample_job(db, cert_connector)

            sample_svc_accounts = [
                {
                    "display_name": f"[{SAMPLE_TAG}] svc-ci-runner",
                    "fingerprint": "sample:svc_acct:ci-runner",
                    "owner": owners["platform"],
                    "linked_system": systems["jenkins"],
                    "risk_score": 42.0,
                },
                {
                    "display_name": f"[{SAMPLE_TAG}] svc-vault-auth",
                    "fingerprint": "sample:svc_acct:vault-auth",
                    "owner": owners["security"],
                    "linked_system": systems["vault"],
                    "risk_score": 71.0,
                },
            ]

            sample_certs = [
                {
                    "display_name": f"[{SAMPLE_TAG}] cert-ci-runner",
                    "fingerprint": "sample:cert:ci-runner",
                    "owner": owners["platform"],
                    "linked_system": systems["jenkins"],
                    "risk_score": 64.0,
                    "status": "expiring_soon",
                },
                {
                    "display_name": f"[{SAMPLE_TAG}] cert-vault",
                    "fingerprint": "sample:cert:vault",
                    "owner": owners["security"],
                    "linked_system": systems["vault"],
                    "risk_score": 23.0,
                    "status": "valid",
                },
            ]

            for item in sample_svc_accounts:
                created = _create_sample_identity_and_finding(
                    db,
                    enclave_id=enclave.id,
                    connector=svc_connector,
                    job=svc_job,
                    source_type="ad_svc_acct",
                    identity_type="svc_acct",
                    display_name=item["display_name"],
                    fingerprint=item["fingerprint"],
                    owner=item["owner"],
                    linked_system=item["linked_system"],
                    risk_score=item["risk_score"],
                    normalized_data={
                        "kind": "svc_acct",
                        "description": f"{SAMPLE_TAG} fake service account",
                    },
                )
                created_items += int(created)

            for item in sample_certs:
                created = _create_sample_identity_and_finding(
                    db,
                    enclave_id=enclave.id,
                    connector=cert_connector,
                    job=cert_job,
                    source_type="adcs_cert",
                    identity_type="cert",
                    display_name=item["display_name"],
                    fingerprint=item["fingerprint"],
                    owner=item["owner"],
                    linked_system=item["linked_system"],
                    risk_score=item["risk_score"],
                    normalized_data={
                        "kind": "cert",
                        "status": item["status"],
                        "description": f"{SAMPLE_TAG} fake certificate identity",
                    },
                )
                created_items += int(created)

            print(f"+ SAMPLE identities created: {created_items}")
            if created_items == 0:
                print("- Existing SAMPLE identities/findings detected; nothing new created.")
        else:
            print("- Skipping SAMPLE identities/findings")

        db.commit()
        print("\nSeed complete. You can now open the UI and inspect SAMPLE data.\n")

    except KeyboardInterrupt:
        print("\nSeed cancelled.")
        db.rollback()
        sys.exit(1)
    except SystemExit:
        db.rollback()
        raise
    except Exception as exc:
        print(f"\nERROR: {exc}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
