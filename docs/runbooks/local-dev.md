# Local Development Runbook

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | v2+ | Service orchestration |
| Make | any | Convenience targets |
| Node.js | 20+ | UI development (optional, for running outside Docker) |
| Python | 3.11+ | API/Worker development (optional, for running outside Docker) |

---

## Quick Start

```bash
# Clone the repository
git clone <repo-url> NMAI
cd NMAI

# Start all services
make up

# Run database migrations
make migrate
```

Open the UI at http://localhost:5173 and log in with the default credentials.

---

## Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| API | 8000 | http://localhost:8000 | FastAPI REST API, Swagger docs at `/docs` |
| UI | 5173 | http://localhost:5173 | React + Vite development server |
| Worker | -- | (background) | APScheduler-based connector job runner |
| Collector | 9000 | http://localhost:9000 | Windows ADCS collector (simulated in Docker) |
| PostgreSQL | 5432 | `postgresql://nmia:nmia@localhost:5432/nmia` | Database |

---

## Default Credentials

| Account | Username | Password | Role |
|---------|----------|----------|------|
| Admin | `admin` | `admin` | Global admin |

**Important:** Change these immediately in any non-local environment.

---

## Running Migrations

Migrations are managed by Alembic and run inside the API container.

```bash
# Apply all pending migrations
make migrate

# Create a new migration (after modifying models)
make migration msg="add_new_column_to_identities"

# Check current migration state
docker compose exec api alembic current

# Downgrade one revision
docker compose exec api alembic downgrade -1
```

---

## Running Tests

```bash
# Run all API tests
make test

# Run tests with specific markers or paths
docker compose exec api pytest tests/ -v -k "test_login"

# Run with coverage
docker compose exec api pytest tests/ --cov=nmia --cov-report=term-missing
```

---

## Viewing Logs

```bash
# Follow all service logs
make logs

# Follow logs for a specific service
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f ui
docker compose logs -f collector

# View last 100 lines
docker compose logs --tail=100 api
```

---

## Hot Reload

Both the API and UI support hot reload via Docker volume mounts:

- **API**: The `./api/src` directory is mounted into the container. Uvicorn
  watches for file changes and restarts automatically.
- **UI**: The `./ui/src` directory is mounted into the container. Vite's HMR
  (Hot Module Replacement) picks up changes instantly in the browser.
- **Worker**: The `./worker/src` and `./api/src` directories are mounted. The
  worker process must be restarted manually (or the container restarted) to pick
  up changes.

```bash
# Restart only the worker after code changes
docker compose restart worker
```

---

## Resetting the Database

To completely reset the database (destroy all data and re-create from scratch):

```bash
# Stop everything, remove volumes, rebuild, and re-migrate
make clean && make up && make migrate
```

This will:

1. Stop all containers
2. Remove the PostgreSQL data volume
3. Rebuild all images
4. Start fresh containers
5. Apply all migrations to create the schema

---

## Running Individual Services

You can start individual services when you do not need the full stack:

```bash
# Start just the database
make db

# Start the API (depends on db, will start db too)
make api

# Start the UI (depends on api)
make ui

# Start the worker (depends on db)
make worker

# Rebuild and restart a single service
docker compose up -d --build api
```

---

## Environment Variables

Environment variables are set in `docker-compose.yml` for local development.
For production or custom local overrides, create a `.env` file in the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://nmia:nmia@db:5432/nmia` | PostgreSQL connection string |
| `SECRET_KEY` | `dev-secret-key-change-in-prod` | JWT signing secret |
| `POSTGRES_USER` | `nmia` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `nmia` | PostgreSQL password |
| `POSTGRES_DB` | `nmia` | PostgreSQL database name |
| `NMIA_SERVER_URL` | `http://api:8000` | API URL for collector |
| `PYTHONPATH` | `/app/src` | Python module search path |

### Using a .env File

Create `/home/user/NMAI/.env`:

```bash
DATABASE_URL=postgresql://nmia:nmia@db:5432/nmia
SECRET_KEY=my-custom-dev-secret
```

Docker Compose will automatically load variables from `.env`.

---

## Interactive Shell Access

```bash
# Shell into the API container
make shell

# PostgreSQL interactive shell
make psql

# Shell into any container
docker compose exec worker bash
docker compose exec ui sh
```

---

## Common Development Workflows

### Adding a New API Endpoint

1. Define the Pydantic schema in `api/src/nmia/schemas/`.
2. Add the route in `api/src/nmia/api/`.
3. Implement any service logic in `api/src/nmia/services/`.
4. Add/update the SQLAlchemy model in `api/src/nmia/models/` if needed.
5. Create a migration: `make migration msg="describe_change"`.
6. Apply it: `make migrate`.
7. Write tests in `api/tests/`.
8. Run tests: `make test`.

### Adding a New Connector Type

1. Define the connector type in the `connector_types` seed data.
2. Implement the connector logic in `worker/src/nmia_worker/connectors/`.
3. Add the fingerprint formula for the new identity type.
4. Write tests for the connector.
5. Create a migration if new DB columns are needed.

### Modifying the UI

1. Edit files in `ui/src/`. Vite HMR will update the browser.
2. Add new pages in `ui/src/pages/`.
3. Add new API calls in `ui/src/api/`.
4. The UI proxies API requests to `http://api:8000` in development.

---

## Troubleshooting

### Port Already in Use

```bash
# Find what is using a port
lsof -i :8000

# Kill it or change the port mapping in docker-compose.yml
```

### Database Connection Refused

```bash
# Ensure the db container is healthy
docker compose ps

# Check db logs
docker compose logs db

# The API waits for the db health check, but if you started manually:
docker compose up -d db
# Wait a few seconds, then:
docker compose up -d api
```

### Module Not Found Errors

```bash
# Ensure PYTHONPATH is set correctly in docker-compose.yml
# For the API: PYTHONPATH=/app/src
# For the worker: PYTHONPATH=/app/src:/api-src

# Rebuild the container to pick up new dependencies
docker compose up -d --build api
```

### Stale Docker Images

```bash
# Force rebuild without cache
docker compose build --no-cache api
docker compose up -d api
```
