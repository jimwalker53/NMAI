"""Tests for ingestion endpoints, idempotency, normalization, and risk scoring."""

from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from nmia.core.models import (
    ConnectorInstance,
    Enclave,
    Finding,
    Identity,
    Job,
)
from nmia.auth.models import UserRoleEnclave
from nmia.ingestion.normalize import normalize_findings
from nmia.ingestion.risk import score_risks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connector_and_job(
    db_session: Session,
    seed_data: dict,
    enclave=None,
) -> tuple[ConnectorInstance, Job]:
    """Create a ConnectorInstance + Job in the given (or default) enclave
    and return both.
    """
    enc = enclave or seed_data["enclave"]
    ct = seed_data["connector_types"]["adcs_file"]
    admin = seed_data["admin_user"]

    connector = ConnectorInstance(
        connector_type_id=ct.id,
        enclave_id=enc.id,
        name="test-adcs-connector",
        config={},
        created_by=admin.id,
    )
    db_session.add(connector)
    db_session.flush()

    job = Job(
        connector_instance_id=connector.id,
        status="running",
        triggered_by="manual",
    )
    db_session.add(job)
    db_session.flush()

    return connector, job


SAMPLE_RECORDS = [
    {
        "serial_number": "ABC123",
        "common_name": "test.example.com",
        "issuer_dn": "CN=TestCA",
        "not_before": "2024-01-01",
        "not_after": "2024-12-31",
        "template_name": "WebServer",
        "thumbprint": "aabbccdd",
    },
    {
        "serial_number": "DEF456",
        "common_name": "api.example.com",
        "issuer_dn": "CN=TestCA",
        "not_before": "2024-01-01",
        "not_after": "2025-06-30",
        "template_name": "WebServer",
        "thumbprint": "eeff0011",
    },
]

SAMPLE_CSV = (
    "serial_number,common_name,issuer_dn,not_before,not_after,template_name,thumbprint\n"
    "ABC123,test.example.com,CN=TestCA,2024-01-01,2024-12-31,WebServer,aabbccdd\n"
    "DEF456,api.example.com,CN=TestCA,2024-01-01,2025-06-30,WebServer,eeff0011\n"
)


# ---------------------------------------------------------------------------
# JSON ingestion
# ---------------------------------------------------------------------------

class TestADCSIngestJSON:
    """POST /api/v1/ingest/adcs/{connector_id} with JSON payload."""

    def test_adcs_ingest_json(
        self, client, db_session, seed_data, admin_token
    ):
        """Ingest JSON cert records and verify the ingested count."""
        connector, job = _make_connector_and_job(db_session, seed_data)

        resp = client.post(
            f"/api/v1/ingest/adcs/{connector.id}?job_id={job.id}",
            json={
                "connector_instance_id": str(connector.id),
                "records": SAMPLE_RECORDS,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 2
        assert body["duplicates"] == 0

        # Verify Findings were actually created
        findings = (
            db_session.query(Finding)
            .filter(Finding.connector_instance_id == connector.id)
            .all()
        )
        assert len(findings) == 2

    def test_adcs_ingest_idempotent(
        self, client, db_session, seed_data, admin_token
    ):
        """Ingesting the same records twice should report duplicates on the
        second call without creating new findings.
        """
        connector, job = _make_connector_and_job(db_session, seed_data)

        payload = {
            "connector_instance_id": str(connector.id),
            "records": SAMPLE_RECORDS,
        }
        url = f"/api/v1/ingest/adcs/{connector.id}?job_id={job.id}"
        headers = {"Authorization": f"Bearer {admin_token}"}

        # First ingest
        resp1 = client.post(url, json=payload, headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["ingested"] == 2

        # Second ingest -- same records
        resp2 = client.post(url, json=payload, headers=headers)
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["ingested"] == 0
        assert body2["duplicates"] == 2

        # Still only 2 findings in the DB
        count = (
            db_session.query(Finding)
            .filter(Finding.connector_instance_id == connector.id)
            .count()
        )
        assert count == 2


# ---------------------------------------------------------------------------
# CSV upload ingestion
# ---------------------------------------------------------------------------

class TestADCSIngestCSV:
    """POST /api/v1/ingest/adcs/{connector_id} with multipart CSV file."""

    def test_adcs_ingest_csv_upload(
        self, client, db_session, seed_data, admin_token
    ):
        """Upload a CSV file and verify ingested count."""
        connector, job = _make_connector_and_job(db_session, seed_data)

        csv_bytes = SAMPLE_CSV.encode("utf-8")
        resp = client.post(
            f"/api/v1/ingest/adcs/{connector.id}?job_id={job.id}",
            files={"file": ("certs.csv", io.BytesIO(csv_bytes), "text/csv")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ingested"] == 2
        assert body["duplicates"] == 0


# ---------------------------------------------------------------------------
# Finding fingerprint uniqueness
# ---------------------------------------------------------------------------

class TestFindingFingerprint:
    """Fingerprint-based de-duplication within and across enclaves."""

    def test_finding_fingerprint_uniqueness(
        self, client, db_session, seed_data, admin_token
    ):
        """The same fingerprint in the same enclave updates the existing
        Finding rather than creating a duplicate.
        """
        connector, job = _make_connector_and_job(db_session, seed_data)
        headers = {"Authorization": f"Bearer {admin_token}"}
        url = f"/api/v1/ingest/adcs/{connector.id}?job_id={job.id}"

        # Ingest first record
        resp1 = client.post(
            url,
            json={
                "connector_instance_id": str(connector.id),
                "records": [SAMPLE_RECORDS[0]],
            },
            headers=headers,
        )
        assert resp1.json()["ingested"] == 1

        # Ingest same record again -- should be a duplicate / update
        resp2 = client.post(
            url,
            json={
                "connector_instance_id": str(connector.id),
                "records": [SAMPLE_RECORDS[0]],
            },
            headers=headers,
        )
        assert resp2.json()["duplicates"] == 1
        assert resp2.json()["ingested"] == 0

        # Only one Finding row
        count = (
            db_session.query(Finding)
            .filter(Finding.enclave_id == seed_data["enclave"].id)
            .count()
        )
        assert count == 1

    def test_different_enclave_same_fingerprint(
        self, client, db_session, seed_data, admin_token
    ):
        """The same fingerprint in different enclaves creates separate
        Finding rows.
        """
        headers = {"Authorization": f"Bearer {admin_token}"}

        # First enclave
        connector1, job1 = _make_connector_and_job(db_session, seed_data)

        resp1 = client.post(
            f"/api/v1/ingest/adcs/{connector1.id}?job_id={job1.id}",
            json={
                "connector_instance_id": str(connector1.id),
                "records": [SAMPLE_RECORDS[0]],
            },
            headers=headers,
        )
        assert resp1.json()["ingested"] == 1

        # Second enclave
        enclave2 = Enclave(name="second-ingest-enclave", description="Second")
        db_session.add(enclave2)
        db_session.flush()

        connector2, job2 = _make_connector_and_job(
            db_session, seed_data, enclave=enclave2
        )

        resp2 = client.post(
            f"/api/v1/ingest/adcs/{connector2.id}?job_id={job2.id}",
            json={
                "connector_instance_id": str(connector2.id),
                "records": [SAMPLE_RECORDS[0]],
            },
            headers=headers,
        )
        assert resp2.json()["ingested"] == 1

        # Two distinct Finding rows
        total = db_session.query(Finding).count()
        assert total == 2


# ---------------------------------------------------------------------------
# Normalization pipeline
# ---------------------------------------------------------------------------

class TestNormalization:
    """normalize_findings and run_normalization_pipeline."""

    def _ingest_records(self, client, db_session, seed_data, admin_token):
        """Helper: ingest SAMPLE_RECORDS and return the connector/job."""
        connector, job = _make_connector_and_job(db_session, seed_data)
        client.post(
            f"/api/v1/ingest/adcs/{connector.id}?job_id={job.id}",
            json={
                "connector_instance_id": str(connector.id),
                "records": SAMPLE_RECORDS,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        return connector, job

    def test_normalization_creates_identities(
        self, client, db_session, seed_data, admin_token
    ):
        """After ingestion, normalize_findings should create Identity records."""
        self._ingest_records(client, db_session, seed_data, admin_token)
        enclave = seed_data["enclave"]

        count = normalize_findings(db_session, enclave_id=enclave.id)
        db_session.flush()

        # We ingested 2 records with different serial numbers -> 2 identities
        assert count == 2

        identities = (
            db_session.query(Identity)
            .filter(Identity.enclave_id == enclave.id)
            .all()
        )
        assert len(identities) == 2

    def test_normalization_idempotent(
        self, client, db_session, seed_data, admin_token
    ):
        """Running normalization twice should not create duplicate
        identities.
        """
        self._ingest_records(client, db_session, seed_data, admin_token)
        enclave = seed_data["enclave"]

        count1 = normalize_findings(db_session, enclave_id=enclave.id)
        db_session.flush()
        assert count1 == 2

        count2 = normalize_findings(db_session, enclave_id=enclave.id)
        db_session.flush()
        assert count2 == 0  # already processed

        identities = (
            db_session.query(Identity)
            .filter(Identity.enclave_id == enclave.id)
            .all()
        )
        assert len(identities) == 2


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

class TestRiskScoring:
    """score_risks service function."""

    def _create_cert_identity(
        self,
        db_session: Session,
        enclave,
        *,
        not_after: str,
        owner: str | None = None,
        fingerprint: str | None = None,
    ) -> Identity:
        """Create a cert Identity with the given not_after date."""
        now = datetime.now(timezone.utc)
        fp = fingerprint or f"CN=TestCA|{not_after}"
        identity = Identity(
            enclave_id=enclave.id,
            identity_type="cert",
            display_name=f"cert-{not_after}",
            fingerprint=fp,
            normalized_data={
                "issuer_dn": "CN=TestCA",
                "serial_number": not_after,
                "not_before": "2023-01-01",
                "not_after": not_after,
            },
            owner=owner,
            first_seen=now,
            last_seen=now,
            finding_ids=[],
            risk_score=0.0,
        )
        db_session.add(identity)
        db_session.flush()
        return identity

    def test_risk_scoring(self, db_session, seed_data):
        """An identity with an expired cert (and no owner, no linked_system)
        should have risk_score > 0.
        """
        enclave = seed_data["enclave"]
        # Expired cert: not_after in the past
        expired_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%d"
        )
        identity = self._create_cert_identity(
            db_session, enclave, not_after=expired_date, owner="someone"
        )

        scored = score_risks(db_session, enclave_id=enclave.id)
        db_session.flush()

        assert scored >= 1
        db_session.refresh(identity)
        # Expired cert (+40) + no linked_system (+15) = 55 at minimum
        assert identity.risk_score > 0

    def test_risk_scoring_no_owner(self, db_session, seed_data):
        """An identity without an owner should receive a higher risk score
        than one with an owner (all else being equal).
        """
        enclave = seed_data["enclave"]

        # Use a future date so cert-specific expiry penalty is zero
        future = (datetime.now(timezone.utc) + timedelta(days=365)).strftime(
            "%Y-%m-%d"
        )

        ident_with_owner = self._create_cert_identity(
            db_session,
            enclave,
            not_after=future,
            owner="team-alpha",
            fingerprint="fp-with-owner",
        )
        ident_no_owner = self._create_cert_identity(
            db_session,
            enclave,
            not_after=future,
            owner=None,
            fingerprint="fp-no-owner",
        )

        score_risks(db_session, enclave_id=enclave.id)
        db_session.flush()

        db_session.refresh(ident_with_owner)
        db_session.refresh(ident_no_owner)

        # The identity without an owner should have a *higher* score
        assert ident_no_owner.risk_score > ident_with_owner.risk_score
