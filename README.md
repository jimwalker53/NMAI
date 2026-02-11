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

```bash
git clone <repo-url>
cd nmia
make up
```

| Service    | URL                       |
|------------|---------------------------|
| UI         | http://localhost:5173      |
| API        | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs |
| Collector  | http://localhost:9000      |

**Default login**: admin / admin

### Common Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # Tail logs
make migrate     # Run database migrations
make test        # Run API tests
make clean       # Stop + remove volumes
make restart     # Full restart
```

## Configuring Connectors

### AD Service Account Connector (LDAP)

1. Login → Create Enclave → Navigate to Connectors
2. Create connector, type "AD LDAP"
3. Config JSON:

```json
{
  "server": "ldap://dc01.corp.local",
  "port": 389,
  "use_ssl": false,
  "bind_dn": "CN=svc-nmia,OU=ServiceAccounts,DC=corp,DC=local",
  "bind_password": "...",
  "search_base": "DC=corp,DC=local",
  "search_filter": "(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))"
}
```

4. Set cron schedule (e.g., `0 2 * * *` for 2am daily)
5. Test connectivity → Run Now

### ADCS Certificate Connector — File Import

1. Create connector, type "ADCS File"
2. Navigate to connector detail
3. Upload CSV with columns: serial_number, common_name, subject_dn, issuer_dn, not_before, not_after, template_name, thumbprint, san (optional)

### ADCS Certificate Connector — Remote Collector

1. Create connector, type "ADCS Remote" (note the connector instance ID)
2. Install Windows Collector on a CA-accessible machine:

```powershell
.\collector-windows\scripts\install-service.ps1 -Port 9000
```

3. Configure collector env: NMIA_SERVER_URL, CONNECTOR_INSTANCE_ID
4. Trigger: POST http://collector:9000/collector/v1/adcs/run

```json
{
  "mode": "inventory_san",
  "since_days": 30,
  "max_records": 10000,
  "max_san_fetch": 500
}
```

The collector runs certutil, fetches cert blobs for SAN extraction, and pushes results to the API ingest endpoint.

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

- JWT authentication with bcrypt password hashing
- Four RBAC roles: admin, operator, viewer, auditor
- Enclave-scoped access on every endpoint
- Connector credentials in DB config (encrypt at rest in production — TODO)
- Audit logging for administrative actions
- No hardcoded connector instances — all configuration via UI
- Change SECRET_KEY in production

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
│   │   └── util/          # Cron, hashing, logging utilities
│   └── tests/
├── worker/                 # Background job scheduler
│   └── src/nmia_worker/
│       ├── connectors/    # AD and ADCS collectors
│       └── pipeline/      # Normalize, correlate, risk
├── ui/                     # React + TypeScript frontend
│   └── src/
│       ├── auth/          # Login, auth context
│       ├── layout/        # App shell, navigation
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
