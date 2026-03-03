import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("ar_EG")

INVESTOR_COUNT = 50000
SECURITY_COUNT = 250

def random_date(days_back=900):
    return datetime.now() - timedelta(days=random.randint(0, days_back))

# =========================
# CORE REGISTRY DB
# =========================

core_conn = sqlite3.connect("mcdr_core.db")
core = core_conn.cursor()

core.executescript("""
DROP TABLE IF EXISTS investors;
DROP TABLE IF EXISTS securities;
DROP TABLE IF EXISTS holdings;

CREATE TABLE investors (
    investor_id INTEGER PRIMARY KEY,
    investor_code TEXT UNIQUE,
    full_name TEXT,
    national_id TEXT,
    investor_type TEXT,
    account_status TEXT,
    created_at TEXT
);

CREATE TABLE securities (
    security_id INTEGER PRIMARY KEY,
    isin TEXT UNIQUE,
    ticker TEXT,
    company_name TEXT,
    sector TEXT
);

CREATE TABLE holdings (
    holding_id INTEGER PRIMARY KEY,
    investor_id INTEGER,
    security_id INTEGER,
    quantity INTEGER,
    avg_price REAL,
    last_updated TEXT
);
""")

# Insert Securities
sectors = ["Banking","Telecom","Energy","Industrials","Real Estate","Consumer"]
for i in range(1, SECURITY_COUNT + 1):
    core.execute("""
        INSERT INTO securities VALUES (?, ?, ?, ?, ?)
    """, (
        i,
        f"EGS{random.randint(1000000,9999999)}C01{i%10}",
        f"TK{i:03}",
        fake.company(),
        random.choice(sectors)
    ))

# Insert Investors
for i in range(1, INVESTOR_COUNT + 1):
    investor_type = "Institutional" if random.random() < 0.02 else "Retail"
    name = fake.company() if investor_type == "Institutional" else fake.name()

    core.execute("""
        INSERT INTO investors VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        i,
        f"INV-{i:06}",
        name,
        str(random.randint(20000000000000,39999999999999)) if investor_type == "Retail" else None,
        investor_type,
        random.choices(["Active","Dormant","Suspended"], weights=[85,10,5])[0],
        random_date().strftime("%Y-%m-%d")
    ))

# Insert Holdings
holding_id = 1
for investor_id in range(1, INVESTOR_COUNT + 1):
    for _ in range(random.randint(3, 12)):
        core.execute("""
            INSERT INTO holdings VALUES (?, ?, ?, ?, ?, ?)
        """, (
            holding_id,
            investor_id,
            random.randint(1, SECURITY_COUNT),
            random.randint(10, 5000),
            round(random.uniform(5, 250), 2),
            random_date().strftime("%Y-%m-%d")
        ))
        holding_id += 1

core_conn.commit()
core_conn.close()

# =========================
# MOBILE APP DB
# =========================

mobile_conn = sqlite3.connect("mcdr_mobile.db")
mobile = mobile_conn.cursor()

mobile.executescript("""
DROP TABLE IF EXISTS app_users;

CREATE TABLE app_users (
    app_user_id INTEGER PRIMARY KEY,
    investor_id INTEGER,
    username TEXT UNIQUE,
    mobile TEXT,
    email TEXT,
    password_hash TEXT,
    otp_verified INTEGER,
    status TEXT,
    last_login TEXT,
    created_at TEXT
);
""")

app_user_id = 1

for investor_id in range(1, INVESTOR_COUNT + 1):
    if random.random() < 0.6:
        mobile.execute("""
            INSERT INTO app_users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_user_id,
            investor_id,
            f"user{investor_id}",
            "+20" + str(random.randint(1000000000,1999999999)),
            fake.email(),
            "$2b$12$mockhashvalue123456",
            1 if random.random() < 0.9 else 0,
            random.choices(["Active","Locked","Disabled"], weights=[90,5,5])[0],
            random_date(60).strftime("%Y-%m-%d %H:%M:%S"),
            random_date().strftime("%Y-%m-%d")
        ))
        app_user_id += 1

mobile_conn.commit()
mobile_conn.close()

print("✅ 50K MCDR Mock Databases Generated Successfully.")
