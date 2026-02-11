"""
NMIA Seed CLI
=============
Creates sample / demo data for development and testing.
All data is clearly marked as fake.

Usage:
    python -m nmia.seed
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone

from nmia.core.db import SessionLocal
from nmia.core.models import (
    ConnectorInstance,
    ConnectorType,
    Enclave,
    Finding,
    Identity,
    Job,
)
from nmia.auth.models import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ask(prompt: str, default: str = "y") -> bool:
    """Ask a yes/no question."""
    choice = input(f"  {prompt} [{default}]: ").strip().lower() or default
    return choice in ("y", "yes")


def main() -> None:
    print()
    print("=" * 60)
    print("  NMIA -- Sample Data Seed")
    print("  All data created is clearly marked as SAMPLE/FAKE.")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # Guard: require bootstrap to have been run first
        # ------------------------------------------------------------------
        user_count = db.query(User).count()
        if user_count == 0:
            print("ERROR: No users found. Run bootstrap first:")
            print("  python -m nmia.bootstrap")
            sys.exit(1)

        lab_enclave = None
        ad_ldap_connector = None
        adcs_file_connector = None

        # ==================================================================
        # 1. Lab Enclave
        # ==================================================================
        if _ask("Create 'Lab' enclave?"):
            print()
            print("  [1] Creating 'Lab' enclave ...")
            existing = db.query(Enclave).filter(Enclave.name == "Lab").first()
            if existing is not None:
                lab_enclave = existing
                print("       - Lab enclave already exists, reusing it.")
            else:
                lab_enclave = Enclave(
                    name="Lab",
                    description="Sample lab environment for demo and testing. (SEED DATA)",
                )
                db.add(lab_enclave)
                db.flush()
                print("       + Lab enclave created.")
            print()
        else:
            # Try to find an existing Lab enclave for subsequent steps
            lab_enclave = db.query(Enclave).filter(Enclave.name == "Lab").first()
            if lab_enclave is None:
                # Fall back to Default enclave
                lab_enclave = db.query(Enclave).first()
            print()

        if lab_enclave is None:
            print("ERROR: No enclave available. Cannot seed data.")
            sys.exit(1)

        # ==================================================================
        # 2. Connector Instances
        # ==================================================================
        if _ask("Create sample connector instances?"):
            print()
            print("  [2] Creating sample connector instances ...")

            # AD LDAP connector
            ad_ldap_type = db.query(ConnectorType).filter(ConnectorType.code == "ad_ldap").first()
            if ad_ldap_type is None:
                print("       ! ConnectorType 'ad_ldap' not found. Run bootstrap first.")
            else:
                existing = (
                    db.query(ConnectorInstance)
                    .filter(
                        ConnectorInstance.name == "[SAMPLE] Lab AD LDAP",
                        ConnectorInstance.enclave_id == lab_enclave.id,
                    )
                    .first()
                )
                if existing is not None:
                    ad_ldap_connector = existing
                    print("       - [SAMPLE] Lab AD LDAP already exists, reusing.")
                else:
                    ad_ldap_connector = ConnectorInstance(
                        connector_type_id=ad_ldap_type.id,
                        enclave_id=lab_enclave.id,
                        name="[SAMPLE] Lab AD LDAP",
                        config={
                            "host": "dc01.lab.local",
                            "port": 636,
                            "use_ssl": True,
                            "bind_dn": "CN=svc-nmia,OU=Service Accounts,DC=lab,DC=local",
                            "search_base": "DC=lab,DC=local",
                            "search_filter": "(&(objectCategory=user)(servicePrincipalName=*))",
                        },
                        is_enabled=True,
                        last_run_at=_utcnow() - timedelta(hours=2),
                    )
                    db.add(ad_ldap_connector)
                    db.flush()
                    print("       + [SAMPLE] Lab AD LDAP connector created.")

            # ADCS File connector
            adcs_file_type = db.query(ConnectorType).filter(ConnectorType.code == "adcs_file").first()
            if adcs_file_type is None:
                print("       ! ConnectorType 'adcs_file' not found. Run bootstrap first.")
            else:
                existing = (
                    db.query(ConnectorInstance)
                    .filter(
                        ConnectorInstance.name == "[SAMPLE] Lab ADCS File Import",
                        ConnectorInstance.enclave_id == lab_enclave.id,
                    )
                    .first()
                )
                if existing is not None:
                    adcs_file_connector = existing
                    print("       - [SAMPLE] Lab ADCS File Import already exists, reusing.")
                else:
                    adcs_file_connector = ConnectorInstance(
                        connector_type_id=adcs_file_type.id,
                        enclave_id=lab_enclave.id,
                        name="[SAMPLE] Lab ADCS File Import",
                        config={
                            "file_path": "/data/imports/lab-certs-export.csv",
                            "file_format": "csv",
                            "ca_name": "Lab-Issuing-CA",
                        },
                        is_enabled=True,
                        last_run_at=_utcnow() - timedelta(hours=1),
                    )
                    db.add(adcs_file_connector)
                    db.flush()
                    print("       + [SAMPLE] Lab ADCS File Import connector created.")

            print()

        # ==================================================================
        # 3. Sample Jobs (one per connector)
        # ==================================================================
        ad_ldap_job = None
        adcs_file_job = None

        if ad_ldap_connector is not None or adcs_file_connector is not None:
            print("  [3] Creating sample completed job records ...")

            if ad_ldap_connector is not None:
                ad_ldap_job = Job(
                    connector_instance_id=ad_ldap_connector.id,
                    status="completed",
                    started_at=_utcnow() - timedelta(hours=2, minutes=5),
                    finished_at=_utcnow() - timedelta(hours=2),
                    records_found=3,
                    records_ingested=3,
                    triggered_by="manual",
                )
                db.add(ad_ldap_job)
                db.flush()
                print("       + Job for AD LDAP connector (completed, 3 records).")

            if adcs_file_connector is not None:
                adcs_file_job = Job(
                    connector_instance_id=adcs_file_connector.id,
                    status="completed",
                    started_at=_utcnow() - timedelta(hours=1, minutes=10),
                    finished_at=_utcnow() - timedelta(hours=1),
                    records_found=4,
                    records_ingested=4,
                    triggered_by="manual",
                )
                db.add(adcs_file_job)
                db.flush()
                print("       + Job for ADCS File connector (completed, 4 records).")

            print()

        # ==================================================================
        # 4. Sample Identities and Findings
        # ==================================================================
        if _ask("Create sample identities and findings?"):
            print()
            print("  [4] Creating sample identities and findings ...")
            now = _utcnow()

            # --------------------------------------------------------------
            # 4a. AD Service Accounts (3 accounts)
            # --------------------------------------------------------------
            svc_accounts = [
                {
                    "display_name": "svc-jenkins",
                    "fingerprint": "ad:svc-jenkins@lab.local",
                    "owner": "platform-team@lab.local",
                    "linked_system": "jenkins-ci.lab.local",
                    "risk_score": 62.0,
                    "normalized_data": {
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1601",
                        "sAMAccountName": "svc-jenkins",
                        "distinguishedName": "CN=svc-jenkins,OU=Service Accounts,DC=lab,DC=local",
                        "userPrincipalName": "svc-jenkins@lab.local",
                        "servicePrincipalName": [
                            "HTTP/jenkins-ci.lab.local",
                            "HTTP/jenkins-ci",
                        ],
                        "whenCreated": "2023-06-15T08:30:00Z",
                        "lastLogonTimestamp": (now - timedelta(days=1)).isoformat(),
                        "passwordLastSet": (now - timedelta(days=180)).isoformat(),
                        "userAccountControl": 66048,
                        "memberOf": [
                            "CN=CI-Admins,OU=Groups,DC=lab,DC=local",
                            "CN=Deploy-Users,OU=Groups,DC=lab,DC=local",
                        ],
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1601",
                        "sAMAccountName": "svc-jenkins",
                        "distinguishedName": "CN=svc-jenkins,OU=Service Accounts,DC=lab,DC=local",
                        "servicePrincipalName": ["HTTP/jenkins-ci.lab.local", "HTTP/jenkins-ci"],
                    },
                },
                {
                    "display_name": "svc-vault-auth",
                    "fingerprint": "ad:svc-vault-auth@lab.local",
                    "owner": "security-team@lab.local",
                    "linked_system": "vault.lab.local",
                    "risk_score": 85.0,
                    "normalized_data": {
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1602",
                        "sAMAccountName": "svc-vault-auth",
                        "distinguishedName": "CN=svc-vault-auth,OU=Service Accounts,DC=lab,DC=local",
                        "userPrincipalName": "svc-vault-auth@lab.local",
                        "servicePrincipalName": [
                            "HTTP/vault.lab.local",
                        ],
                        "whenCreated": "2023-01-20T14:00:00Z",
                        "lastLogonTimestamp": (now - timedelta(hours=6)).isoformat(),
                        "passwordLastSet": (now - timedelta(days=400)).isoformat(),
                        "userAccountControl": 66048,
                        "memberOf": [
                            "CN=Vault-Admins,OU=Groups,DC=lab,DC=local",
                            "CN=Secret-Readers,OU=Groups,DC=lab,DC=local",
                            "CN=Domain Admins,OU=Groups,DC=lab,DC=local",
                        ],
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1602",
                        "sAMAccountName": "svc-vault-auth",
                        "distinguishedName": "CN=svc-vault-auth,OU=Service Accounts,DC=lab,DC=local",
                        "servicePrincipalName": ["HTTP/vault.lab.local"],
                    },
                },
                {
                    "display_name": "svc-terraform",
                    "fingerprint": "ad:svc-terraform@lab.local",
                    "owner": None,
                    "linked_system": "terraform-runner.lab.local",
                    "risk_score": 48.0,
                    "normalized_data": {
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1603",
                        "sAMAccountName": "svc-terraform",
                        "distinguishedName": "CN=svc-terraform,OU=Service Accounts,DC=lab,DC=local",
                        "userPrincipalName": "svc-terraform@lab.local",
                        "servicePrincipalName": [],
                        "whenCreated": "2024-03-10T09:15:00Z",
                        "lastLogonTimestamp": (now - timedelta(days=30)).isoformat(),
                        "passwordLastSet": (now - timedelta(days=60)).isoformat(),
                        "userAccountControl": 66048,
                        "memberOf": [
                            "CN=Infra-Deploy,OU=Groups,DC=lab,DC=local",
                        ],
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1603",
                        "sAMAccountName": "svc-terraform",
                        "distinguishedName": "CN=svc-terraform,OU=Service Accounts,DC=lab,DC=local",
                        "servicePrincipalName": [],
                    },
                },
            ]

            for acct in svc_accounts:
                # Check for duplicate identity
                existing_identity = (
                    db.query(Identity)
                    .filter(
                        Identity.fingerprint == acct["fingerprint"],
                        Identity.enclave_id == lab_enclave.id,
                    )
                    .first()
                )
                if existing_identity is not None:
                    print(f"       - {acct['display_name']} identity already exists, skipping.")
                    continue

                # Create finding
                finding_id = uuid.uuid4()
                if ad_ldap_job is not None and ad_ldap_connector is not None:
                    finding = Finding(
                        id=finding_id,
                        job_id=ad_ldap_job.id,
                        connector_instance_id=ad_ldap_connector.id,
                        enclave_id=lab_enclave.id,
                        source_type="ad_svc_acct",
                        raw_data=acct["raw_data"],
                        fingerprint=acct["fingerprint"],
                    )
                    db.add(finding)
                    db.flush()

                # Create identity
                identity = Identity(
                    enclave_id=lab_enclave.id,
                    identity_type="svc_acct",
                    display_name=acct["display_name"],
                    fingerprint=acct["fingerprint"],
                    normalized_data=acct["normalized_data"],
                    owner=acct["owner"],
                    linked_system=acct["linked_system"],
                    risk_score=acct["risk_score"],
                    first_seen=now - timedelta(days=90),
                    last_seen=now,
                    finding_ids=[str(finding_id)] if ad_ldap_job is not None else [],
                )
                db.add(identity)
                db.flush()
                owner_info = f", owner={acct['owner']}" if acct["owner"] else ", ORPHANED (no owner)"
                print(f"       + {acct['display_name']} (svc_acct, risk={acct['risk_score']}{owner_info})")

            # --------------------------------------------------------------
            # 4b. ADCS Certificates (4 certificates)
            # --------------------------------------------------------------
            certificates = [
                {
                    "display_name": "jenkins-ci.lab.local",
                    "fingerprint": "cert:sha256:a1b2c3d4e5f6:jenkins-ci.lab.local",
                    "owner": "platform-team@lab.local",
                    "linked_system": "jenkins-ci.lab.local",
                    "risk_score": 78.0,
                    "normalized_data": {
                        "subject_dn": "CN=jenkins-ci.lab.local,OU=Servers,O=Lab Corp",
                        "issuer_dn": "CN=Lab-Issuing-CA,DC=lab,DC=local",
                        "serial_number": "4A:00:00:00:1F:3C:8B:22:DD:01",
                        "not_before": (now - timedelta(days=350)).isoformat(),
                        "not_after": (now + timedelta(days=15)).isoformat(),
                        "subject_alternative_names": [
                            "DNS:jenkins-ci.lab.local",
                            "DNS:jenkins.lab.local",
                            "IP:10.10.1.50",
                        ],
                        "key_usage": ["Digital Signature", "Key Encipherment"],
                        "extended_key_usage": ["Server Authentication", "Client Authentication"],
                        "key_algorithm": "RSA",
                        "key_size": 2048,
                        "signature_algorithm": "sha256WithRSAEncryption",
                        "thumbprint_sha256": "a1b2c3d4e5f60718293a4b5c6d7e8f901234567890abcdef1234567890abcdef",
                        "template_name": "WebServer",
                        "status": "expiring_soon",
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "serial_number": "4A:00:00:00:1F:3C:8B:22:DD:01",
                        "subject": "CN=jenkins-ci.lab.local,OU=Servers,O=Lab Corp",
                        "template": "WebServer",
                    },
                },
                {
                    "display_name": "vault.lab.local",
                    "fingerprint": "cert:sha256:b2c3d4e5f6a7:vault.lab.local",
                    "owner": "security-team@lab.local",
                    "linked_system": "vault.lab.local",
                    "risk_score": 25.0,
                    "normalized_data": {
                        "subject_dn": "CN=vault.lab.local,OU=Servers,O=Lab Corp",
                        "issuer_dn": "CN=Lab-Issuing-CA,DC=lab,DC=local",
                        "serial_number": "4A:00:00:00:20:5D:9C:33:EE:02",
                        "not_before": (now - timedelta(days=30)).isoformat(),
                        "not_after": (now + timedelta(days=335)).isoformat(),
                        "subject_alternative_names": [
                            "DNS:vault.lab.local",
                            "DNS:vault-ha.lab.local",
                            "IP:10.10.1.60",
                            "IP:10.10.1.61",
                        ],
                        "key_usage": ["Digital Signature", "Key Encipherment"],
                        "extended_key_usage": ["Server Authentication"],
                        "key_algorithm": "ECDSA",
                        "key_size": 384,
                        "signature_algorithm": "sha384WithECDSA",
                        "thumbprint_sha256": "b2c3d4e5f6a70829314a5b6c7d8e9f012345678901bcdef2345678901bcdef01",
                        "template_name": "WebServer-ECC",
                        "status": "valid",
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "serial_number": "4A:00:00:00:20:5D:9C:33:EE:02",
                        "subject": "CN=vault.lab.local,OU=Servers,O=Lab Corp",
                        "template": "WebServer-ECC",
                    },
                },
                {
                    "display_name": "expired-api.lab.local",
                    "fingerprint": "cert:sha256:c3d4e5f6a7b8:expired-api.lab.local",
                    "owner": None,
                    "linked_system": None,
                    "risk_score": 95.0,
                    "normalized_data": {
                        "subject_dn": "CN=expired-api.lab.local,OU=Servers,O=Lab Corp",
                        "issuer_dn": "CN=Lab-Issuing-CA,DC=lab,DC=local",
                        "serial_number": "4A:00:00:00:18:2A:7A:11:CC:03",
                        "not_before": (now - timedelta(days=400)).isoformat(),
                        "not_after": (now - timedelta(days=35)).isoformat(),
                        "subject_alternative_names": [
                            "DNS:expired-api.lab.local",
                        ],
                        "key_usage": ["Digital Signature", "Key Encipherment"],
                        "extended_key_usage": ["Server Authentication", "Client Authentication"],
                        "key_algorithm": "RSA",
                        "key_size": 2048,
                        "signature_algorithm": "sha256WithRSAEncryption",
                        "thumbprint_sha256": "c3d4e5f6a7b80930425a6b7c8d9e0f123456789012cdef3456789012cdef0123",
                        "template_name": "WebServer",
                        "status": "expired",
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "serial_number": "4A:00:00:00:18:2A:7A:11:CC:03",
                        "subject": "CN=expired-api.lab.local,OU=Servers,O=Lab Corp",
                        "template": "WebServer",
                    },
                },
                {
                    "display_name": "terraform.lab.local",
                    "fingerprint": "cert:sha256:d4e5f6a7b8c9:terraform.lab.local",
                    "owner": None,
                    "linked_system": "terraform-runner.lab.local",
                    "risk_score": 40.0,
                    "normalized_data": {
                        "subject_dn": "CN=terraform.lab.local,OU=Automation,O=Lab Corp",
                        "issuer_dn": "CN=Lab-Issuing-CA,DC=lab,DC=local",
                        "serial_number": "4A:00:00:00:21:6E:AD:44:FF:04",
                        "not_before": (now - timedelta(days=10)).isoformat(),
                        "not_after": (now + timedelta(days=170)).isoformat(),
                        "subject_alternative_names": [
                            "DNS:terraform.lab.local",
                            "DNS:tf-runner.lab.local",
                            "IP:10.10.2.20",
                        ],
                        "key_usage": ["Digital Signature"],
                        "extended_key_usage": ["Client Authentication"],
                        "key_algorithm": "RSA",
                        "key_size": 4096,
                        "signature_algorithm": "sha256WithRSAEncryption",
                        "thumbprint_sha256": "d4e5f6a7b8c90a41536b7c8d9e0f1234567890123def456789a123def45678901",
                        "template_name": "ClientAuth",
                        "status": "valid",
                    },
                    "raw_data": {
                        "source": "SAMPLE_DATA",
                        "serial_number": "4A:00:00:00:21:6E:AD:44:FF:04",
                        "subject": "CN=terraform.lab.local,OU=Automation,O=Lab Corp",
                        "template": "ClientAuth",
                    },
                },
            ]

            for cert in certificates:
                # Check for duplicate identity
                existing_identity = (
                    db.query(Identity)
                    .filter(
                        Identity.fingerprint == cert["fingerprint"],
                        Identity.enclave_id == lab_enclave.id,
                    )
                    .first()
                )
                if existing_identity is not None:
                    print(f"       - {cert['display_name']} identity already exists, skipping.")
                    continue

                # Create finding
                finding_id = uuid.uuid4()
                if adcs_file_job is not None and adcs_file_connector is not None:
                    finding = Finding(
                        id=finding_id,
                        job_id=adcs_file_job.id,
                        connector_instance_id=adcs_file_connector.id,
                        enclave_id=lab_enclave.id,
                        source_type="adcs_cert",
                        raw_data=cert["raw_data"],
                        fingerprint=cert["fingerprint"],
                    )
                    db.add(finding)
                    db.flush()

                # Build status label for output
                status = cert["normalized_data"].get("status", "unknown")
                owner_info = f", owner={cert['owner']}" if cert["owner"] else ", ORPHANED (no owner)"
                linked_info = f", system={cert['linked_system']}" if cert["linked_system"] else ", no linked system"

                identity = Identity(
                    enclave_id=lab_enclave.id,
                    identity_type="cert",
                    display_name=cert["display_name"],
                    fingerprint=cert["fingerprint"],
                    normalized_data=cert["normalized_data"],
                    owner=cert["owner"],
                    linked_system=cert["linked_system"],
                    risk_score=cert["risk_score"],
                    first_seen=now - timedelta(days=45),
                    last_seen=now,
                    finding_ids=[str(finding_id)] if adcs_file_job is not None else [],
                )
                db.add(identity)
                db.flush()
                print(f"       + {cert['display_name']} (cert, {status}, risk={cert['risk_score']}{owner_info}{linked_info})")

            print()

        # ==================================================================
        # Commit
        # ==================================================================
        db.commit()

        print("=" * 60)
        print("  Seed complete! Sample data has been created.")
        print("  Login to the UI to explore.")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n\nSeed cancelled.")
        db.rollback()
        sys.exit(1)
    except SystemExit:
        db.rollback()
        raise
    except Exception as e:
        print(f"\nERROR: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
