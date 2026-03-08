#!/bin/bash
# Creates all application databases and grants the MYSQL_USER full access.
# Runs as root via docker-entrypoint-initdb.d before the .sql scripts.

set -e

DBUSER="${MYSQL_USER:-mcdr}"

mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS mcdr_core     CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE DATABASE IF NOT EXISTS mcdr_mobile   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE DATABASE IF NOT EXISTS mcdr_cx       CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE DATABASE IF NOT EXISTS mcdr_customer CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

    GRANT ALL PRIVILEGES ON mcdr_core.*     TO '${DBUSER}'@'%';
    GRANT ALL PRIVILEGES ON mcdr_mobile.*   TO '${DBUSER}'@'%';
    GRANT ALL PRIVILEGES ON mcdr_cx.*       TO '${DBUSER}'@'%';
    GRANT ALL PRIVILEGES ON mcdr_customer.* TO '${DBUSER}'@'%';
    FLUSH PRIVILEGES;
EOSQL

echo "Databases created and privileges granted to '${DBUSER}'."
