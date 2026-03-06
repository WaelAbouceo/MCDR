#!/bin/sh
set -e

DB_DIR="/app/mcdr_mock"

if [ ! -f "$DB_DIR/mcdr_core.db" ]; then
    echo "==> Generating mock databases (first run)..."
    cd "$DB_DIR"
    python generate_db.py
    python generate_cx_data.py
    cd /app
    python seed_poc.py
    echo "==> Mock data ready."
else
    echo "==> Mock databases already exist, skipping generation."
fi

echo "==> Starting MCDR CX Platform on :8100 ..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8100
