"""Seed authentication tables into mcdr_cx.db.

Adds roles and users tables (for ORM-based auth) alongside the existing
cx_users table. Maps test user IDs to match cx_users IDs so that
agent1 (user_id=1) sees cases assigned to agent_id=1 in the CX data.
"""

import sqlite3
import bcrypt


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

DB_PATH = "mcdr_mock/mcdr_cx.db"

ROLES = [
    (1, "admin", "Full system administrator"),
    (2, "supervisor", "Team lead / supervisor"),
    (3, "agent", "Front-line CX agent"),
    (4, "qa_analyst", "Quality assurance evaluator"),
]

TEST_USERS = [
    {"username": "agent1",      "password": "agent123", "role_id": 3},
    {"username": "agent2",      "password": "agent123", "role_id": 3},
    {"username": "supervisor1", "password": "super123", "role_id": 2},
    {"username": "qa1",         "password": "qa1234",   "role_id": 4},
    {"username": "admin1",      "password": "admin123", "role_id": 1},
]

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.executescript("""
    DROP TABLE IF EXISTS roles;
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS permissions;
    DROP TABLE IF EXISTS role_permissions;

    CREATE TABLE roles (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        field_mask_config TEXT
    );

    CREATE TABLE permissions (
        id INTEGER PRIMARY KEY,
        resource TEXT NOT NULL,
        action TEXT NOT NULL
    );

    CREATE TABLE role_permissions (
        role_id INTEGER,
        permission_id INTEGER,
        PRIMARY KEY (role_id, permission_id)
    );

    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT,
        hashed_password TEXT,
        full_name TEXT,
        tier TEXT DEFAULT 'tier1',
        is_active INTEGER DEFAULT 1,
        role_id INTEGER REFERENCES roles(id),
        created_at TEXT
    );
""")

for role in ROLES:
    c.execute("INSERT INTO roles VALUES (?, ?, ?, NULL)", role)

role_map = {"agent": 3, "supervisor": 2, "qa_analyst": 4, "admin": 1}

cx_users = c.execute("SELECT * FROM cx_users ORDER BY user_id").fetchall()
print(f"Found {len(cx_users)} CX users")

passwords_set = {}
for tu in TEST_USERS:
    passwords_set[tu["username"]] = hash_pw(tu["password"])

for row in cx_users:
    user_id, username, full_name, email, role, tier, is_active, created_at = row
    hashed = passwords_set.get(username)
    rid = role_map.get(role, 3)

    c.execute(
        "INSERT INTO users (id, username, email, hashed_password, full_name, tier, is_active, role_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, username, email, hashed, full_name, tier, is_active, rid, created_at),
    )

conn.commit()

print(f"""
Seeded auth tables into {DB_PATH}
─────────────────────────────────
  Roles:  {len(ROLES)}
  Users:  {len(cx_users)} (from cx_users, {len(passwords_set)} with passwords)

Test logins:
  agent1      / agent123     (user_id=1,  role=agent)
  agent2      / agent123     (user_id=2,  role=agent)
  supervisor1 / super123     (user_id=61, role=supervisor)
  qa1         / qa1234       (user_id=73, role=qa_analyst)
  admin1      / admin123     (user_id=81, role=admin)
""")

conn.close()
