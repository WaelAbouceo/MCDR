#!/bin/sh
set -e

MYSQL_HOST="${MYSQL_HOST:-mysql}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-mcdr}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-mcdr_pass}"

# Give MySQL a few extra seconds after "healthy" before we start pinging
echo "==> Giving MySQL 10s to settle..."
sleep 10

echo "==> Waiting for MySQL at ${MYSQL_HOST}:${MYSQL_PORT} (up to 120s)..."
MAX_ATTEMPTS=120
attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
    if python -c "
import pymysql
import sys
try:
    conn = pymysql.connect(
        host='${MYSQL_HOST}',
        port=${MYSQL_PORT},
        user='${MYSQL_USER}',
        password='${MYSQL_PASSWORD}',
        connect_timeout=10
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
        echo "==> MySQL is ready (attempt $attempt)."
        break
    fi
    if [ "$attempt" -eq "$MAX_ATTEMPTS" ]; then
        echo "==> ERROR: MySQL not ready after ${MAX_ATTEMPTS} seconds, aborting."
        echo "==> Last attempt: running Python check with errors visible:"
        python -c "
import pymysql
try:
    pymysql.connect(host='${MYSQL_HOST}', port=${MYSQL_PORT}, user='${MYSQL_USER}', password='${MYSQL_PASSWORD}', connect_timeout=5)
except Exception as e:
    print('Error:', e)
" || true
        exit 1
    fi
    printf "    attempt %d/%d...\r" "$attempt" "$MAX_ATTEMPTS"
    attempt=$((attempt + 1))
    sleep 1
done

# Check if mock data already seeded by looking for cx_users rows
SEEDED=$(python -c "
import pymysql
try:
    conn = pymysql.connect(host='${MYSQL_HOST}', port=${MYSQL_PORT}, user='${MYSQL_USER}', password='${MYSQL_PASSWORD}', database='mcdr_cx', connect_timeout=10)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM cx_users')
    print(cur.fetchone()[0])
    conn.close()
except Exception as e:
    print('0')
" 2>/dev/null || echo "0")

if [ "$SEEDED" = "0" ] || [ "$SEEDED" = "" ]; then
    echo "==> Generating mock data (first run)..."
    cd /app/mcdr_mock
    python generate_db.py
    python generate_cx_data.py
    cd /app
    python seed_poc.py
    echo "==> Mock data ready."
else
    echo "==> Mock data already present ($SEEDED cx_users), skipping generation."
fi

echo "==> Starting MCDR CX Platform on :8100 ..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8100
