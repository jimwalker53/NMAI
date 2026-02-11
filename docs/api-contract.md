# NMIA API Contract

Base URL: `http://localhost:8000`

All API endpoints (except login) require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Responses use standard HTTP status codes. Error responses follow the format:

```json
{
  "detail": "Error description"
}
```

---

## Table of Contents

- [Authentication](#authentication)
- [Enclaves](#enclaves)
- [Users](#users)
- [Connectors](#connectors)
- [Ingestion](#ingestion)
- [Identities](#identities)
- [Reports](#reports)
- [Collector (Windows)](#collector-windows)

---

## Authentication

### POST /api/v1/auth/login

Authenticate a user and receive a JWT access token.

**Auth required:** No

**Request body:**

```json
{
  "username": "admin",
  "password": "admin"
}
```

**Response 200:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Response 401:**

```json
{
  "detail": "Invalid credentials"
}
```

---

## Enclaves

Enclaves are logical boundaries that scope all resources. Users only see enclaves
they have been granted access to.

### GET /api/v1/enclaves

List enclaves accessible to the authenticated user.

**Auth required:** Yes (any role)

**Response 200:**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Production",
    "description": "Production environment NHIs",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "name": "Development",
    "description": "Dev environment NHIs",
    "created_at": "2025-01-16T08:00:00Z",
    "updated_at": "2025-01-16T08:00:00Z"
  }
]
```

### POST /api/v1/enclaves

Create a new enclave.

**Auth required:** Yes (admin only)

**Request body:**

```json
{
  "name": "Staging",
  "description": "Staging environment NHIs"
}
```

**Response 201:**

```json
{
  "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "name": "Staging",
  "description": "Staging environment NHIs",
  "created_at": "2025-02-01T14:00:00Z",
  "updated_at": "2025-02-01T14:00:00Z"
}
```

**Response 403:**

```json
{
  "detail": "Admin access required"
}
```

### GET /api/v1/enclaves/{id}

Get a single enclave by ID.

**Auth required:** Yes (must have access to the enclave)

**Response 200:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Production",
  "description": "Production environment NHIs",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Response 404:**

```json
{
  "detail": "Enclave not found"
}
```

### PUT /api/v1/enclaves/{id}

Update an enclave.

**Auth required:** Yes (admin only)

**Request body:**

```json
{
  "name": "Production (US-East)",
  "description": "Updated description"
}
```

**Response 200:**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Production (US-East)",
  "description": "Updated description",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-02-01T15:00:00Z"
}
```

### DELETE /api/v1/enclaves/{id}

Delete an enclave and all associated resources.

**Auth required:** Yes (admin only)

**Response 204:** No content

**Response 403:**

```json
{
  "detail": "Admin access required"
}
```

---

## Users

### GET /api/v1/users

List all users.

**Auth required:** Yes (admin only)

**Response 200:**

```json
[
  {
    "id": "d4e5f6a7-b8c9-0123-def0-123456789abc",
    "username": "admin",
    "email": "admin@example.com",
    "is_active": true,
    "is_superuser": true,
    "created_at": "2025-01-01T00:00:00Z",
    "roles": [
      {
        "role_name": "admin",
        "enclave_id": null
      }
    ]
  },
  {
    "id": "e5f6a7b8-c9d0-1234-ef01-23456789abcd",
    "username": "analyst1",
    "email": "analyst1@example.com",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2025-01-10T09:00:00Z",
    "roles": [
      {
        "role_name": "analyst",
        "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
      }
    ]
  }
]
```

### POST /api/v1/users

Create a new user.

**Auth required:** Yes (admin only)

**Request body:**

```json
{
  "username": "operator1",
  "email": "operator1@example.com",
  "password": "SecurePassword123!"
}
```

**Response 201:**

```json
{
  "id": "f6a7b8c9-d0e1-2345-f012-3456789abcde",
  "username": "operator1",
  "email": "operator1@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-02-01T16:00:00Z",
  "roles": []
}
```

**Response 409:**

```json
{
  "detail": "Username already exists"
}
```

### GET /api/v1/users/{id}

Get a single user by ID.

**Auth required:** Yes (admin, or the user themselves)

**Response 200:**

```json
{
  "id": "f6a7b8c9-d0e1-2345-f012-3456789abcde",
  "username": "operator1",
  "email": "operator1@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-02-01T16:00:00Z",
  "roles": [
    {
      "role_name": "operator",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
  ]
}
```

### PUT /api/v1/users/{id}

Update a user.

**Auth required:** Yes (admin, or the user themselves for limited fields)

**Request body:**

```json
{
  "email": "new-email@example.com",
  "password": "NewSecurePassword456!"
}
```

**Response 200:**

```json
{
  "id": "f6a7b8c9-d0e1-2345-f012-3456789abcde",
  "username": "operator1",
  "email": "new-email@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-02-01T16:00:00Z",
  "roles": []
}
```

### DELETE /api/v1/users/{id}

Deactivate a user (soft delete).

**Auth required:** Yes (admin only)

**Response 200:**

```json
{
  "id": "f6a7b8c9-d0e1-2345-f012-3456789abcde",
  "username": "operator1",
  "email": "new-email@example.com",
  "is_active": false,
  "is_superuser": false,
  "created_at": "2025-02-01T16:00:00Z",
  "roles": []
}
```

### POST /api/v1/users/{id}/roles

Assign a role to a user for a specific enclave.

**Auth required:** Yes (admin only)

**Request body:**

```json
{
  "role_name": "operator",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Response 201:**

```json
{
  "user_id": "f6a7b8c9-d0e1-2345-f012-3456789abcde",
  "role_name": "operator",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "assigned_at": "2025-02-01T17:00:00Z"
}
```

**Response 409:**

```json
{
  "detail": "Role already assigned"
}
```

### DELETE /api/v1/users/{id}/roles/{role_enclave_id}

Remove a role assignment from a user.

**Auth required:** Yes (admin only)

**Path parameters:**

- `id` -- User ID
- `role_enclave_id` -- The ID of the role-enclave assignment record

**Response 204:** No content

---

## Connectors

Connectors define how NMIA discovers NHIs from external systems.

### GET /api/v1/connectors/types

List available connector types.

**Auth required:** Yes (any role)

**Response 200:**

```json
[
  {
    "code": "ad_service_account",
    "display_name": "Active Directory Service Accounts",
    "description": "Discovers service accounts in Active Directory via LDAP",
    "config_schema": {
      "ldap_url": {"type": "string", "required": true},
      "bind_dn": {"type": "string", "required": true},
      "bind_password": {"type": "string", "required": true, "sensitive": true},
      "search_base": {"type": "string", "required": true},
      "search_filter": {"type": "string", "required": false}
    }
  },
  {
    "code": "adcs_certificate",
    "display_name": "ADCS Certificates",
    "description": "Discovers certificates issued by Active Directory Certificate Services",
    "config_schema": {
      "mode": {"type": "string", "enum": ["push"], "required": true},
      "collector_url": {"type": "string", "required": false}
    }
  }
]
```

### GET /api/v1/connectors

List connectors accessible to the authenticated user (scoped by enclave).

**Auth required:** Yes (operator, analyst, admin)

**Query parameters:**

- `enclave_id` (optional) -- Filter by enclave

**Response 200:**

```json
[
  {
    "id": "11111111-2222-3333-4444-555555555555",
    "connector_type_code": "ad_service_account",
    "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Corp AD Service Accounts",
    "config": {
      "ldap_url": "ldaps://dc01.corp.example.com:636",
      "bind_dn": "CN=nmia-svc,OU=Service Accounts,DC=corp,DC=example,DC=com",
      "bind_password": "********",
      "search_base": "DC=corp,DC=example,DC=com"
    },
    "cron_expression": "0 2 * * *",
    "is_enabled": true,
    "last_run_at": "2025-02-01T02:00:00Z",
    "last_run_status": "success",
    "created_at": "2025-01-20T10:00:00Z"
  }
]
```

**Note:** Sensitive fields like `bind_password` are masked in list responses.

### POST /api/v1/connectors

Create a new connector.

**Auth required:** Yes (operator or admin, scoped to enclave)

**Request body:**

```json
{
  "connector_type_code": "ad_service_account",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Corp AD Service Accounts",
  "config": {
    "ldap_url": "ldaps://dc01.corp.example.com:636",
    "bind_dn": "CN=nmia-svc,OU=Service Accounts,DC=corp,DC=example,DC=com",
    "bind_password": "RealPassword123!",
    "search_base": "DC=corp,DC=example,DC=com"
  },
  "cron_expression": "0 2 * * *"
}
```

**Response 201:**

```json
{
  "id": "11111111-2222-3333-4444-555555555555",
  "connector_type_code": "ad_service_account",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Corp AD Service Accounts",
  "config": {
    "ldap_url": "ldaps://dc01.corp.example.com:636",
    "bind_dn": "CN=nmia-svc,OU=Service Accounts,DC=corp,DC=example,DC=com",
    "bind_password": "********",
    "search_base": "DC=corp,DC=example,DC=com"
  },
  "cron_expression": "0 2 * * *",
  "is_enabled": true,
  "last_run_at": null,
  "last_run_status": null,
  "created_at": "2025-01-20T10:00:00Z"
}
```

### GET /api/v1/connectors/{id}

Get a single connector by ID.

**Auth required:** Yes (must have access to the connector's enclave)

**Response 200:** Same shape as the object in the list response.

### PUT /api/v1/connectors/{id}

Update a connector.

**Auth required:** Yes (operator or admin, scoped to enclave)

**Request body:**

```json
{
  "name": "Corp AD Service Accounts (Updated)",
  "config": {
    "ldap_url": "ldaps://dc02.corp.example.com:636",
    "bind_dn": "CN=nmia-svc,OU=Service Accounts,DC=corp,DC=example,DC=com",
    "bind_password": "NewPassword456!",
    "search_base": "DC=corp,DC=example,DC=com"
  },
  "cron_expression": "0 3 * * *",
  "is_enabled": true
}
```

**Response 200:** Updated connector object.

### DELETE /api/v1/connectors/{id}

Delete a connector and its associated jobs/findings.

**Auth required:** Yes (operator or admin, scoped to enclave)

**Response 204:** No content

### POST /api/v1/connectors/{id}/test

Test a connector's configuration without creating a full job.

**Auth required:** Yes (operator or admin, scoped to enclave)

**Response 200:**

```json
{
  "status": "success",
  "message": "Successfully connected to ldaps://dc01.corp.example.com:636",
  "details": {
    "server": "dc01.corp.example.com",
    "base_dn_accessible": true,
    "estimated_results": 142
  }
}
```

**Response 200 (failure):**

```json
{
  "status": "error",
  "message": "Connection failed: unable to bind with provided credentials",
  "details": {
    "error_code": "LDAP_INVALID_CREDENTIALS"
  }
}
```

### POST /api/v1/connectors/{id}/run

Trigger an immediate connector run (creates a job).

**Auth required:** Yes (operator or admin, scoped to enclave)

**Response 202:**

```json
{
  "job_id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
  "connector_id": "11111111-2222-3333-4444-555555555555",
  "status": "pending",
  "created_at": "2025-02-01T18:00:00Z"
}
```

### GET /api/v1/connectors/{id}/jobs

List jobs for a connector.

**Auth required:** Yes (must have access to the connector's enclave)

**Query parameters:**

- `limit` (optional, default 20) -- Maximum number of results
- `offset` (optional, default 0) -- Pagination offset

**Response 200:**

```json
{
  "items": [
    {
      "id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
      "connector_id": "11111111-2222-3333-4444-555555555555",
      "status": "completed",
      "started_at": "2025-02-01T02:00:01Z",
      "completed_at": "2025-02-01T02:03:45Z",
      "findings_count": 142,
      "error_message": null
    },
    {
      "id": "66666666-7777-8888-9999-aaaaaaaaaaaa",
      "connector_id": "11111111-2222-3333-4444-555555555555",
      "status": "failed",
      "started_at": "2025-01-31T02:00:01Z",
      "completed_at": "2025-01-31T02:00:05Z",
      "findings_count": 0,
      "error_message": "LDAP connection timed out"
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

---

## Ingestion

Push-based ingestion for connectors that send data to NMIA (e.g., the Windows
ADCS collector).

### POST /api/v1/ingest/adcs/{connector_id}

Ingest ADCS certificate data for a specific connector.

**Auth required:** Yes (operator or admin, scoped to connector's enclave)

**Query parameters:**

- `job_id` (optional) -- Associate the ingested data with an existing job ID

**Option A -- JSON body:**

```json
{
  "certificates": [
    {
      "serial_number": "6A00000001",
      "subject": "CN=web-server-01.corp.example.com",
      "issuer_dn": "CN=Corp-CA,DC=corp,DC=example,DC=com",
      "not_before": "2024-06-01T00:00:00Z",
      "not_after": "2025-06-01T00:00:00Z",
      "template_name": "WebServer",
      "san_entries": ["DNS:web-server-01.corp.example.com"],
      "requester": "CORP\\svc-iis",
      "key_length": 2048,
      "signature_algorithm": "sha256RSA",
      "status": "issued"
    }
  ]
}
```

**Option B -- CSV file upload:**

```
POST /api/v1/ingest/adcs/{connector_id}?job_id=xxx
Content-Type: multipart/form-data

file=@certificates.csv
```

CSV columns: `serial_number,subject,issuer_dn,not_before,not_after,template_name,san_entries,requester,key_length,signature_algorithm,status`

**Response 202:**

```json
{
  "status": "accepted",
  "findings_created": 1,
  "job_id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
}
```

**Response 400:**

```json
{
  "detail": "Invalid certificate data: missing required field 'serial_number'"
}
```

---

## Identities

Normalized NHI records with provenance tracking.

### GET /api/v1/identities

List identities with filtering and search.

**Auth required:** Yes (any role, scoped by enclave)

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `enclave_id` | UUID | Filter by enclave |
| `identity_type` | string | Filter by type: `service_account`, `certificate`, `api_key`, `bot_account` |
| `owner` | string | Filter by owner (exact match) |
| `linked_system` | string | Filter by linked system (exact match) |
| `search` | string | Free-text search across display name, owner, linked system |
| `min_risk` | integer | Minimum risk score (0-100) |
| `max_risk` | integer | Maximum risk score (0-100) |
| `limit` | integer | Page size (default 50) |
| `offset` | integer | Pagination offset (default 0) |

**Response 200:**

```json
{
  "items": [
    {
      "id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
      "fingerprint": "ad_svc_acct:S-1-5-21-3623811015-3361044348-30300820-1013",
      "identity_type": "service_account",
      "display_name": "svc-backup",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_type": "ad_service_account",
      "owner": "backup-team@example.com",
      "linked_system": "Veeam Backup",
      "risk_score": 35,
      "attributes": {
        "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1013",
        "sAMAccountName": "svc-backup",
        "servicePrincipalName": ["HOST/backup-srv"],
        "whenCreated": "2022-03-15T00:00:00Z",
        "passwordLastSet": "2024-11-01T08:30:00Z"
      },
      "first_seen": "2025-01-20T02:00:00Z",
      "last_seen": "2025-02-01T02:00:00Z",
      "created_at": "2025-01-20T02:00:00Z",
      "updated_at": "2025-02-01T02:00:00Z"
    },
    {
      "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "fingerprint": "adcs_cert:CN=Corp-CA,DC=corp,DC=example,DC=com|6A00000001",
      "identity_type": "certificate",
      "display_name": "CN=web-server-01.corp.example.com",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_type": "adcs_certificate",
      "owner": null,
      "linked_system": null,
      "risk_score": 72,
      "attributes": {
        "serial_number": "6A00000001",
        "subject": "CN=web-server-01.corp.example.com",
        "issuer_dn": "CN=Corp-CA,DC=corp,DC=example,DC=com",
        "not_before": "2024-06-01T00:00:00Z",
        "not_after": "2025-06-01T00:00:00Z",
        "template_name": "WebServer",
        "requester": "CORP\\svc-iis"
      },
      "first_seen": "2025-01-20T02:00:00Z",
      "last_seen": "2025-02-01T02:00:00Z",
      "created_at": "2025-01-20T02:00:00Z",
      "updated_at": "2025-02-01T02:00:00Z"
    }
  ],
  "total": 284,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/identities/{id}

Get a single identity with full detail including provenance.

**Auth required:** Yes (must have access to the identity's enclave)

**Response 200:**

```json
{
  "id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
  "fingerprint": "ad_svc_acct:S-1-5-21-3623811015-3361044348-30300820-1013",
  "identity_type": "service_account",
  "display_name": "svc-backup",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source_type": "ad_service_account",
  "owner": "backup-team@example.com",
  "linked_system": "Veeam Backup",
  "risk_score": 35,
  "attributes": {
    "objectSid": "S-1-5-21-3623811015-3361044348-30300820-1013",
    "sAMAccountName": "svc-backup",
    "servicePrincipalName": ["HOST/backup-srv"],
    "whenCreated": "2022-03-15T00:00:00Z",
    "passwordLastSet": "2024-11-01T08:30:00Z"
  },
  "first_seen": "2025-01-20T02:00:00Z",
  "last_seen": "2025-02-01T02:00:00Z",
  "findings": [
    {
      "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
      "job_id": "77777777-8888-9999-aaaa-bbbbbbbbbbbb",
      "connector_id": "11111111-2222-3333-4444-555555555555",
      "source_type": "ad_service_account",
      "raw_attributes": { "...": "full raw LDAP attributes" },
      "discovered_at": "2025-02-01T02:03:12Z"
    },
    {
      "id": "cccccccc-dddd-eeee-ffff-000000000000",
      "job_id": "66666666-7777-8888-9999-aaaaaaaaaaaa",
      "connector_id": "11111111-2222-3333-4444-555555555555",
      "source_type": "ad_service_account",
      "raw_attributes": { "...": "full raw LDAP attributes" },
      "discovered_at": "2025-01-20T02:02:45Z"
    }
  ],
  "created_at": "2025-01-20T02:00:00Z",
  "updated_at": "2025-02-01T02:00:00Z"
}
```

### PUT /api/v1/identities/{id}

Update enrichment fields on an identity.

**Auth required:** Yes (operator or admin, scoped to enclave)

**Request body:**

```json
{
  "owner": "backup-team@example.com",
  "linked_system": "Veeam Backup"
}
```

**Response 200:**

```json
{
  "id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
  "fingerprint": "ad_svc_acct:S-1-5-21-3623811015-3361044348-30300820-1013",
  "identity_type": "service_account",
  "display_name": "svc-backup",
  "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "source_type": "ad_service_account",
  "owner": "backup-team@example.com",
  "linked_system": "Veeam Backup",
  "risk_score": 35,
  "attributes": { "...": "..." },
  "first_seen": "2025-01-20T02:00:00Z",
  "last_seen": "2025-02-01T02:00:00Z",
  "created_at": "2025-01-20T02:00:00Z",
  "updated_at": "2025-02-01T18:30:00Z"
}
```

---

## Reports

Pre-built analytical queries for NHI risk management.

### GET /api/v1/reports/expiring

List identities (certificates) expiring within a given window.

**Auth required:** Yes (any role, scoped by enclave)

**Query parameters:**

- `days` (optional, default 90) -- Number of days in the lookahead window
- `enclave_id` (optional) -- Filter by enclave

**Response 200:**

```json
{
  "report": "expiring_certificates",
  "parameters": {
    "days": 90,
    "as_of": "2025-02-01T00:00:00Z"
  },
  "items": [
    {
      "identity_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "display_name": "CN=web-server-01.corp.example.com",
      "identity_type": "certificate",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "not_after": "2025-04-15T00:00:00Z",
      "days_until_expiry": 73,
      "owner": null,
      "linked_system": null,
      "risk_score": 72
    }
  ],
  "total": 12
}
```

### GET /api/v1/reports/orphaned

List identities with no assigned owner.

**Auth required:** Yes (any role, scoped by enclave)

**Query parameters:**

- `enclave_id` (optional) -- Filter by enclave

**Response 200:**

```json
{
  "report": "orphaned_identities",
  "parameters": {
    "as_of": "2025-02-01T00:00:00Z"
  },
  "items": [
    {
      "identity_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
      "display_name": "CN=web-server-01.corp.example.com",
      "identity_type": "certificate",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_type": "adcs_certificate",
      "first_seen": "2025-01-20T02:00:00Z",
      "last_seen": "2025-02-01T02:00:00Z",
      "risk_score": 72
    },
    {
      "identity_id": "dddddddd-eeee-ffff-0000-111111111111",
      "display_name": "svc-legacy-app",
      "identity_type": "service_account",
      "enclave_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_type": "ad_service_account",
      "first_seen": "2025-01-20T02:00:00Z",
      "last_seen": "2025-02-01T02:00:00Z",
      "risk_score": 55
    }
  ],
  "total": 47
}
```

---

## Collector (Windows)

These endpoints are served by the Windows Collector service (port 9000), not the
main NMIA API server. They allow remote control of certificate discovery on Windows
hosts running near ADCS CAs.

### POST /collector/v1/adcs/run

Start a certificate discovery job on the collector.

**Auth required:** None (network-level trust; TODO: API key auth)

**Request body:**

```json
{
  "mode": "full",
  "since_days": null,
  "max_records": 10000,
  "max_san_fetch": 1000,
  "callback_url": "http://nmia-api:8000/api/v1/ingest/adcs/11111111-2222-3333-4444-555555555555"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | `full` or `incremental`. Full scans all certs; incremental scans since `since_days` ago. |
| `since_days` | integer or null | For incremental mode: number of days to look back. |
| `max_records` | integer | Maximum certificates to retrieve (safety limit). |
| `max_san_fetch` | integer | Maximum SANs to fetch per certificate. |
| `callback_url` | string or null | If set, collector POSTs results to this URL on completion. |

**Response 202:**

```json
{
  "job_id": "collector-job-001",
  "status": "running",
  "started_at": "2025-02-01T19:00:00Z"
}
```

### GET /collector/v1/jobs/{id}

Get the status of a collector job.

**Auth required:** None (network-level trust; TODO: API key auth)

**Response 200:**

```json
{
  "job_id": "collector-job-001",
  "status": "completed",
  "started_at": "2025-02-01T19:00:00Z",
  "completed_at": "2025-02-01T19:05:30Z",
  "records_found": 3842,
  "records_processed": 3842,
  "errors": 0
}
```

**Status values:** `pending`, `running`, `completed`, `failed`

### GET /collector/v1/jobs/{id}/logs

Stream or retrieve logs for a collector job.

**Auth required:** None (network-level trust; TODO: API key auth)

**Response 200:**

```json
{
  "job_id": "collector-job-001",
  "logs": [
    {"timestamp": "2025-02-01T19:00:00Z", "level": "INFO", "message": "Starting ADCS scan in full mode"},
    {"timestamp": "2025-02-01T19:00:01Z", "level": "INFO", "message": "Running certutil -view -restrict 'Disposition=20'"},
    {"timestamp": "2025-02-01T19:03:00Z", "level": "INFO", "message": "Retrieved 3842 certificate records"},
    {"timestamp": "2025-02-01T19:05:00Z", "level": "INFO", "message": "Parsing complete, 3842 records processed"},
    {"timestamp": "2025-02-01T19:05:30Z", "level": "INFO", "message": "Pushed results to callback URL"}
  ]
}
```

### GET /collector/v1/jobs/{id}/result

Retrieve the full result set of a completed collector job.

**Auth required:** None (network-level trust; TODO: API key auth)

**Response 200:**

```json
{
  "job_id": "collector-job-001",
  "status": "completed",
  "certificates": [
    {
      "serial_number": "6A00000001",
      "subject": "CN=web-server-01.corp.example.com",
      "issuer_dn": "CN=Corp-CA,DC=corp,DC=example,DC=com",
      "not_before": "2024-06-01T00:00:00Z",
      "not_after": "2025-06-01T00:00:00Z",
      "template_name": "WebServer",
      "san_entries": ["DNS:web-server-01.corp.example.com"],
      "requester": "CORP\\svc-iis",
      "key_length": 2048,
      "signature_algorithm": "sha256RSA",
      "status": "issued"
    }
  ],
  "total": 3842
}
```

**Response 404:**

```json
{
  "detail": "Job not found or results expired"
}
```

---

## RBAC Role Reference

| Endpoint Pattern | admin | operator | analyst | viewer |
|-----------------|-------|----------|---------|--------|
| `POST /auth/login` | -- | -- | -- | -- |
| `GET /enclaves` | all | scoped | scoped | scoped |
| `POST /enclaves` | yes | no | no | no |
| `PUT/DELETE /enclaves/{id}` | yes | no | no | no |
| `GET /users` | yes | no | no | no |
| `POST /users` | yes | no | no | no |
| `PUT/DELETE /users/{id}` | yes | self | self | self |
| `POST /users/{id}/roles` | yes | no | no | no |
| `GET /connectors` | all | scoped | scoped | scoped |
| `POST /connectors` | yes | scoped | no | no |
| `PUT/DELETE /connectors/{id}` | yes | scoped | no | no |
| `POST /connectors/{id}/test` | yes | scoped | no | no |
| `POST /connectors/{id}/run` | yes | scoped | no | no |
| `GET /connectors/{id}/jobs` | yes | scoped | scoped | scoped |
| `POST /ingest/*` | yes | scoped | no | no |
| `GET /identities` | all | scoped | scoped | scoped |
| `PUT /identities/{id}` | yes | scoped | no | no |
| `GET /reports/*` | all | scoped | scoped | scoped |

**Scoped** means the user must have the corresponding role for the enclave that owns the resource.

---

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async operation started) |
| 204 | No content (successful deletion) |
| 400 | Bad request (validation error) |
| 401 | Unauthorized (missing or invalid token) |
| 403 | Forbidden (insufficient role/permissions) |
| 404 | Not found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable entity (schema validation error) |
| 500 | Internal server error |
