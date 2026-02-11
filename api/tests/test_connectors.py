"""Tests for connector CRUD operations and test/run endpoints."""

from __future__ import annotations

from uuid import UUID

from nmia.core.models import ConnectorInstance, Job


# ---------------------------------------------------------------------------
# Connector CRUD
# ---------------------------------------------------------------------------

class TestConnectorCRUD:
    """Basic create / read / update / delete for connector instances."""

    def test_list_connector_types(self, client, seed_data, admin_token):
        """GET /api/v1/connectors/types returns seeded connector types."""
        resp = client.get(
            "/api/v1/connectors/types",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        codes = [ct["code"] for ct in resp.json()]
        assert "ad_ldap" in codes
        assert "adcs_file" in codes
        assert "adcs_remote" in codes

    def test_create_connector(self, client, seed_data, admin_token):
        """POST /api/v1/connectors/ creates a connector instance."""
        enclave = seed_data["enclave"]
        resp = client.post(
            "/api/v1/connectors/",
            json={
                "connector_type_code": "adcs_file",
                "enclave_id": str(enclave.id),
                "name": "test-adcs-connector",
                "config": {"file_path": "/data/certs.csv"},
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "test-adcs-connector"
        assert body["enclave_id"] == str(enclave.id)
        assert body["is_enabled"] is True

    def test_list_connectors(self, client, db_session, seed_data, admin_token):
        """GET /api/v1/connectors/ returns connectors in accessible enclaves."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="listed-connector",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.get(
            "/api/v1/connectors/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        names = [conn["name"] for conn in resp.json()]
        assert "listed-connector" in names

    def test_get_connector(self, client, db_session, seed_data, admin_token):
        """GET /api/v1/connectors/{id} returns the connector."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="get-me",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.get(
            f"/api/v1/connectors/{c.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "get-me"

    def test_update_connector(self, client, db_session, seed_data, admin_token):
        """PUT /api/v1/connectors/{id} updates the connector."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="before-update",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.put(
            f"/api/v1/connectors/{c.id}",
            json={"name": "after-update"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "after-update"

    def test_delete_connector(self, client, db_session, seed_data, admin_token):
        """DELETE /api/v1/connectors/{id} removes the connector (admin only)."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="delete-me",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.delete(
            f"/api/v1/connectors/{c.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

        # Verify it's gone
        gone = db_session.query(ConnectorInstance).filter(ConnectorInstance.id == c.id).first()
        assert gone is None


# ---------------------------------------------------------------------------
# Test / Run endpoints
# ---------------------------------------------------------------------------

class TestConnectorTestAndRun:
    """POST /api/v1/connectors/{id}/test and /run endpoints."""

    def test_test_adcs_connector(self, client, db_session, seed_data, admin_token):
        """POST /api/v1/connectors/{id}/test returns config validation result."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="test-me",
            config={"file_path": "/data/certs.csv"},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.post(
            f"/api/v1/connectors/{c.id}/test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"

    def test_run_connector(self, client, db_session, seed_data, admin_token):
        """POST /api/v1/connectors/{id}/run creates a pending Job."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="run-me",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.post(
            f"/api/v1/connectors/{c.id}/run",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "pending"
        assert body["triggered_by"] == "manual"
        assert body["connector_instance_id"] == str(c.id)

    def test_list_connector_jobs(self, client, db_session, seed_data, admin_token):
        """GET /api/v1/connectors/{id}/jobs returns jobs for the connector."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="jobs-connector",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        job = Job(
            connector_instance_id=c.id,
            status="completed",
            triggered_by="manual",
        )
        db_session.add(job)
        db_session.flush()

        resp = client.get(
            f"/api/v1/connectors/{c.id}/jobs",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        jobs = resp.json()
        assert len(jobs) >= 1
        assert jobs[0]["connector_instance_id"] == str(c.id)


# ---------------------------------------------------------------------------
# Permission checks
# ---------------------------------------------------------------------------

class TestConnectorPermissions:
    """Connector endpoints respect enclave-scoped RBAC."""

    def test_viewer_cannot_create_connector(self, client, seed_data, viewer_token):
        """Viewer is forbidden from creating connectors."""
        enclave = seed_data["enclave"]
        resp = client.post(
            "/api/v1/connectors/",
            json={
                "connector_type_code": "adcs_file",
                "enclave_id": str(enclave.id),
                "name": "viewer-connector",
                "config": {},
            },
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403

    def test_viewer_cannot_run_connector(self, client, db_session, seed_data, viewer_token):
        """Viewer is forbidden from running connectors."""
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin = seed_data["admin_user"]

        c = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="no-run-for-viewer",
            config={},
            created_by=admin.id,
        )
        db_session.add(c)
        db_session.flush()

        resp = client.post(
            f"/api/v1/connectors/{c.id}/run",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403
