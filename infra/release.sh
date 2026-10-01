#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${1:?Usage: infra/release.sh RELEASE_TAG; configure .env.production first}"
export RELEASE_TAG="$1"
compose=(docker compose --env-file .env.production -f infra/compose.production.yml)
"${compose[@]}" config --quiet
"${compose[@]}" build api web
"${compose[@]}" up -d postgres redis
"${compose[@]}" run --rm migrate
"${compose[@]}" up -d api mcp worker web proxy
"${compose[@]}" ps
printf 'Release stack started. Complete the authenticated staging smoke and record image digests before audience release.\n'
