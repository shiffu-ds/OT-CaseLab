# Runbook

Operational commands for OTCaseLab deployment.

## Database Operations

### Run Migrations

```bash
uv run alembic upgrade head
# or in Docker:
docker compose exec api alembic upgrade head
```

### Backup (SQLite)

```bash
sqlite3 .runtime/otcaselab.db ".backup '.runtime/backups/otcaselab-$(date +%Y%m%d-%H%M%S).db'"
```

### Backup (PostgreSQL)

```bash
pg_dump "$DATABASE_URL" -Fc -f "backup-$(date +%Y%m%d-%H%M%S).dump"
```

### Restore (SQLite)

```bash
# Stop the API first
cp .runtime/backups/<backup-file>.db .runtime/otcaselab.db
# Restart the API
```

### Restore (PostgreSQL)

```bash
pg_restore --clean --if-exists -d "$DATABASE_URL" <backup-file>.dump
```

## Rollback

### Alembic Downgrade

```bash
uv run alembic downgrade -1   # One step back
uv run alembic history        # View migration history
```

### Application Rollback

```bash
docker compose -f infra/compose.production.yml pull <previous-tag>
docker compose -f infra/compose.production.yml up -d
```

## Restart Commands

### Development

```bash
make dev  # Restarts both API and web
```

### Production

```bash
docker compose -f infra/compose.production.yml restart api
docker compose -f infra/compose.production.yml restart web
docker compose -f infra/compose.production.yml restart worker  # if using Celery
```

## User Management

### Create Educator Account

```bash
uv run python scripts/create_user.py --role educator
# or in Docker:
docker compose exec -it api python scripts/create_user.py --role educator
```

### Promote User to Educator

Via the admin panel in the web UI, or:

```bash
# Use the admin API endpoint
curl -X POST http://localhost:8000/api/v1/admin/users/<user_id>/role \
  -H "Content-Type: application/json" \
  -d '{"role": "educator"}'
```

## Health Checks

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `broken symbolic link` for `.venv/bin/python` | Re-run `uv sync --frozen --extra dev` |
| `Database is locked` | Stop concurrent writers; check WAL mode |
| `401 Unauthorized` on every request | Verify `COOKIE_SECURE` matches protocol (false for HTTP) |
| Tests hang on torch import | Patience — first import compiles; or use `--extra dev` without `--extra neural` |
