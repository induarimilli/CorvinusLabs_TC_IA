#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d
echo "Corvinus Labs: App → port 5173 · API → port 8000"
