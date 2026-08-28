#!/usr/bin/env bash
set -euo pipefail
# Render provides postgres:// ; SQLAlchemy async needs postgresql+asyncpg://
if [[ -n "${DATABASE_URL:-}" && "$DATABASE_URL" == postgres://* ]]; then
  export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}"
fi
if [[ -n "${DATABASE_URL_SYNC:-}" && "$DATABASE_URL_SYNC" == postgres://* ]]; then
  export DATABASE_URL_SYNC="postgresql://${DATABASE_URL_SYNC#postgres://}"
elif [[ -n "${DATABASE_URL:-}" && -z "${DATABASE_URL_SYNC:-}" ]]; then
  export DATABASE_URL_SYNC="${DATABASE_URL/postgresql+asyncpg:\/\//postgresql:\/\/}"
fi
alembic upgrade head
python scripts/seed.py || true
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
