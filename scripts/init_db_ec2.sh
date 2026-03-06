#!/usr/bin/env bash
# Create SQLite databases on EC2 (or any server) so you don't need to copy .db files.
# Run from the MCDR repo root:  ./scripts/init_db_ec2.sh
# Requires: Python 3, pip. Installs faker and bcrypt if missing.

set -e
cd "$(dirname "$0")/.."
DATA_DIR="${1:-data}"
mkdir -p "$DATA_DIR"
echo "Using data dir: $(pwd)/$DATA_DIR"

# Install Python deps (for generate_db, generate_cx_data, seed_poc)
pip3 install --user faker bcrypt 2>/dev/null || true

# 1) Core + Mobile DBs (registry and app users)
echo "Step 1/3: Creating mcdr_core.db and mcdr_mobile.db..."
(cd "$DATA_DIR" && python3 ../mcdr_mock/generate_db.py)

# 2) CX DB (cases, calls, cx_users, etc.) — may take a few minutes
echo "Step 2/3: Creating mcdr_cx.db (this can take 2–5 minutes)..."
(cd "$DATA_DIR" && python3 ../mcdr_mock/generate_cx_data.py)

# 3) Auth tables + test user passwords in mcdr_cx.db
echo "Step 3/3: Seeding auth (roles, users) into mcdr_cx.db..."
abs_cx_db="$(cd "$DATA_DIR" && pwd)/mcdr_cx.db"
MCDR_CX_DB_PATH="$abs_cx_db" python3 seed_poc.py

echo "Done. DBs are in $(pwd)/$DATA_DIR/"
ls -la "$DATA_DIR"/*.db
