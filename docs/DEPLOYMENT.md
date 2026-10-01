# Deployment Guide

## Prerequisites

- Linux VM (Ubuntu 22.04+ recommended)
- Docker and Docker Compose v2
- Domain with DNS pointing to VM
- Caddy or Nginx for TLS termination

## Local Development

```bash
cp .env.example .env
uv sync --frozen --extra dev
uv run alembic upgrade head
uv run python -m services.api.seed
npm ci --prefix apps/web
make dev
```

Open `http://localhost:3005`. Demo credentials are in `.runtime/demo-credentials.json`.

## Docker Compose (Local)

```bash
docker compose -f infra/compose.local.yml up --build
```

## Production Deployment

### 1. Prepare Environment

```bash
cp infra/production.env.example .env.production
# Edit .env.production with real secrets, domain, database URL
python infra/generate_secrets.py >> .env.production
```

### 2. Build and Deploy

```bash
docker compose -f infra/compose.production.yml --env-file .env.production up -d --build
```

### 3. Initialize Database

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m services.api.seed --content-only
docker compose exec api python scripts/create_user.py --role educator
```

### 4. TLS with Caddy

Configure Caddy to proxy `localhost:3000` (web) and `localhost:8000` (API) behind HTTPS.

### 5. Smoke Test

```bash
docker compose exec api python infra/smoke.py
```

## Security Checklist

- [ ] `COOKIE_SECURE=true`
- [ ] `ALLOW_DEMO=false`
- [ ] `ENVIRONMENT=production`
- [ ] `APP_ORIGIN=https://your-domain.com`
- [ ] Strong `MCP_SERVICE_SECRET` (≥32 characters)
- [ ] PostgreSQL instead of SQLite
- [ ] HTTPS enforced via reverse proxy
