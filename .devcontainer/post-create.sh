#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Building and starting demo stack (docker compose)…"
docker compose up -d --build
echo "Waiting for API…"
for i in $(seq 1 60); do
  if curl -sf http://localhost:8000/docs >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
docker compose exec -T api alembic upgrade head || true
docker compose exec -T api python scripts/seed.py || true
echo "Demo stack ready — open forwarded port 5173 (App)."
