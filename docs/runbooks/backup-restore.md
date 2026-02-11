# Backup and Restore Runbook

This runbook covers procedures for backing up and restoring NMIA data and
configuration. All critical state lives in PostgreSQL; there are no significant
file-based stores outside the database.

---

## What to Back Up

| Item | Location | Method | Priority |
|------|----------|--------|----------|
| PostgreSQL database | Docker volume `pgdata` | `pg_dump` | **Critical** |
| Docker Compose config | `docker-compose.yml`, `.env` | File copy | High |
| Connector configurations | In database (`connectors` table) | Included in DB backup | Critical |
| User accounts and roles | In database | Included in DB backup | Critical |
| Application source code | Git repository | Git remote | Medium |

**Not backed up (by design):**

- Container images (rebuilt from Dockerfiles)
- Node modules, Python virtualenvs (rebuilt from lock files)
- Logs (ephemeral; configure external log aggregation for production)

---

## Database Backup

### Full Backup (Recommended)

Use `pg_dump` in custom format for maximum flexibility on restore.

```bash
# From the host, using the running db container
docker compose exec db pg_dump \
  -U nmia \
  -d nmia \
  -Fc \
  --file=/tmp/nmia_backup.dump

# Copy the dump file out of the container
docker compose cp db:/tmp/nmia_backup.dump ./backups/nmia_backup_$(date +%Y%m%d_%H%M%S).dump
```

### SQL Text Backup

Plain SQL format is human-readable and useful for inspection or partial restores.

```bash
docker compose exec db pg_dump \
  -U nmia \
  -d nmia \
  --format=plain \
  --file=/tmp/nmia_backup.sql

docker compose cp db:/tmp/nmia_backup.sql ./backups/nmia_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Schema-Only Backup

Useful for documenting the current schema without data.

```bash
docker compose exec db pg_dump \
  -U nmia \
  -d nmia \
  --schema-only \
  --file=/tmp/nmia_schema.sql

docker compose cp db:/tmp/nmia_schema.sql ./backups/nmia_schema_$(date +%Y%m%d_%H%M%S).sql
```

### Automated Backup Script

Create a cron job on the Docker host for scheduled backups:

```bash
#!/bin/bash
# /opt/nmia/backup.sh
set -euo pipefail

BACKUP_DIR="/opt/nmia/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Dump the database
docker compose -f /opt/nmia/docker-compose.yml exec -T db pg_dump \
  -U nmia \
  -d nmia \
  -Fc \
  > "$BACKUP_DIR/nmia_backup_${TIMESTAMP}.dump"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "nmia_backup_*.dump" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: nmia_backup_${TIMESTAMP}.dump"
```

Cron entry (daily at 02:00):

```
0 2 * * * /opt/nmia/backup.sh >> /var/log/nmia-backup.log 2>&1
```

---

## Database Restore

### Restore from Custom Format Dump

```bash
# Stop the API and worker to prevent writes during restore
docker compose stop api worker collector

# Copy the dump file into the container
docker compose cp ./backups/nmia_backup_20250201_020000.dump db:/tmp/nmia_restore.dump

# Drop and recreate the database
docker compose exec db psql -U nmia -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nmia' AND pid <> pg_backend_pid();"
docker compose exec db dropdb -U nmia nmia
docker compose exec db createdb -U nmia nmia

# Restore
docker compose exec db pg_restore \
  -U nmia \
  -d nmia \
  --no-owner \
  --no-privileges \
  /tmp/nmia_restore.dump

# Restart services
docker compose start api worker collector
```

### Restore from SQL Text Dump

```bash
# Stop the API and worker
docker compose stop api worker collector

# Copy the SQL file into the container
docker compose cp ./backups/nmia_backup_20250201_020000.sql db:/tmp/nmia_restore.sql

# Drop and recreate the database
docker compose exec db psql -U nmia -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nmia' AND pid <> pg_backend_pid();"
docker compose exec db dropdb -U nmia nmia
docker compose exec db createdb -U nmia nmia

# Restore
docker compose exec db psql -U nmia -d nmia -f /tmp/nmia_restore.sql

# Restart services
docker compose start api worker collector
```

### Restore to a Different Database (for Testing)

```bash
# Create a test database
docker compose exec db createdb -U nmia nmia_restore_test

# Restore into the test database
docker compose exec db pg_restore \
  -U nmia \
  -d nmia_restore_test \
  --no-owner \
  --no-privileges \
  /tmp/nmia_restore.dump

# Connect and verify
docker compose exec db psql -U nmia -d nmia_restore_test -c "SELECT count(*) FROM identities;"

# Clean up when done
docker compose exec db dropdb -U nmia nmia_restore_test
```

---

## Docker Volume Backup

If you need to back up the raw PostgreSQL data volume (e.g., for snapshotting):

```bash
# Stop the database
docker compose stop db

# Back up the volume
docker run --rm \
  -v nmai_pgdata:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/pgdata_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# Restart the database
docker compose start db
```

### Restore Docker Volume

```bash
# Stop the database
docker compose stop db

# Remove the existing volume
docker volume rm nmai_pgdata

# Create a new volume and restore
docker volume create nmai_pgdata
docker run --rm \
  -v nmai_pgdata:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/pgdata_20250201_020000.tar.gz -C /data

# Restart the database
docker compose start db
```

---

## Configuration Backup

Connector configurations (LDAP URLs, bind DNs, search bases, cron schedules)
are stored in the database and are included in database backups. There is no
separate configuration file to back up beyond what is in the repository.

To export connector configurations for documentation or migration:

```bash
docker compose exec db psql -U nmia -d nmia -c \
  "SELECT id, name, connector_type_code, enclave_id, cron_expression, is_enabled, created_at FROM connectors;" \
  --csv > ./backups/connectors_export.csv
```

**Warning:** Do not export the `config` column in plain text, as it may contain
sensitive credentials (bind passwords). If you must export it, ensure the export
is encrypted or stored securely.

---

## Disaster Recovery Checklist

Use this checklist when recovering from a complete environment loss.

### Prerequisites

- [ ] Docker and Docker Compose installed on the recovery host
- [ ] Access to the NMIA Git repository
- [ ] Access to the most recent database backup file
- [ ] Knowledge of the `SECRET_KEY` used in the original environment
- [ ] Knowledge of any custom `.env` overrides

### Recovery Steps

1. **Clone the repository**

   ```bash
   git clone <repo-url> /opt/nmia
   cd /opt/nmia
   ```

2. **Restore environment configuration**

   ```bash
   # Create .env with production values
   cat > .env <<EOF
   DATABASE_URL=postgresql://nmia:nmia@db:5432/nmia
   SECRET_KEY=<original-secret-key>
   EOF
   ```

   **Critical:** The `SECRET_KEY` must match the original. If it is lost, all
   existing JWT tokens will be invalid and users must re-authenticate. If user
   passwords were hashed with a different mechanism that depends on the secret,
   they may need to be reset.

3. **Start the database**

   ```bash
   docker compose up -d db
   # Wait for health check to pass
   docker compose ps
   ```

4. **Restore the database backup**

   ```bash
   docker compose cp /path/to/nmia_backup.dump db:/tmp/nmia_restore.dump
   docker compose exec db dropdb -U nmia nmia
   docker compose exec db createdb -U nmia nmia
   docker compose exec db pg_restore \
     -U nmia -d nmia --no-owner --no-privileges \
     /tmp/nmia_restore.dump
   ```

5. **Start remaining services**

   ```bash
   docker compose up -d
   ```

6. **Verify recovery**

   - [ ] API responds at http://host:8000/docs
   - [ ] UI loads at http://host:5173
   - [ ] Admin can log in with existing credentials
   - [ ] Enclaves and connectors are visible
   - [ ] Identity counts match pre-disaster numbers
   - [ ] Worker is running (check `docker compose logs worker`)
   - [ ] Run a test connector scan to verify connectivity

7. **Post-recovery actions**

   - [ ] Rotate the `SECRET_KEY` if there is any suspicion of compromise
   - [ ] Rotate connector credentials (AD bind passwords) if the backup was stored insecurely
   - [ ] Verify backup automation is re-enabled on the new host
   - [ ] Update DNS or load balancer to point to the new host
   - [ ] Notify users of any credential resets required
