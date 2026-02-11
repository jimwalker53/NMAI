"""Tests for role-based access control and enclave scoping."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from nmia.core.models import (
    ConnectorInstance,
    Enclave,
    Identity,
)
from nmia.auth.models import UserRoleEnclave


# ---------------------------------------------------------------------------
# Enclave creation permissions
# ---------------------------------------------------------------------------

class TestEnclaveCreation:
    """POST /api/v1/enclaves -- admin-only."""

    def test_admin_can_create_enclave(self, client, seed_data, admin_token):
        """Admin can create a new enclave."""
        resp = client.post(
            "/api/v1/enclaves/",
            json={"name": "new-enclave", "description": "Created by admin"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "new-enclave"

    def test_operator_cannot_create_enclave(self, client, seed_data, operator_token):
        """Operator is forbidden from creating enclaves."""
        resp = client.post(
            "/api/v1/enclaves/",
            json={"name": "op-enclave"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 403

    def test_viewer_cannot_create_enclave(self, client, seed_data, viewer_token):
        """Viewer is forbidden from creating enclaves."""
        resp = client.post(
            "/api/v1/enclaves/",
            json={"name": "viewer-enclave"},
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# User creation permissions
# ---------------------------------------------------------------------------

class TestUserCreation:
    """POST /api/v1/users -- admin-only."""

    def test_admin_can_create_user(self, client, seed_data, admin_token):
        """Admin can create a new user."""
        resp = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "password": "newpass123",
                "email": "new@test.local",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser"

    def test_operator_cannot_create_user(self, client, seed_data, operator_token):
        """Operator is forbidden from creating users."""
        resp = client.post(
            "/api/v1/users/",
            json={"username": "opuser", "password": "p"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Enclave visibility
# ---------------------------------------------------------------------------

class TestEnclaveVisibility:
    """GET /api/v1/enclaves -- enclave scoping."""

    def test_admin_sees_all_enclaves(self, client, db_session, seed_data, admin_token):
        """Admin can see every enclave, including ones they have no direct
        role assignment in.
        """
        # Create a second enclave the admin has no explicit assignment in.
        # Admins still see it because get_user_enclaves returns all for admins.
        second = Enclave(name="second-enclave", description="Another enclave")
        db_session.add(second)
        db_session.flush()

        resp = client.get(
            "/api/v1/enclaves/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "test-enclave" in names
        assert "second-enclave" in names

    def test_user_sees_only_assigned_enclaves(
        self, client, db_session, seed_data, operator_token
    ):
        """Operator should only see enclaves they are assigned to.

        Create a second enclave without assigning operator to it; the
        operator should only see ``test-enclave``.
        """
        second = Enclave(name="hidden-enclave", description="Not for operator")
        db_session.add(second)
        db_session.flush()

        resp = client.get(
            "/api/v1/enclaves/",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        names = [e["name"] for e in resp.json()]
        assert "test-enclave" in names
        assert "hidden-enclave" not in names


# ---------------------------------------------------------------------------
# Connector enclave scoping
# ---------------------------------------------------------------------------

class TestConnectorEnclaveScoping:
    """Connectors are scoped to the enclaves the user has access to."""

    def test_connector_enclave_scoping(
        self, client, db_session, seed_data, admin_token, operator_token
    ):
        """An operator can see connectors in their enclave but NOT connectors
        in an enclave they have no access to.
        """
        enclave = seed_data["enclave"]
        ct = seed_data["connector_types"]["adcs_file"]
        admin_user = seed_data["admin_user"]

        # Connector in test-enclave (operator has access)
        c1 = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=enclave.id,
            name="visible-connector",
            config={},
            created_by=admin_user.id,
        )
        db_session.add(c1)

        # Second enclave with a connector
        other_enclave = Enclave(name="other-enc", description="Other")
        db_session.add(other_enclave)
        db_session.flush()

        c2 = ConnectorInstance(
            connector_type_id=ct.id,
            enclave_id=other_enclave.id,
            name="hidden-connector",
            config={},
            created_by=admin_user.id,
        )
        db_session.add(c2)
        db_session.flush()

        # Operator list: should see only visible-connector
        resp = client.get(
            "/api/v1/connectors/",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "visible-connector" in names
        assert "hidden-connector" not in names

        # Admin should see both
        resp_admin = client.get(
            "/api/v1/connectors/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_admin.status_code == 200
        admin_names = [c["name"] for c in resp_admin.json()]
        assert "visible-connector" in admin_names
        assert "hidden-connector" in admin_names


# ---------------------------------------------------------------------------
# Identity enclave scoping
# ---------------------------------------------------------------------------

class TestIdentityEnclaveScoping:
    """Identities are scoped to the enclaves the user has access to."""

    def test_identity_enclave_scoping(
        self, client, db_session, seed_data, viewer_token, admin_token
    ):
        """Viewer can see identities in their enclave but NOT identities in
        another enclave they have no access to.
        """
        enclave = seed_data["enclave"]
        now = datetime.now(timezone.utc)

        # Identity in test-enclave (viewer has access)
        i1 = Identity(
            enclave_id=enclave.id,
            identity_type="cert",
            display_name="visible-cert",
            fingerprint="fp-visible",
            normalized_data={},
            first_seen=now,
            last_seen=now,
            finding_ids=[],
        )
        db_session.add(i1)

        # Other enclave with an identity
        other_enclave = Enclave(name="other-id-enc", description="Other")
        db_session.add(other_enclave)
        db_session.flush()

        i2 = Identity(
            enclave_id=other_enclave.id,
            identity_type="cert",
            display_name="hidden-cert",
            fingerprint="fp-hidden",
            normalized_data={},
            first_seen=now,
            last_seen=now,
            finding_ids=[],
        )
        db_session.add(i2)
        db_session.flush()

        # Viewer list: should only see the identity in test-enclave
        resp = client.get(
            "/api/v1/identities/",
            headers={"Authorization": f"Bearer {viewer_token}"},
        )
        assert resp.status_code == 200
        names = [ident["display_name"] for ident in resp.json()]
        assert "visible-cert" in names
        assert "hidden-cert" not in names

        # Admin should see both
        resp_admin = client.get(
            "/api/v1/identities/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp_admin.status_code == 200
        admin_names = [ident["display_name"] for ident in resp_admin.json()]
        assert "visible-cert" in admin_names
        assert "hidden-cert" in admin_names


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------

class TestRoleAssignment:
    """POST /api/v1/users/{user_id}/roles -- admin assigns roles."""

    def test_role_assignment(self, client, db_session, seed_data, admin_token):
        """Admin can assign the operator role to the viewer user in
        test-enclave.
        """
        viewer = seed_data["viewer_user"]
        enclave = seed_data["enclave"]

        resp = client.post(
            f"/api/v1/users/{viewer.id}/roles",
            json={
                "user_id": str(viewer.id),
                "role_name": "operator",
                "enclave_id": str(enclave.id),
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == str(viewer.id)
        assert body["enclave_id"] == str(enclave.id)

        # Verify the assignment exists in the DB
        assignment = (
            db_session.query(UserRoleEnclave)
            .filter(
                UserRoleEnclave.user_id == viewer.id,
                UserRoleEnclave.enclave_id == enclave.id,
                UserRoleEnclave.role_id == seed_data["roles"]["operator"].id,
            )
            .first()
        )
        assert assignment is not None
