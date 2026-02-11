# NMIA Architecture

## System Overview

NMIA (Non-Human Identity Authority) is a platform for discovering, inventorying, and
managing Non-Human Identities (NHIs) across enterprise infrastructure. NHIs include
service accounts, machine certificates, API keys, bot accounts, and any credential
or identity not directly tied to a human user.

NMIA provides:

- **Discovery** -- automated connectors that scan Active Directory, ADCS, and other
  identity stores to find NHIs.
- **Inventory** -- a normalized identity store with provenance tracking so every
  identity can be traced back to the raw finding that created it.
- **Risk scoring** -- expiring certificates, orphaned accounts, and other risk
  indicators surfaced through reports and dashboards.
- **Multi-enclave RBAC** -- strict tenant-style scoping so different teams or
  environments see only what they are authorized to see.

---

## Component Diagram

```
 +---------------------+         +-----------------------+
 |                     |  HTTPS  |                       |
 |   React UI (Vite)   +-------->+   FastAPI API Server   |
 |   :5173             |         |   :8000               |
 +---------------------+         +----------+------------+
                                            |
                              +-------------+-------------+
                              |                           |
                    +---------v----------+    +-----------v-----------+
                    |                    |    |                       |
                    |   PostgreSQL 16    |    |   Worker (APScheduler)|
                    |   :5432           |<---+   background process  |
                    |                    |    |                       |
                    +--------------------+    +-----------------------+
                              ^
                              |
               +--------------+--------------+
               |                             |
   +-----------v-----------+                 |
   |                       |    HTTP push    |
   |  Windows Collector    +------>----------+
   |  (certutil wrapper)   |         (via API /ingest)
   |  :9000                |
   +-----------------------+
```

### Components

| Component | Technology | Role |
|-----------|-----------|------|
| **API Server** | FastAPI, SQLAlchemy, Alembic | REST API, authentication, RBAC, CRUD, ingestion |
| **Worker** | APScheduler, SQLAlchemy | Polls database for scheduled connector jobs, executes connectors, writes findings |
| **PostgreSQL** | Postgres 16 (Alpine) | Persistent store for users, enclaves, connectors, findings, identities |
| **React UI** | React 18, Vite, TanStack Query | Single-page application for dashboards, identity browsing, connector management |
| **Windows Collector** | FastAPI (lightweight), certutil | Runs on Windows hosts near ADCS CAs, calls certutil to extract certificate data, pushes findings to the API ingest endpoint |

---

## Data Flow

### Discovery Flow (Scheduled Connector)

```
1. Admin creates a Connector via UI
      |
      v
2. Connector config persisted in DB (type, schedule, credentials)
      |
      v
3. Worker picks up due jobs on cron tick
      |
      v
4. Worker executes the connector (e.g., LDAP query to AD)
      |
      v
5. Raw results written as Findings in DB
      |
      v
6. Normalization pass converts Findings -> Identities
      |
      v
7. Identities visible in UI with provenance chain
```

### Discovery Flow (Windows Collector / Push)

```
1. Collector runs certutil -view on local ADCS CA
      |
      v
2. Collector parses certificate data into structured findings
      |
      v
3. Collector POSTs findings to API  POST /api/v1/ingest/adcs/{connector_id}
      |
      v
4. API validates, stores Findings in DB
      |
      v
5. Normalization pass converts Findings -> Identities
```

### User Interaction Flow

```
User -> React UI -> API (JWT auth) -> PostgreSQL
                                   -> Worker (reads/writes via shared DB)
```

---

## Two-Stage Ingestion

NMIA uses a two-stage ingestion model to separate raw data from normalized identities.

### Stage 1: Findings (Raw)

A **Finding** is the raw, unprocessed record as returned by a connector. Each finding:

- Belongs to a specific connector instance and job run.
- Contains the raw attributes as a JSON blob (`raw_attributes`).
- Has a `source_type` indicating the connector that produced it (e.g., `ad_service_account`, `adcs_certificate`).
- Is immutable once written -- findings are append-only.

### Stage 2: Identities (Normalized)

An **Identity** is the normalized, deduplicated representation of an NHI. Each identity:

- Has a deterministic `fingerprint` computed from its source type and key attributes.
- Links back to one or more findings via provenance records.
- Carries enrichment fields: `owner`, `linked_system`, `risk_score`, `identity_type`.
- Is upserted on fingerprint -- if a new finding matches an existing identity fingerprint, the identity is updated rather than duplicated.

### Provenance Tracking

Every identity maintains a chain of provenance:

```
Identity
  |-- Finding (from Job X, Connector Y, 2025-01-15)
  |-- Finding (from Job Z, Connector Y, 2025-02-01)  <- re-discovered
```

This allows auditors to trace any identity back to the exact scan run and raw data
that created or last confirmed it.

---

## Identity Fingerprinting

Fingerprints ensure that the same real-world NHI always maps to the same identity
record, regardless of how many times it is discovered.

| Source Type | Fingerprint Formula | Example |
|-------------|-------------------|---------|
| AD service account | `ad_svc_acct:{objectSid}` | `ad_svc_acct:S-1-5-21-...` |
| ADCS certificate | `adcs_cert:{issuer_dn}\|{serial_number}` | `adcs_cert:CN=CorpCA\|6A00...` |

The fingerprint is a deterministic string. On upsert, if a fingerprint already exists,
the existing identity is updated with the latest finding data.

---

## Multi-Enclave Architecture

An **enclave** is a logical boundary (similar to a tenant) that scopes all resources.

```
Enclave: "Production"
  |-- Connectors (scan prod AD, prod ADCS)
  |-- Findings (from prod scans)
  |-- Identities (prod NHIs)
  |-- Users with roles scoped to this enclave

Enclave: "Development"
  |-- Connectors (scan dev AD)
  |-- Findings
  |-- Identities
  |-- Users with roles scoped to this enclave
```

### RBAC Model

| Role | Scope | Permissions |
|------|-------|-------------|
| `admin` | Global | Full access to all enclaves, user management, system config |
| `analyst` | Per-enclave | Read identities, findings, reports within assigned enclaves |
| `operator` | Per-enclave | Manage connectors, run scans, edit identities within assigned enclaves |
| `viewer` | Per-enclave | Read-only access within assigned enclaves |

Every API request is scoped: the authenticated user's enclave memberships determine
which resources are visible. A user with `operator` on Enclave A and `viewer` on
Enclave B cannot modify anything in Enclave B.

---

## Authentication

### Current Implementation

- **Local JWT authentication**: Users authenticate with username/password, receive a
  JWT access token.
- Passwords are hashed with **bcrypt**.
- Tokens are signed with a configurable `SECRET_KEY` (HS256).
- Token lifetime is configurable (default 60 minutes).

### Planned / Placeholder

- **SAML 2.0** -- for enterprise SSO integration.
- **OIDC / OAuth2** -- for cloud identity provider integration (Azure AD, Okta).
- **API keys** -- for machine-to-machine auth (collector to API).

---

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| API framework | FastAPI | 0.110+ | Async REST API with OpenAPI docs |
| ORM | SQLAlchemy | 2.0+ | Database models and queries |
| Migrations | Alembic | 1.13+ | Schema migrations |
| Database | PostgreSQL | 16 | Primary data store |
| Task scheduling | APScheduler | 3.10+ | Cron-based connector job scheduling in worker |
| Frontend | React | 18 | Single-page application |
| Build tooling | Vite | 5+ | Frontend dev server and bundler |
| HTTP client | TanStack Query | 5+ | Data fetching and caching in UI |
| Auth | python-jose, passlib | -- | JWT signing, bcrypt hashing |
| Containerization | Docker, Docker Compose | -- | Local dev and deployment |
| Collector | certutil (Windows) | -- | ADCS certificate extraction |

---

## Directory Layout

```
NMAI/
  api/                  # FastAPI API server
    src/nmia/           # Application package
    tests/              # API tests
    pyproject.toml
    Dockerfile
  worker/               # Background job worker
    src/nmia_worker/    # Worker package
    tests/              # Worker tests
    pyproject.toml
    Dockerfile
  ui/                   # React frontend
    src/                # React source
    Dockerfile
    package.json
  collector-windows/    # Windows ADCS collector
    src/nmia_collector/ # Collector package
    scripts/            # PowerShell install scripts
    pyproject.toml
    Dockerfile
  docs/                 # Documentation
    runbooks/           # Operational runbooks
  docker-compose.yml    # Local dev orchestration
  Makefile              # Dev convenience targets
```
