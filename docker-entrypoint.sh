#!/bin/sh
set -e

echo "[TrustGuard Startup] Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "[TrustGuard Startup] Starting Uvicorn production server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
