#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${1:?Usage: infra/backup.sh ABSOLUTE_BACKUP_DIRECTORY}"
[[ "$1" = /* ]] || { printf 'Use an absolute backup directory.\n' >&2; exit 2; }
backup_dir="$1/$(date -u +%Y%m%dT%H%M%SZ)"
umask 077
mkdir -p "$backup_dir"
compose=(docker compose --env-file .env.production -f infra/compose.production.yml)
# Quiesce application writes before pairing database and private asset snapshots.
"${compose[@]}" stop api worker mcp
trap '"${compose[@]}" start api worker mcp >/dev/null' EXIT
"${compose[@]}" exec -T postgres pg_dump -U otcaselab -d otcaselab -Fc > "$backup_dir/database.dump"
"${compose[@]}" run --rm --no-deps -T api tar -C /app/.runtime -cf - uploads > "$backup_dir/uploads.tar"
(cd "$backup_dir" && sha256sum database.dump uploads.tar > SHA256SUMS)
if git rev-parse --verify HEAD > "$backup_dir/source-commit.txt" 2>/dev/null; then :; else printf "uncommitted-working-tree\n" > "$backup_dir/source-commit.txt"; fi
printf 'Backup written to %s; encrypt and copy off-host using your approved storage.\n' "$backup_dir"
