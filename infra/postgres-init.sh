#!/usr/bin/env bash
set -euo pipefail
: "${APP_DB_PASSWORD:?Set APP_DB_PASSWORD}"
psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=app_password="$APP_DB_PASSWORD" <<'SQL'
CREATE ROLE otcase_app WITH LOGIN PASSWORD :'app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT CONNECT, TEMPORARY ON DATABASE otcaselab TO otcase_app;
GRANT USAGE, CREATE ON SCHEMA public TO otcase_app;
SQL
