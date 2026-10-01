#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${1:?Usage: infra/restore.sh ABSOLUTE_SNAPSHOT_DIRECTORY DISPOSABLE_COMPOSE_PROJECT}"
: "${2:?Use a new disposable Compose project name for the restore rehearsal}"
[[ "$1" = /* ]] || { printf 'Use an absolute snapshot directory.\n' >&2; exit 2; }
[[ "$2" == restore-* ]] || { printf 'Restore project name must begin restore-.\n' >&2; exit 2; }
(cd "$1" && sha256sum -c SHA256SUMS)
compose=(docker compose -p "$2" --env-file .env.production -f infra/compose.production.yml)
"${compose[@]}" up -d postgres redis
"${compose[@]}" exec -T postgres pg_restore -U otcaselab -d otcaselab --clean --if-exists < "$1/database.dump"
"${compose[@]}" run --rm --no-deps -T api tar -C /app/.runtime -xf - < "$1/uploads.tar"
printf 'Snapshot restored into disposable project %s. Start internal services only and perform ownership/persistence smoke tests.\n' "$2"
