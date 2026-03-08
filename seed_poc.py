"""Seed authentication tables into mcdr_cx MySQL database.

Adds roles and users tables (for ORM-based auth) alongside the existing
cx_users table. Maps test user IDs to match cx_users IDs so that
agent1 (user_id=1) sees cases assigned to agent_id=1 in the CX data.
"""

import os

import bcrypt
import pymysql
import pymysql.cursors


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "mcdr")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "mcdr_pass")
MYSQL_DB = os.environ.get("MYSQL_DB", "mcdr_cx")

ROLES = [
    (1, "admin", "Full system administrator"),
    (2, "supervisor", "Operations supervisor"),
    (3, "agent", "Front-line T1 agent"),
    (4, "qa_analyst", "Quality assurance evaluator"),
    (5, "team_lead", "Team lead — manages a squad of agents"),
    (6, "senior_agent", "Senior T2 agent — handles escalations"),
]

TEST_USERS = [
    {"username": "agent1",      "password": "agent123", "role_id": 6},
    {"username": "agent2",      "password": "agent123", "role_id": 6},
    {"username": "agent11",     "password": "agent123", "role_id": 3},
    {"username": "agent12",     "password": "agent123", "role_id": 3},
    {"username": "supervisor1", "password": "super123", "role_id": 2},
    {"username": "tl1",         "password": "lead123",  "role_id": 5},
    {"username": "qa1",         "password": "qa1234",   "role_id": 4},
    {"username": "admin1",      "password": "admin123", "role_id": 1},
]

conn = pymysql.connect(
    host=MYSQL_HOST, port=MYSQL_PORT,
    user=MYSQL_USER, password=MYSQL_PASSWORD,
    database=MYSQL_DB, charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)
c = conn.cursor()

c.execute("DELETE FROM users")
c.execute("DELETE FROM role_permissions")
c.execute("DELETE FROM permissions")
c.execute("DELETE FROM roles")

for role in ROLES:
    c.execute("INSERT INTO roles (id, name, description) VALUES (%s, %s, %s)", role)

role_map = {"agent": 3, "senior_agent": 6, "supervisor": 2, "qa_analyst": 4, "admin": 1, "team_lead": 5}

c.execute("SELECT * FROM cx_users ORDER BY user_id")
cx_users = c.fetchall()
print(f"Found {len(cx_users)} CX users")

passwords_set = {}
for tu in TEST_USERS:
    passwords_set[tu["username"]] = hash_pw(tu["password"])

user_rows = []
for row in cx_users:
    user_id = row["user_id"]
    username = row["username"]
    full_name = row["full_name"]
    email = row["email"]
    role = row["role"]
    tier = row["tier"]
    is_active = row["is_active"]
    created_at = row["created_at"]

    hashed = passwords_set.get(username)
    rid = role_map.get(role, 3)

    unique_email = email or f"{username}@gochat247.com"
    if "@" in (email or ""):
        local, domain = unique_email.rsplit("@", 1)
        unique_email = f"{local}+{user_id}@{domain}"

    user_rows.append((
        user_id, username, unique_email,
        hashed or "", full_name, tier, is_active, rid, created_at,
    ))

if user_rows:
    c.executemany(
        "INSERT INTO users (id, username, email, hashed_password, full_name, tier, is_active, role_id, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        user_rows,
    )

conn.commit()

print(f"""
Seeded auth tables into {MYSQL_DB}@{MYSQL_HOST}
─────────────────────────────────
  Roles:  {len(ROLES)}
  Users:  {len(cx_users)} (from cx_users, {len(passwords_set)} with passwords)

Test logins:
  agent1      / agent123     (user_id=1,  role=senior_agent, tier2)
  agent2      / agent123     (user_id=2,  role=senior_agent, tier2)
  agent11     / agent123     (user_id=11, role=agent, tier1)
  agent12     / agent123     (user_id=12, role=agent, tier1)
  tl1         / lead123      (user_id=61, role=team_lead)
  supervisor1 / super123     (user_id=66, role=supervisor)
  qa1         / qa1234       (user_id=78, role=qa_analyst)
  admin1      / admin123     (user_id=86, role=admin)
""")

conn.close()
