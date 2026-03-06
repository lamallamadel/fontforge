# AIFont Database — Backup and Restore Guide

This guide covers backup and restore procedures for the AIFont PostgreSQL
database.  Follow these steps in all environments (development, staging,
production).

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| `pg_dump` | ≥ 15 | Logical backup |
| `pg_restore` | ≥ 15 | Restore from custom-format dumps |
| `psql` | ≥ 15 | Restore from plain-SQL dumps |
| `pg_basebackup` | ≥ 15 | Physical / streaming backup |

Ensure the PostgreSQL client tools match the server version:

```bash
pg_dump --version
# pg_dump (PostgreSQL) 15.x
```

---

## Environment Variables

```bash
export PGHOST=localhost
export PGPORT=5432
export PGUSER=aifont
export PGPASSWORD=<secret>          # or use ~/.pgpass
export PGDATABASE=aifont
```

---

## Logical Backup (recommended)

### Full backup — custom format

The **custom format** (`-Fc`) is the most flexible option.  It is
compressed, supports parallel restore, and allows object-level selection.

```bash
pg_dump \
  --format=custom \
  --compress=9 \
  --file=aifont_$(date +%Y%m%d_%H%M%S).dump \
  "$PGDATABASE"
```

### Full backup — plain SQL

Useful for human-readable inspection or piping directly into `psql`.

```bash
pg_dump \
  --format=plain \
  --file=aifont_$(date +%Y%m%d_%H%M%S).sql \
  "$PGDATABASE"
```

### Schema-only backup

```bash
pg_dump \
  --schema-only \
  --format=plain \
  --file=aifont_schema_$(date +%Y%m%d).sql \
  "$PGDATABASE"
```

### Data-only backup

```bash
pg_dump \
  --data-only \
  --format=custom \
  --file=aifont_data_$(date +%Y%m%d_%H%M%S).dump \
  "$PGDATABASE"
```

---

## Restore

### Restore from custom-format dump

```bash
# Drop and recreate the target database first (production: use with caution)
dropdb aifont_restore_target
createdb aifont_restore_target

pg_restore \
  --dbname=aifont_restore_target \
  --jobs=4 \                    # parallel restore workers
  --verbose \
  aifont_20250101_120000.dump
```

### Restore from plain SQL

```bash
psql \
  --dbname=aifont_restore_target \
  --file=aifont_20250101_120000.sql
```

### Restore a single table

```bash
pg_restore \
  --dbname=aifont \
  --table=glyphs \
  aifont_20250101_120000.dump
```

---

## Incremental / Continuous Archiving (WAL)

For production setups that require point-in-time recovery (PITR):

1. Enable WAL archiving in `postgresql.conf`:

   ```ini
   wal_level = replica
   archive_mode = on
   archive_command = 'cp %p /mnt/wal_archive/%f'
   ```

2. Take a base backup:

   ```bash
   pg_basebackup \
     --pgdata=/mnt/base_backup \
     --format=tar \
     --gzip \
     --progress \
     --verbose
   ```

3. To restore to a specific point in time, set `recovery_target_time` in
   `recovery.conf` (PostgreSQL ≤ 11) or `postgresql.conf` (PostgreSQL ≥ 12)
   and place `recovery.signal` in the data directory.

---

## Automated Backup Script

Save as `scripts/backup_db.sh` and schedule with `cron` or a CI/CD job.

```bash
#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# AIFont database backup script
# ---------------------------------------------------------------------------
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/aifont}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${BACKUP_DIR}/aifont_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup → ${DUMP_FILE}"
pg_dump \
  --format=custom \
  --compress=9 \
  --file="$DUMP_FILE" \
  "${PGDATABASE:-aifont}"

echo "[$(date -Iseconds)] Backup complete: $(du -sh "$DUMP_FILE" | cut -f1)"

# Remove backups older than RETENTION_DAYS
find "$BACKUP_DIR" -name "aifont_*.dump" -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -Iseconds)] Pruned backups older than ${RETENTION_DAYS} days."
```

Example `cron` entry (daily at 02:00):

```
0 2 * * * PGPASSWORD=secret /opt/aifont/scripts/backup_db.sh >> /var/log/aifont_backup.log 2>&1
```

---

## Verify a Backup

Always verify a backup before relying on it:

```bash
# Check the table of contents
pg_restore --list aifont_20250101_120000.dump | head -40

# Restore into a temporary database and run a quick sanity check
createdb aifont_verify_tmp
pg_restore --dbname=aifont_verify_tmp aifont_20250101_120000.dump

psql --dbname=aifont_verify_tmp --command="
  SELECT
    (SELECT COUNT(*) FROM users)        AS users,
    (SELECT COUNT(*) FROM font_projects) AS projects,
    (SELECT COUNT(*) FROM fonts)        AS fonts,
    (SELECT COUNT(*) FROM glyphs)       AS glyphs;
"

dropdb aifont_verify_tmp
```

---

## Docker / Container Environments

When PostgreSQL is running inside Docker:

```bash
# Backup
docker exec -i aifont_db \
  pg_dump -U aifont -Fc aifont \
  > aifont_$(date +%Y%m%d_%H%M%S).dump

# Restore
docker exec -i aifont_db \
  pg_restore -U aifont -d aifont \
  < aifont_20250101_120000.dump
```

---

## Alembic Migrations After Restore

After restoring a backup, ensure the database schema is up-to-date:

```bash
# Check current revision
alembic current

# Apply any pending migrations
alembic upgrade head
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `pg_restore: error: input file does not appear to be a valid archive` | Wrong format flag | Match `-F` to how the dump was created |
| `ERROR: relation already exists` | Restoring into a non-empty database | Use `--clean` or restore into a fresh database |
| `ERROR: type "project_status_enum" already exists` | Enum type collision | Add `--if-exists` or drop types manually |
| Slow restore | Single-threaded | Add `--jobs=N` (custom format only) |
