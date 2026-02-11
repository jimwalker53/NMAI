# NMIA — Non-Human Identity Authority

## Overview

NMIA is a web-based platform for discovering, inventorying, and managing non-human identities (NHIs) across enterprise environments. It provides centralized visibility into service accounts and certificates with automated risk scoring.

### Key Capabilities

- **Discovery**: Ingest AD service accounts via LDAP/LDAPS and ADCS certificates via file import or remote Windows collector
- **Multi-Enclave**: Strict RBAC scoping — every resource belongs to an enclave; users get role+enclave assignments
- **Two-Stage Ingestion**: Raw Findings → Normalized Identities with full provenance
- **Risk Scoring**: Automated scoring based on certificate expiry, ownership gaps, and missing system links
- **Scheduled & On-Demand**: Cron expressions for connector schedules plus "Run Now"
- **SAN Parsing**: Remote collector fetches cert blobs to parse SANs (exports often omit them)

## Architecture

```
┌──────────┐     ┌──────────────┐     ┌────────────┐
│  React   │────▶│  FastAPI     │────▶│ PostgreSQL │
│  UI      │◀────│  API Server  │◀────│            │
│ :5173    │     │  :8000       │     │  :5432     │
└──────────┘     └──────┬───────┘     └─────┬──────┘
                        │                    │
                 ┌──────▼───────┐     ┌─────▼──────┐
                 │   Worker     │     │  Alembic   │
                 │  (scheduler) │─────│ migrations │
                 └──────────────┘     └────────────┘

┌─────────────────┐        ┌──────────────┐
│ Windows         │───────▶│ API ingest   │
│ Collector :9000 │  push  │ endpoint     │
│ (certutil+SAN)  │        └──────────────┘
└─────────────────┘
```

## Quick Start

Prerequisites: Docker, Docker Compose, Make

### 1. Start services

```bash
git clone <repo-url>
cd nmia
make up
```

Wait for containers to become healthy (~20 seconds on first build).

### 2. Run database migrations

```bash
make migrate
```

### 3. Create the admin account (interactive)

```bash
make bootstrap
```

> **There are no default passwords.** The admin password is set interactively during bootstrap. The system will not function until you run this step.

You will see:

```
============================================================
  NMIA — Non-Human Identity Authority
  First-Run Bootstrap
============================================================

[1/5] Creating RBAC roles ...        done  admin, operator, viewer, auditor
[2/5] Creating connector types ...   done  ad_ldap, adcs_file, adcs_remote
[3/5] Creating default enclave ...   done  Default
[4/5] Setting up GlobalAdmin account ...

  Admin username [admin]: myadmin
  Admin password: ********
  Confirm password: ********

[5/5] Creating admin user ...        done

============================================================
  Bootstrap complete!
  Username: myadmin
  Login at: http://localhost:5173
============================================================
```

- Prompts for admin username (defaults to `admin`)
- Prompts for password with hidden input — **no default password is stored anywhere**
- Password must be at least 8 characters and must be confirmed
- Refuses to run if users already exist (one-time operation)

### 4. (Optional) Seed sample data

```bash
make seed
```

This runs an interactive prompt that creates clearly-marked fake data:

- **Lab enclave** for experimentation
- **Sample connectors** — AD LDAP and ADCS File with example configs
- **Sample identities** — service accounts and certificates with varying risk profiles (expiring, orphaned, high-risk)

All seed data is prefixed with `[SAMPLE]`. Safe to skip in production.

### 5. Open the UI

| Service    | URL                       |
|------------|---------------------------|
| UI         | http://localhost:5173      |
| API        | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs |
| Collector  | http://localhost:9000      |

Login with the credentials you created in step 3.

### Complete copy/paste bootstrap

```bash
# Full first-run sequence
make up && make migrate && make bootstrap

# With sample data
make up && make migrate && make bootstrap && make seed
```

### Common Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Tail logs
make migrate     # Run database migrations
make bootstrap   # Interactive first-run setup (creates admin account)
make seed        # Interactive sample data population
make test        # Run API tests
make shell       # Bash shell in API container
make psql        # PostgreSQL shell
make clean       # Stop + remove volumes (destroys data)
make restart     # Full restart (down + up)
```

## Tech Stack

| Layer     | Technology                                          |
|-----------|-----------------------------------------------------|
| UI        | React 18 + Vite + TypeScript                        |
| Components| MUI (Material UI) v5 — drawer layout, data tables   |
| State     | TanStack React Query (server cache + mutations)     |
| Forms     | react-hook-form + zod (validation)                  |
| Backend   | FastAPI + SQLAlchemy + Alembic + PostgreSQL          |
| Worker    | Python + APScheduler                                |
| Collector | Python FastAPI (Windows service)                    |
| Dev env   | Docker Compose                                      |

## Running the UI Locally (outside Docker)

If you prefer hot-reload development outside of Docker:

```bash
cd ui
npm install
npm run dev
```

The Vite dev server starts at http://localhost:5173. By default it proxies `/api` requests to the API container at `http://localhost:8000`. Make sure the API is running (`make api` or `make up`).

To point at a different API host, set the `VITE_API_BASE_URL` environment variable:

```bash
VITE_API_BASE_URL=http://192.168.1.50:8000 npm run dev
```

Build for production:

```bash
cd ui
npm run build     # outputs to ui/dist/
```

## Configuring Connectors

All connector configuration is done through the UI. Navigate to **Connectors** in the left drawer.

### AD Service Account Connector (LDAP)

Discovers service accounts via LDAP queries against Active Directory.

**Setup:**

1. Go to **Connectors → Add Connector**
2. Select type **AD LDAP**, choose an enclave, give it a name
3. Click the new connector to open its detail page
4. Fill in the type-specific configuration fields:

| Field           | Example                                                                 |
|-----------------|-------------------------------------------------------------------------|
| LDAP Server     | `ldap://dc01.corp.local`                                               |
| Port            | `389` (LDAP) or `636` (LDAPS)                                          |
| SSL             | Toggle on for LDAPS                                                     |
| Bind DN         | `CN=svc-nmia,OU=ServiceAccounts,DC=corp,DC=local`                      |
| Bind Password   | Service account password                                                |
| Search Base     | `DC=corp,DC=local`                                                      |
| Search Filter   | `(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))` |

5. Set a cron schedule (e.g., `0 2 * * *` for daily at 2 AM). The UI shows a human-readable hint below the field.
6. Click **Save Configuration**
7. Click **Test** to verify connectivity, then **Run Now** to trigger the first sync

### ADCS Certificate Connector — File Import

Ingests certificate inventory from a CSV export (e.g., from `certutil -view -out` or a CA admin export).

**Setup:**

1. Go to **Connectors → Add Connector**
2. Select type **ADCS File**, choose an enclave, give it a name
3. Open the connector detail page
4. Optionally configure delimiter and encoding
5. Use the **File Upload** widget to upload a CSV

**Expected CSV columns:**

```
serial_number, common_name, subject_dn, issuer_dn, not_before, not_after, template_name, thumbprint, san
```

The `san` column is optional — if your CA export omits SANs, use the Remote Collector below to backfill them.

### ADCS Certificate Connector — Remote Collector

Uses a Windows agent to run `certutil` against a live CA, fetch cert blobs, and parse SANs that CSV exports typically omit.

**Setup:**

1. Go to **Connectors → Add Connector**, select type **ADCS Remote**
2. Fill in configuration:

| Field    | Example                |
|----------|------------------------|
| CA Host  | `ca01.corp.local`      |
| CA Name  | `Corp-Issuing-CA`      |
| SSL      | Toggle on              |
| Username | `DOMAIN\svc-nmia`     |
| Password | Service account password|

3. Save and note the **connector instance ID** (shown in the URL)
4. On a Windows machine with network access to the CA, install the collector:

```powershell
cd collector-windows
pip install -e .

# Set environment variables
$env:NMIA_SERVER_URL = "http://nmia-api-host:8000"
$env:CONNECTOR_INSTANCE_ID = "<connector-id-from-step-3>"

# Run manually
python -m nmia_collector
```

Or install as a Windows service:

```powershell
.\collector-windows\scripts\install-service.ps1 -Port 9000
```

5. Trigger a collection run from the NMIA UI (**Run Now**) or via API:

```bash
curl -X POST http://collector-host:9000/collector/v1/adcs/run \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "inventory_san",
    "since_days": 30,
    "max_records": 10000,
    "max_san_fetch": 500
  }'
```

The collector runs `certutil -view`, fetches individual cert blobs for SAN extraction via the `cryptography` library, and pushes results to the NMIA API ingest endpoint.

## Data Model

### Two-Stage Ingestion

- **Findings**: Immutable raw records from connectors, tagged with source/job
- **Identities**: Normalized, correlated, deduplicated with risk scores

### Identity Fingerprints

| Type               | Fingerprint                |
|--------------------|----------------------------|
| AD Service Account | `objectSid`                |
| ADCS Certificate   | `issuer_dn\|serial_number` |

### Risk Scoring

| Factor                     | Points |
|----------------------------|--------|
| No owner assigned          | +25    |
| No linked system           | +15    |
| Certificate expired        | +40    |
| Cert expiring < 30 days    | +30    |
| Cert expiring < 90 days    | +15    |
| No SAN data                | +10    |
| Password > 365 days old    | +20    |
| Account disabled           | +10    |

## Security Notes

- **No default passwords** — admin account is created interactively via `make bootstrap`
- JWT authentication with bcrypt password hashing
- Four RBAC roles: admin, operator, viewer, auditor
- Enclave-scoped access on every endpoint
- Connector credentials stored in DB config JSON (encrypt at rest in production — TODO)
- Audit logging for administrative actions
- No hardcoded connector instances — all configuration via UI
- Change `SECRET_KEY` in production
- CORS configured for UI origin only

## Project Structure

```
nmia/
├── api/                    # FastAPI backend
│   ├── src/nmia/          # Main package
│   │   ├── auth/          # Authentication, RBAC
│   │   ├── core/          # DB, models, shared schemas
│   │   ├── enclaves/      # Enclave management
│   │   ├── users/         # User management
│   │   ├── connectors/    # Connector CRUD, scheduling, jobs
│   │   ├── ingestion/     # Ingest, normalize, correlate, risk
│   │   ├── reports/       # Expiring/orphaned reports
│   │   ├── util/          # Cron, hashing, logging utilities
│   │   ├── bootstrap.py   # Interactive first-run setup CLI
│   │   └── seed.py        # Sample data population CLI
│   └── tests/
├── worker/                 # Background job scheduler
│   └── src/nmia_worker/
│       ├── connectors/    # AD and ADCS collectors
│       └── pipeline/      # Normalize, correlate, risk
├── ui/                     # React + Vite + TypeScript + MUI
│   └── src/
│       ├── auth/          # Login, auth context
│       ├── layout/        # App shell, navigation
│       ├── api/           # Axios client + TanStack Query hooks
│       └── pages/         # All pages
├── collector-windows/      # Windows ADCS collector
│   └── src/nmia_collector/
│       ├── adcs/          # Certutil, SAN parsing, push
│       └── jobs/          # Job store, runner
├── docs/                   # Documentation
│   └── runbooks/
├── docker-compose.yml
└── Makefile
```

## API Reference

See [docs/api-contract.md](docs/api-contract.md) for full API documentation.

Key endpoints:

- `POST /api/v1/auth/login`
- `CRUD /api/v1/enclaves`
- `CRUD /api/v1/users` + `POST /users/{id}/roles`
- `CRUD /api/v1/connectors` + `POST /{id}/test` + `POST /{id}/run` + `GET /{id}/jobs`
- `POST /api/v1/ingest/adcs/{connector_id}`
- `GET /api/v1/identities` + `PUT /{id}`
- `GET /api/v1/reports/expiring` + `GET /reports/orphaned`

Interactive docs: http://localhost:8000/docs

## Roadmap

- [ ] **Auth Federation**: SAMLv2, OIDC, OAuth2
- [ ] **More Connectors**: Keyfactor Command, EJBCA, HashiCorp Vault PKI
- [ ] **Database**: MSSQL support alongside PostgreSQL
- [ ] **Collector**: MSI installer, auto-enrollment monitoring
- [ ] **ML Risk Scoring**: Anomaly detection, behavioral analysis
- [ ] **Reporting**: CSV/PDF export, scheduled email reports
- [ ] **HA**: Worker clustering, API horizontal scaling
- [ ] **Secrets**: Vault integration for connector credential encryption

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run `make test` to verify
5. Submit a pull request

## License

See [LICENSE](LICENSE) for details.
