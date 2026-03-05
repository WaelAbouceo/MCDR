"""Generate the GoChat247 CX Intelligent Layer mock data.

This is the data GoChat247 OWNS — created by agents during call handling.
It links back to the MCDR registry (investors/app_users) via investor_id and ANI.

Generates:
  - CX staff (agents, supervisors, QA analysts, admins)
  - Call records with CTI events
  - Cases/tickets with taxonomy, priority, SLA
  - Case notes (agent + internal)
  - Case history (field change audit trail)
  - Escalations (T1 → T2)
  - SLA breaches
  - QA evaluations with scores
"""

import sqlite3
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker("ar_EG")

# ─── Egyptian Name Pools ─────────────────────────────────────────
# Mix of Arabic-script and Latin-transliterated Egyptian names

_MALE_FIRST_AR = [
    "محمد", "محمد", "أحمد", "أحمد", "محمود", "محمود", "مصطفى",
    "عمرو", "علي", "إبراهيم", "خالد", "عمر",
    "حسن", "حسين", "يوسف", "كريم", "طارق", "نبيل", "سمير", "شريف",
    "رامي", "حسام", "أشرف", "وليد", "عادل", "جمال", "فادي", "ماجد",
    "إيهاب", "وائل", "سامر", "باسم", "تامر", "هشام", "ياسر", "عصام",
    "مروان", "أيمن", "زياد", "سيف", "بلال", "عبدالله", "عبدالرحمن",
    "مجدي", "رمضان", "سعد", "صالح", "سعيد", "كمال", "عماد", "هاني",
    "أسامة", "حاتم", "مينا", "جورج",
]
_FEMALE_FIRST_AR = [
    "إيمان", "إيمان", "منى", "منى", "هبة", "هبة", "آية", "آية",
    "مروة", "سارة", "أسماء", "أميرة",
    "فاطمة", "نور", "هنا", "مريم", "ياسمين", "دينا", "رانيا", "ليلى",
    "أمل", "نهى", "سلمى", "نهلة", "غادة", "سميرة", "ريم", "هالة",
    "داليا", "لمياء", "مها", "نورهان", "شيماء", "عبير", "سحر", "مي",
    "رضوى", "هدى", "نجلاء", "إسراء", "دعاء", "ندى", "رنا", "حنان",
    "منال", "نيفين", "مارينا",
]
_LAST_AR = [
    "محمد", "محمد", "أحمد", "أحمد", "علي", "علي", "حسن", "حسن",
    "محمود", "إبراهيم", "صلاح", "مصطفى", "عادل", "جمال",
    "سعد", "السيد", "سمير", "عمر", "حسين", "كمال", "مجدي", "سالم",
    "صالح", "رمضان", "حمدي", "خالد", "سعيد", "فاروق", "منصور",
    "عبدالرحمن", "ناصر", "سليمان", "فهمي", "عبدالله", "يوسف", "عثمان",
    "المصري", "حلمي", "شاكر", "جابر", "توفيق", "بركات", "حسنين",
    "زكي", "كامل", "رفعت", "بدوي", "خليل", "عبدالعزيز", "عبدالفتاح",
]

_MALE_FIRST_EN = [
    "Mohamed", "Mohamed", "Ahmed", "Ahmed", "Mahmoud", "Mahmoud",
    "Mostafa", "Amr", "Ali", "Ibrahim", "Khaled", "Omar",
    "Hassan", "Hussein", "Youssef", "Karim", "Tarek", "Sherif",
    "Ramy", "Hossam", "Waleed", "Fady", "Wael", "Tamer", "Hesham",
    "Yasser", "Essam", "Marwan", "Ayman", "Ziad", "Seif", "Adel",
    "Gamal", "Samir", "Nabil", "Ashraf", "Magdy", "Saad", "Emad",
    "Hany", "Osama", "Mina",
]
_FEMALE_FIRST_EN = [
    "Eman", "Eman", "Mona", "Heba", "Aya", "Marwa", "Sara", "Asmaa",
    "Amira", "Fatma", "Nour", "Mariam", "Yasmin", "Dina", "Rania",
    "Laila", "Salma", "Dalia", "Reem", "Hala", "Shimaa", "Noha",
    "Ghada", "Maha", "Nourhan", "Esraa", "Doaa", "Nada", "Rana",
    "Hanan", "Manal",
]
_LAST_EN = [
    "Mohamed", "Mohamed", "Ahmed", "Ahmed", "Ali", "Ali",
    "Hassan", "Hassan", "Mahmoud", "Ibrahim",
    "Salah", "Mostafa", "Adel", "Gamal", "Saad", "El-Sayed",
    "Samir", "Omar", "Hussein", "Kamal", "Magdy", "Salem",
    "Saleh", "Ramadan", "Hamdy", "Khaled", "Saeed", "Farouk",
    "Mansour", "Abdel-Rahman", "Nasser", "Soliman", "Fahmy",
    "Abdallah", "Youssef", "Osman", "El-Masry", "Helmy", "Shaker",
    "Gaber", "Tawfik", "Barakat", "Zaki", "Kamel", "Khalil",
]


def _egyptian_name(arabic_ratio: float = 0.6) -> tuple[str, str]:
    """Return (full_name, email_prefix) for an Egyptian person.

    arabic_ratio controls how often the display name is in Arabic script.
    """
    gender = random.choice(["m", "f"])
    if random.random() < arabic_ratio:
        first = random.choice(_MALE_FIRST_AR if gender == "m" else _FEMALE_FIRST_AR)
        last = random.choice(_LAST_AR)
        full_name = f"{first} {last}"
    else:
        first = random.choice(_MALE_FIRST_EN if gender == "m" else _FEMALE_FIRST_EN)
        last = random.choice(_LAST_EN)
        full_name = f"{first} {last}"

    first_en = random.choice(_MALE_FIRST_EN if gender == "m" else _FEMALE_FIRST_EN)
    last_en = random.choice(_LAST_EN)
    email_prefix = f"{first_en.lower()}.{last_en.lower().replace('-', '')}"
    return full_name, email_prefix


def _egyptian_staff_email(prefix: str) -> str:
    return f"{prefix}@gochat247.com"

# ─── Config ──────────────────────────────────────────────────────

AGENT_COUNT = 60
TEAM_LEAD_COUNT = 5
SUPERVISOR_COUNT = 12
QA_COUNT = 8
ADMIN_COUNT = 3
CALL_COUNT = 35000
CASE_COUNT = 25000
DAYS_OF_DATA = 730  # ~2 years

CATEGORIES = {
    "Billing":    ["Overcharge", "Refund Request", "Fee Dispute", "Statement Error"],
    "Technical":  ["App Crash", "Login Issue", "OTP Failure", "Slow Performance", "Trading Error"],
    "Account":    ["Profile Update", "Closure Request", "KYC Update", "Account Unlock", "Password Reset"],
    "Service":    ["Coverage Issue", "Plan Change", "Transfer Request", "Statement Request"],
    "Trading":    ["Order Dispute", "Settlement Issue", "Dividend Query", "Corporate Action"],
}

PRIORITIES = ["low", "medium", "high", "critical"]
PRIORITY_WEIGHTS = [15, 50, 25, 10]

CASE_STATUSES = ["open", "in_progress", "pending_customer", "escalated", "resolved", "closed"]
STATUS_WEIGHTS = [5, 8, 4, 3, 40, 40]

CALL_STATUSES = ["completed", "completed", "completed", "completed", "abandoned", "transferred"]

SLA_POLICIES = {
    "critical": {"frt": 15, "rt": 120},
    "high":     {"frt": 30, "rt": 240},
    "medium":   {"frt": 60, "rt": 480},
    "low":      {"frt": 120, "rt": 1440},
}

QA_CRITERIA = ["greeting", "identification", "empathy", "resolution", "closing", "compliance", "accuracy"]


_BUSINESS_WEEKDAYS = {6, 0, 1, 2, 3}  # Sun=6, Mon=0, Tue=1, Wed=2, Thu=3

def random_ts(days_back=DAYS_OF_DATA):
    """Generate a random timestamp within Egyptian business hours (Sun-Thu 09:00-22:00)."""
    for _ in range(100):
        base = datetime.now() - timedelta(days=random.randint(0, days_back))
        base = base.replace(
            hour=random.randint(9, 21),
            minute=random.randint(0, 59),
            second=random.randint(0, 59),
        )
        if base.weekday() in _BUSINESS_WEEKDAYS:
            return base
    return base


def ts_str(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# ─── Load MCDR registry for linking ─────────────────────────────

print("Loading MCDR registry data...")

core_conn = sqlite3.connect("mcdr_core.db")
core_conn.row_factory = sqlite3.Row
investors = [dict(r) for r in core_conn.execute("SELECT investor_id FROM investors WHERE account_status='Active' LIMIT 20000").fetchall()]
core_conn.close()

mobile_conn = sqlite3.connect("mcdr_mobile.db")
mobile_conn.row_factory = sqlite3.Row
app_users = [dict(r) for r in mobile_conn.execute("SELECT investor_id, mobile FROM app_users WHERE status='Active'").fetchall()]
mobile_conn.close()

investor_ids = [inv["investor_id"] for inv in investors]
caller_pool = [(u["investor_id"], u["mobile"]) for u in app_users]

print(f"  {len(investor_ids)} active investors, {len(caller_pool)} active app users for linking")

# ─── Create CX Database ─────────────────────────────────────────

print("Creating mcdr_cx.db...")

cx = sqlite3.connect("mcdr_cx.db")
c = cx.cursor()

c.executescript("""
DROP TABLE IF EXISTS cx_users;
DROP TABLE IF EXISTS calls;
DROP TABLE IF EXISTS cti_events;
DROP TABLE IF EXISTS case_taxonomy;
DROP TABLE IF EXISTS sla_policies;
DROP TABLE IF EXISTS verification_sessions;
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS case_notes;
DROP TABLE IF EXISTS case_history;
DROP TABLE IF EXISTS sla_breaches;
DROP TABLE IF EXISTS escalation_rules;
DROP TABLE IF EXISTS escalations;
DROP TABLE IF EXISTS qa_scorecards;
DROP TABLE IF EXISTS qa_evaluations;
DROP TABLE IF EXISTS outbound_tasks;
DROP TABLE IF EXISTS kb_articles;
DROP TABLE IF EXISTS approvals;
DROP TABLE IF EXISTS agent_presence;

-- CX Staff
CREATE TABLE cx_users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    full_name TEXT,
    email TEXT,
    role TEXT,
    tier TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT
);

-- Call Records
CREATE TABLE calls (
    call_id INTEGER PRIMARY KEY,
    ani TEXT,
    dnis TEXT,
    investor_id INTEGER,
    queue TEXT,
    ivr_path TEXT,
    agent_id INTEGER,
    status TEXT,
    call_start TEXT,
    call_end TEXT,
    duration_seconds INTEGER,
    wait_seconds INTEGER,
    recording_url TEXT
);

-- CTI Events
CREATE TABLE cti_events (
    event_id INTEGER PRIMARY KEY,
    call_id INTEGER,
    event_type TEXT,
    timestamp TEXT,
    payload TEXT
);

-- Case Taxonomy
CREATE TABLE case_taxonomy (
    taxonomy_id INTEGER PRIMARY KEY,
    category TEXT,
    subcategory TEXT,
    description TEXT,
    is_active INTEGER DEFAULT 1
);

-- SLA Policies
CREATE TABLE sla_policies (
    policy_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    priority TEXT,
    first_response_minutes INTEGER,
    resolution_minutes INTEGER,
    is_active INTEGER DEFAULT 1
);

-- Verification Sessions
CREATE TABLE verification_sessions (
    verification_id INTEGER PRIMARY KEY,
    investor_id INTEGER,
    agent_id INTEGER,
    call_id INTEGER,
    method TEXT DEFAULT 'verbal',
    status TEXT DEFAULT 'pending',
    steps_completed TEXT DEFAULT '{}',
    steps_required TEXT DEFAULT '["full_name","national_id","mobile_number","account_status"]',
    failure_reason TEXT,
    notes TEXT,
    created_at TEXT,
    verified_at TEXT,
    expires_at TEXT
);

-- Cases / Tickets
CREATE TABLE cases (
    case_id INTEGER PRIMARY KEY,
    case_number TEXT UNIQUE,
    call_id INTEGER,
    investor_id INTEGER,
    agent_id INTEGER,
    taxonomy_id INTEGER,
    verification_id INTEGER,
    priority TEXT,
    status TEXT,
    subject TEXT,
    description TEXT,
    sla_policy_id INTEGER,
    first_response_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    created_at TEXT,
    updated_at TEXT,
    pending_seconds INTEGER DEFAULT 0,
    pending_since TEXT,
    resolution_code TEXT
);

-- Case Notes
CREATE TABLE case_notes (
    note_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    author_id INTEGER,
    content TEXT,
    is_internal INTEGER DEFAULT 0,
    created_at TEXT
);

-- Case History (field-level audit)
CREATE TABLE case_history (
    history_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    field_changed TEXT,
    old_value TEXT,
    new_value TEXT,
    changed_by INTEGER,
    changed_at TEXT
);

-- SLA Breaches
CREATE TABLE sla_breaches (
    breach_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    policy_id INTEGER,
    breach_type TEXT,
    breached_at TEXT
);

-- Escalation Rules
CREATE TABLE escalation_rules (
    rule_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    trigger_condition TEXT,
    from_tier TEXT,
    to_tier TEXT,
    alert_channels TEXT,
    is_active INTEGER DEFAULT 1
);

-- Escalations
CREATE TABLE escalations (
    escalation_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    rule_id INTEGER,
    from_agent_id INTEGER,
    to_agent_id INTEGER,
    from_tier TEXT,
    to_tier TEXT,
    reason TEXT,
    escalated_at TEXT
);

-- QA Scorecards
CREATE TABLE qa_scorecards (
    scorecard_id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    criteria TEXT,
    max_score INTEGER DEFAULT 100,
    is_active INTEGER DEFAULT 1
);

-- QA Evaluations
CREATE TABLE qa_evaluations (
    evaluation_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    call_id INTEGER,
    evaluator_id INTEGER,
    agent_id INTEGER,
    scorecard_id INTEGER,
    scores TEXT,
    total_score REAL,
    feedback TEXT,
    evaluated_at TEXT
);

-- Knowledge Base
CREATE TABLE kb_articles (
    article_id INTEGER PRIMARY KEY,
    title TEXT,
    category TEXT,
    content TEXT,
    tags TEXT,
    author_id INTEGER,
    is_published INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

-- Approvals
CREATE TABLE approvals (
    approval_id INTEGER PRIMARY KEY,
    case_id INTEGER,
    requested_by INTEGER,
    reviewed_by INTEGER,
    approval_type TEXT,
    amount REAL,
    description TEXT,
    status TEXT DEFAULT 'pending',
    reviewer_notes TEXT,
    requested_at TEXT,
    reviewed_at TEXT
);

-- Agent Presence
CREATE TABLE agent_presence (
    agent_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'offline',
    updated_at TEXT
);

-- Outbound Tasks
CREATE TABLE outbound_tasks (
    task_id INTEGER PRIMARY KEY,
    task_type TEXT,
    investor_id INTEGER,
    agent_id INTEGER,
    case_id INTEGER,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    notes TEXT,
    outcome TEXT,
    scheduled_at TEXT,
    attempted_at TEXT,
    completed_at TEXT,
    created_at TEXT,
    updated_at TEXT
);
""")

# ─── 1. CX Staff ────────────────────────────────────────────────

print("Generating CX staff...")

user_id = 1
agent_ids = []
team_lead_ids = []
supervisor_ids = []
qa_ids = []
t2_agent_ids = []

for i in range(AGENT_COUNT):
    tier = "tier2" if i < 10 else "tier1"
    role = "senior_agent" if tier == "tier2" else "agent"
    name, email_pfx = _egyptian_name()
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"agent{i+1}", name, _egyptian_staff_email(email_pfx),
        role, tier, 1, ts_str(random_ts(900))
    ))
    agent_ids.append(user_id)
    if tier == "tier2":
        t2_agent_ids.append(user_id)
    user_id += 1

for i in range(TEAM_LEAD_COUNT):
    name, email_pfx = _egyptian_name(arabic_ratio=0.5)
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"tl{i+1}", name, _egyptian_staff_email(email_pfx),
        "team_lead", "tier2", 1, ts_str(random_ts(900))
    ))
    team_lead_ids.append(user_id)
    user_id += 1

for i in range(SUPERVISOR_COUNT):
    name, email_pfx = _egyptian_name(arabic_ratio=0.5)
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"supervisor{i+1}", name, _egyptian_staff_email(email_pfx),
        "supervisor", "tier2", 1, ts_str(random_ts(900))
    ))
    supervisor_ids.append(user_id)
    user_id += 1

for i in range(QA_COUNT):
    name, email_pfx = _egyptian_name(arabic_ratio=0.5)
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"qa{i+1}", name, _egyptian_staff_email(email_pfx),
        "qa_analyst", "tier2", 1, ts_str(random_ts(900))
    ))
    qa_ids.append(user_id)
    user_id += 1

for i in range(ADMIN_COUNT):
    name, email_pfx = _egyptian_name(arabic_ratio=0.4)
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"admin{i+1}", name, _egyptian_staff_email(email_pfx),
        "admin", "tier2", 1, ts_str(random_ts(900))
    ))
    user_id += 1

t1_agent_ids = [aid for aid in agent_ids if aid not in t2_agent_ids]
all_staff = agent_ids + supervisor_ids

# ─── 2. Reference Data ──────────────────────────────────────────

print("Inserting reference data...")

tax_id = 1
taxonomy_ids = []
for cat, subs in CATEGORIES.items():
    for sub in subs:
        c.execute("INSERT INTO case_taxonomy VALUES (?,?,?,?,?)", (
            tax_id, cat, sub, f"{cat} — {sub}", 1
        ))
        taxonomy_ids.append(tax_id)
        tax_id += 1

pol_id = 1
policy_map = {}
for priority, times in SLA_POLICIES.items():
    c.execute("INSERT INTO sla_policies VALUES (?,?,?,?,?,?)", (
        pol_id, f"{priority.title()} SLA", priority, times["frt"], times["rt"], 1
    ))
    policy_map[priority] = pol_id
    pol_id += 1

c.execute("INSERT INTO escalation_rules VALUES (?,?,?,?,?,?,?)",
          (1, "T1→T2 SLA breach", "sla_breach", "tier1", "tier2", "email,slack", 1))
c.execute("INSERT INTO escalation_rules VALUES (?,?,?,?,?,?,?)",
          (2, "T1→T2 Critical", "priority=critical", "tier1", "tier2", "email,slack,sms", 1))
c.execute("INSERT INTO escalation_rules VALUES (?,?,?,?,?,?,?)",
          (3, "T1→T2 Manual", "manual", "tier1", "tier2", "email", 1))

c.execute("INSERT INTO qa_scorecards VALUES (?,?,?,?,?)",
          (1, "Standard Voice QA", ",".join(QA_CRITERIA), 100, 1))
c.execute("INSERT INTO qa_scorecards VALUES (?,?,?,?,?)",
          (2, "Escalation Review", "identification,resolution,compliance,documentation", 100, 1))

# ─── 3. Call Records ────────────────────────────────────────────

print(f"Generating {CALL_COUNT:,} call records...")

call_data = []
for call_id in range(1, CALL_COUNT + 1):
    caller = random.choice(caller_pool)
    investor_id = caller[0]
    ani = caller[1]
    agent_id = random.choice(t1_agent_ids)
    call_ts = random_ts()
    status = random.choice(CALL_STATUSES)
    if status == "abandoned":
        duration = random.randint(0, 15)
        wait = random.randint(30, 300)
    elif status == "transferred":
        duration = random.randint(30, 300)
        wait = random.randint(5, 120)
    else:
        duration = random.randint(60, 1800)
        wait = random.randint(5, 120)

    queues = ["billing", "technical", "general", "priority", "retention"]
    ivr_paths = ["1>2", "1>3", "2>1", "3>1", "1>1>2", "2>2"]

    call_end = call_ts + timedelta(seconds=duration + wait)

    c.execute("INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        call_id, ani, "+20221234567", investor_id,
        random.choice(queues), random.choice(ivr_paths),
        agent_id, status,
        ts_str(call_ts), ts_str(call_end),
        duration, wait,
        f"https://recordings.gochat247.local/calls/{call_id}.wav" if status == "completed" else None
    ))
    call_data.append({
        "call_id": call_id, "investor_id": investor_id,
        "agent_id": agent_id, "ts": call_ts, "status": status, "ani": ani
    })

# ─── 4. CTI Events ──────────────────────────────────────────────

print("Generating CTI events...")

event_id = 1
for call in call_data[:15000]:
    events = ["call_offered", "call_answered"]
    if random.random() < 0.2:
        events.append("call_held")
        events.append("call_resumed")
    events.append("call_ended")

    t = call["ts"]
    for evt in events:
        c.execute("INSERT INTO cti_events VALUES (?,?,?,?,?)", (
            event_id, call["call_id"], evt, ts_str(t), None
        ))
        t += timedelta(seconds=random.randint(5, 120))
        event_id += 1

# ─── 5. Verification Sessions & Cases ──────────────────────────

VERIFICATION_STEPS = ["full_name", "national_id", "mobile_number", "account_status"]
VERIFICATION_METHODS = ["verbal", "verbal", "verbal", "otp", "document"]

print(f"Generating {CASE_COUNT:,} verification sessions + cases...")

import json

RESOLUTION_CODES = [
    "fixed", "fixed", "fixed", "fixed",
    "information_provided", "information_provided",
    "account_updated", "account_updated",
    "duplicate", "cannot_reproduce",
    "referred_third_party", "customer_withdrew", "wont_fix",
]

available_calls = list(range(len(call_data)))
random.shuffle(available_calls)
call_assignment_idx = 0

case_data = []
verification_id = 1
for case_id in range(1, CASE_COUNT + 1):
    if random.random() < 0.85 and call_assignment_idx < len(available_calls):
        call = call_data[available_calls[call_assignment_idx]]
        call_assignment_idx += 1
    else:
        call = None

    investor_id = call["investor_id"] if call else random.choice(investor_ids)
    agent_id = call["agent_id"] if call else random.choice(t1_agent_ids)
    created_at = call["ts"] if call else random_ts()

    priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0]
    status = random.choices(CASE_STATUSES, weights=STATUS_WEIGHTS)[0]
    taxonomy_id = random.choice(taxonomy_ids)

    cat_idx = (taxonomy_id - 1) // max(1, len(taxonomy_ids) // len(CATEGORIES))
    category = list(CATEGORIES.keys())[min(cat_idx, len(CATEGORIES) - 1)]

    subjects = {
        "Billing": ["Incorrect charge on account", "Refund not received", "Double billing", "Fee dispute"],
        "Technical": ["App crashing on login", "OTP not arriving", "Portfolio not loading", "Trading screen frozen"],
        "Account": ["Need to update KYC", "Account locked after 3 attempts", "Password reset needed", "Close my account"],
        "Service": ["Request account statement", "Transfer shares to another broker", "Dividend not credited"],
        "Trading": ["Order executed at wrong price", "Settlement delayed", "Corporate action not applied"],
    }
    subject = random.choice(subjects.get(category, ["General inquiry"]))

    sla_policy_id = policy_map[priority]

    frt_at = None
    resolved_at = None
    closed_at = None

    sla_frt = SLA_POLICIES[priority]["frt"]
    sla_rt = SLA_POLICIES[priority]["rt"]

    if status not in ["open"]:
        frt_minutes = random.randint(1, sla_frt + 30)
        frt_at = ts_str(created_at + timedelta(minutes=frt_minutes))

    if status in ["resolved", "closed"]:
        rt_minutes = random.randint(max(10, sla_frt + 1), sla_rt + 200)
        resolved_at = ts_str(created_at + timedelta(minutes=rt_minutes))

    if status == "closed" and resolved_at:
        resolved_dt = datetime.strptime(resolved_at, "%Y-%m-%d %H:%M:%S")
        close_offset = int((resolved_dt - created_at).total_seconds() / 60)
        closed_at = ts_str(created_at + timedelta(minutes=random.randint(
            close_offset + 1, close_offset + 1440
        )))

    if status == "open":
        updated_at = ts_str(created_at + timedelta(hours=random.randint(0, 2)))
    elif status in ["in_progress", "pending_customer", "escalated"]:
        updated_at = frt_at or ts_str(created_at + timedelta(hours=random.randint(1, 24)))
    else:
        updated_at = closed_at or resolved_at or frt_at or ts_str(created_at + timedelta(hours=random.randint(1, 48)))

    v_method = random.choice(VERIFICATION_METHODS)
    v_status = random.choices(
        ["verified", "verified", "verified", "failed"],
        weights=[85, 5, 5, 5],
    )[0]

    steps_completed = {}
    if v_status == "verified":
        steps_completed = {s: True for s in VERIFICATION_STEPS}
    else:
        passed = random.sample(VERIFICATION_STEPS, random.randint(0, 2))
        steps_completed = {s: (s in passed) for s in VERIFICATION_STEPS}

    v_created = created_at - timedelta(minutes=random.randint(1, 5))
    v_verified = ts_str(v_created + timedelta(minutes=random.randint(1, 3))) if v_status == "verified" else None
    v_expires = ts_str(v_created + timedelta(minutes=30))
    v_failure_reason = random.choice([
        "Caller could not confirm National ID",
        "Mobile number mismatch",
        "Caller refused to verify identity",
    ]) if v_status == "failed" else None

    c.execute(
        "INSERT INTO verification_sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (verification_id, investor_id, agent_id,
         call["call_id"] if call else None,
         v_method, v_status,
         json.dumps(steps_completed),
         json.dumps(VERIFICATION_STEPS),
         v_failure_reason, None,
         ts_str(v_created), v_verified, v_expires),
    )

    cur_verification_id = verification_id if v_status == "verified" else None
    verification_id += 1

    resolution_code = random.choice(RESOLUTION_CODES) if status in ("resolved", "closed") else None

    pending_seconds = 0
    if status in ("resolved", "closed", "in_progress", "escalated") and random.random() < 0.25:
        pending_seconds = random.randint(600, 86400)

    c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        case_id, f"CAS-{case_id:06}", call["call_id"] if call else None,
        investor_id, agent_id, taxonomy_id, cur_verification_id,
        priority, status, subject,
        f"Customer reported: {subject.lower()}. Investor code: INV-{investor_id:06}",
        sla_policy_id, frt_at, resolved_at, closed_at,
        ts_str(created_at), updated_at,
        pending_seconds, None, resolution_code,
    ))
    case_data.append({
        "case_id": case_id, "agent_id": agent_id, "investor_id": investor_id,
        "priority": priority, "status": status, "created_at": created_at,
        "frt_at": frt_at, "resolved_at": resolved_at, "sla_policy_id": sla_policy_id,
        "call_id": call["call_id"] if call else None,
    })

# ─── 6. Case Notes ──────────────────────────────────────────────

print("Generating case notes...")

note_id = 1
note_templates = {
    "initial": [
        "Customer called regarding {subject}. Verified identity via national ID.",
        "Inbound call received. Customer explained the issue clearly.",
        "Customer is a {tier} investor. Pulled up portfolio and account details.",
    ],
    "update": [
        "Reviewed account history. Issue appears related to recent transaction.",
        "Contacted back-office team for clarification on the dispute.",
        "Waiting for customer to provide additional documentation.",
        "Escalated to senior team for review per customer request.",
        "Customer provided screenshots confirming the issue.",
    ],
    "resolution": [
        "Issue resolved. Customer confirmed satisfaction.",
        "Refund processed and confirmed with customer.",
        "Account corrected. Sent confirmation email to customer.",
        "Technical team deployed fix. Verified working with customer.",
        "Case resolved after back-office review. No further action needed.",
    ],
    "internal": [
        "Checked with compliance — no regulatory impact.",
        "Supervisor review: handling was appropriate.",
        "Note: customer has history of similar complaints.",
        "SLA warning — approaching FRT threshold.",
        "Cross-referenced with trading system — data matches.",
    ],
}

for case in case_data:
    note_count = random.randint(1, 6)
    t = case["created_at"]

    c.execute("INSERT INTO case_notes VALUES (?,?,?,?,?,?)", (
        note_id, case["case_id"], case["agent_id"],
        random.choice(note_templates["initial"]).format(subject="their issue", tier="retail"),
        0, ts_str(t)
    ))
    note_id += 1
    t += timedelta(minutes=random.randint(5, 60))

    for _ in range(note_count - 1):
        is_internal = random.random() < 0.25
        template_key = "internal" if is_internal else random.choice(["update", "update", "resolution"])
        if is_internal:
            author = random.choice(supervisor_ids)
        else:
            author = case["agent_id"]

        c.execute("INSERT INTO case_notes VALUES (?,?,?,?,?,?)", (
            note_id, case["case_id"], author,
            random.choice(note_templates[template_key]),
            1 if is_internal else 0,
            ts_str(t)
        ))
        note_id += 1
        t += timedelta(minutes=random.randint(10, 480))

# ─── 7. Case History ────────────────────────────────────────────
# Build a coherent transition chain that ends at the case's final status.
# Some resolved/closed cases went through escalation first.

print("Generating case history...")

_STATUS_CHAINS_DIRECT = {
    "open":             [],
    "in_progress":      [("open", "in_progress")],
    "pending_customer": [("open", "in_progress"), ("in_progress", "pending_customer")],
    "escalated":        [("open", "in_progress"), ("in_progress", "escalated")],
    "resolved":         [("open", "in_progress"), ("in_progress", "resolved")],
    "closed":           [("open", "in_progress"), ("in_progress", "resolved"), ("resolved", "closed")],
}

_STATUS_CHAINS_VIA_ESC = {
    "resolved":  [("open", "in_progress"), ("in_progress", "escalated"), ("escalated", "in_progress"), ("in_progress", "resolved")],
    "closed":    [("open", "in_progress"), ("in_progress", "escalated"), ("escalated", "in_progress"), ("in_progress", "resolved"), ("resolved", "closed")],
}

# Mark ~15% of resolved/closed cases as having gone through escalation
escalated_then_resolved = set()
for case in case_data:
    if case["status"] in ("resolved", "closed") and random.random() < 0.15:
        escalated_then_resolved.add(case["case_id"])

def _get_chain(case):
    if case["case_id"] in escalated_then_resolved:
        return _STATUS_CHAINS_VIA_ESC.get(case["status"], [])
    return _STATUS_CHAINS_DIRECT.get(case["status"], [])

history_id = 1
for case in case_data:
    t = case["created_at"] + timedelta(minutes=random.randint(1, 30))
    chain = _get_chain(case)

    for old_val, new_val in chain:
        changed_by = case["agent_id"]
        if new_val == "escalated":
            changed_by = random.choice(supervisor_ids + [case["agent_id"]])
        c.execute("INSERT INTO case_history VALUES (?,?,?,?,?,?,?)", (
            history_id, case["case_id"], "status", old_val, new_val,
            changed_by, ts_str(t)
        ))
        history_id += 1
        t += timedelta(minutes=random.randint(10, 120))

    if random.random() < 0.3:
        old_p = random.choice(PRIORITIES)
        c.execute("INSERT INTO case_history VALUES (?,?,?,?,?,?,?)", (
            history_id, case["case_id"], "priority", old_p, case["priority"],
            random.choice(supervisor_ids), ts_str(t + timedelta(minutes=random.randint(5, 60)))
        ))
        history_id += 1

# ─── 8. SLA Breaches ────────────────────────────────────────────

print("Generating SLA breaches...")

breach_id = 1
for case in case_data:
    sla = SLA_POLICIES[case["priority"]]

    if case["frt_at"]:
        frt_delta = (datetime.strptime(case["frt_at"], "%Y-%m-%d %H:%M:%S") - case["created_at"]).total_seconds() / 60
        if frt_delta > sla["frt"]:
            c.execute("INSERT INTO sla_breaches VALUES (?,?,?,?,?)", (
                breach_id, case["case_id"], case["sla_policy_id"],
                "first_response", case["frt_at"]
            ))
            breach_id += 1

    if case["resolved_at"]:
        rt_delta = (datetime.strptime(case["resolved_at"], "%Y-%m-%d %H:%M:%S") - case["created_at"]).total_seconds() / 60
        if rt_delta > sla["rt"]:
            c.execute("INSERT INTO sla_breaches VALUES (?,?,?,?,?)", (
                breach_id, case["case_id"], case["sla_policy_id"],
                "resolution", case["resolved_at"]
            ))
            breach_id += 1

# ─── 9. Escalations ─────────────────────────────────────────────
# Only create escalation records for cases that actually went through escalated status:
# - cases whose final status is "escalated"
# - cases in escalated_then_resolved (resolved/closed via escalation)

print("Generating escalations...")

esc_id = 1
escalation_eligible = [
    case for case in case_data
    if case["status"] == "escalated" or case["case_id"] in escalated_then_resolved
]
for case in escalation_eligible:
    rule_id = random.choice([1, 2, 3])
    from_agent = case["agent_id"]
    to_agent = random.choice(t2_agent_ids + supervisor_ids)
    while to_agent == from_agent:
        to_agent = random.choice(t2_agent_ids + supervisor_ids)

    reasons = [
        "Customer dissatisfied with initial resolution",
        "SLA breach — requires senior attention",
        "Complex case requiring T2 expertise",
        "Customer explicitly requested supervisor",
        "Regulatory compliance concern flagged",
        "High-value investor — priority handling required",
        "Multiple related complaints on same issue",
    ]

    c.execute("INSERT INTO escalations VALUES (?,?,?,?,?,?,?,?,?)", (
        esc_id, case["case_id"], rule_id, from_agent, to_agent,
        "tier1", "tier2", random.choice(reasons),
        ts_str(case["created_at"] + timedelta(minutes=random.randint(15, 240)))
    ))
    esc_id += 1

    if case["status"] in ("resolved", "closed", "in_progress"):
        c.execute("UPDATE cases SET agent_id = ? WHERE case_id = ?", (to_agent, case["case_id"]))
        case["agent_id"] = to_agent

# ─── 10. QA Evaluations ─────────────────────────────────────────

print("Generating QA evaluations...")

eval_id = 1
sampled = random.sample(case_data, min(6000, len(case_data)))
for case in sampled:
    evaluator = random.choice(qa_ids)
    scorecard_id = 2 if case["status"] == "escalated" else 1

    criteria_scores = {}
    for criterion in QA_CRITERIA:
        criteria_scores[criterion] = random.randint(5, 20)
    total = sum(criteria_scores.values())
    normalized = round(total / len(QA_CRITERIA) * 5, 1)

    feedbacks = [
        "Good handling overall. Minor improvement needed on empathy.",
        "Excellent call. All criteria met above standard.",
        "Needs improvement on compliance documentation.",
        "Strong resolution skills. Greeting could be warmer.",
        "Below standard — coaching session recommended.",
        "Outstanding call. Recommended as training example.",
        "Adequate performance. Follow-up on closing procedure.",
    ]

    c.execute("INSERT INTO qa_evaluations VALUES (?,?,?,?,?,?,?,?,?,?)", (
        eval_id, case["case_id"], case["call_id"],
        evaluator, case["agent_id"], scorecard_id,
        str(criteria_scores), normalized,
        random.choice(feedbacks),
        ts_str(case["created_at"] + timedelta(days=random.randint(1, 14)))
    ))
    eval_id += 1

# ─── 8. Outbound Tasks ──────────────────────────────────────────

print("Generating outbound tasks...")

OUTBOUND_TYPES = ["broken_signup", "inactive_user", "transaction_verification", "qa_callback"]
OUTBOUND_NOTES = {
    "broken_signup": [
        "User dropped off during KYC upload step",
        "Registration incomplete — email verified but no phone",
        "Sign-up abandoned at terms acceptance",
        "OTP verification failed twice — user might need help",
    ],
    "inactive_user": [
        "No login in 90+ days — follow up on account status",
        "Account dormant since onboarding — never placed a trade",
        "Previous active trader, inactive for 60 days",
        "App installed but never completed first login",
    ],
    "transaction_verification": [
        "Large sell order flagged for verbal confirmation",
        "Transfer to external account requires callback verification",
        "Settlement mismatch needs investor confirmation",
        "Dividend reinvestment preference needs confirmation",
    ],
    "qa_callback": [
        "Follow-up on case resolution satisfaction",
        "Post-escalation quality check with investor",
        "Confirm issue was fully resolved after agent intervention",
        "Scheduled callback per investor request during last call",
    ],
}
OUTBOUND_OUTCOMES = [
    "Investor confirmed — proceeding with action",
    "No answer — will retry tomorrow",
    "Investor requested reschedule to next week",
    "Issue resolved during callback",
    "Phone number no longer in service",
    "Investor declined further action",
    "Voicemail left — follow-up in 48h",
    "Completed successfully — investor satisfied",
]

NUM_OUTBOUND = 400
outbound_agent_pool = [a for a in agent_ids[:8]]
task_id = 1

for _ in range(NUM_OUTBOUND):
    task_type = random.choice(OUTBOUND_TYPES)
    agent_id = random.choice(outbound_agent_pool)
    investor_id = random.choice(investor_ids) if random.random() > 0.1 else None
    case_id = random.choice(case_data)["case_id"] if task_type == "qa_callback" and random.random() > 0.3 else None
    priority = random.choices(["low", "medium", "high", "critical"], weights=[20, 50, 25, 5])[0]

    created = datetime.now() - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 12),
        minutes=random.randint(0, 59),
    )
    scheduled = created + timedelta(hours=random.randint(0, 48))

    status_roll = random.random()
    if status_roll < 0.35:
        status = "completed"
        attempted = scheduled + timedelta(minutes=random.randint(0, 120))
        completed_at = attempted + timedelta(minutes=random.randint(2, 30))
        outcome_text = random.choice(OUTBOUND_OUTCOMES)
    elif status_roll < 0.50:
        status = "failed"
        attempted = scheduled + timedelta(minutes=random.randint(0, 120))
        completed_at = attempted + timedelta(minutes=random.randint(1, 10))
        outcome_text = random.choice(["No answer — will retry", "Phone disconnected", "Wrong number"])
    elif status_roll < 0.70:
        status = "in_progress"
        attempted = scheduled + timedelta(minutes=random.randint(0, 30))
        completed_at = None
        outcome_text = None
    else:
        status = "pending"
        attempted = None
        completed_at = None
        outcome_text = None

    c.execute(
        "INSERT INTO outbound_tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (task_id, task_type, investor_id, agent_id, case_id,
         status, priority,
         random.choice(OUTBOUND_NOTES[task_type]),
         outcome_text,
         ts_str(scheduled),
         ts_str(attempted) if attempted else None,
         ts_str(completed_at) if completed_at else None,
         ts_str(created), ts_str(created)),
    )
    task_id += 1

print(f"  → {NUM_OUTBOUND} outbound tasks")

# ─── Agent Presence ─────────────────────────────────────────────

print("Seeding knowledge base articles...")

KB_ARTICLES = [
    ("How to Process a Refund", "Billing", "1. Verify the customer's identity\n2. Confirm the transaction in the trading system\n3. Calculate the refund amount\n4. Submit a refund approval request (required for amounts > EGP 500)\n5. Once approved, process via the billing system\n6. Send confirmation email to the customer\n7. Add case note documenting the refund", "refund,billing,process"),
    ("Password Reset Procedure", "Account", "1. Verify caller identity (4-step verification required)\n2. Confirm the registered email address\n3. Trigger password reset via admin panel\n4. Guide customer through the reset email\n5. Confirm successful login\n6. Document in case notes", "password,reset,account,security"),
    ("Escalation Guidelines", "Process", "Escalate to T2 when:\n- Issue requires back-office system access\n- Customer requests supervisor\n- SLA breach is imminent (< 15 min remaining)\n- Trading dispute involves > EGP 10,000\n- Regulatory compliance concern identified\n\nAlways document the escalation reason clearly.", "escalation,guidelines,t2,supervisor"),
    ("KYC Update Process", "Account", "1. Verify existing identity\n2. Request updated documents (National ID, proof of address)\n3. Upload documents via KYC portal\n4. Submit for compliance review\n5. KYC review takes 2-3 business days\n6. Notify customer of outcome\n\nNote: Accounts are restricted during KYC review.", "kyc,update,compliance,documents"),
    ("Handling Complaint Calls", "Skills", "1. Listen actively — let the customer vent\n2. Acknowledge the issue with empathy\n3. Apologize sincerely (even if not our fault)\n4. Take ownership — 'I will personally ensure...'\n5. Provide a clear resolution plan with timeline\n6. Follow up within 24 hours\n7. Document everything in case notes", "complaints,empathy,soft-skills"),
    ("Trading Order Dispute Resolution", "Trading", "1. Pull up the order details from the trading system\n2. Check the execution timestamp and market price at that time\n3. Compare with the customer's claimed price\n4. If discrepancy confirmed, escalate to Trading Operations\n5. If within market spread, explain to customer\n6. For orders > EGP 50,000, supervisor approval required\n7. Document all findings in case notes", "trading,dispute,order,execution"),
    ("Account Closure Procedure", "Account", "1. Verify identity (mandatory 4-step verification)\n2. Check for open positions or pending settlements\n3. If positions exist, inform customer they must be closed first\n4. Submit account closure approval request\n5. Once approved, initiate final settlement\n6. Transfer remaining balance to registered bank account\n7. Send closure confirmation letter\n8. Retain records per regulatory requirements (7 years)", "closure,account,settlement"),
    ("SLA Policy Overview", "Process", "Priority levels and response times:\n- Critical: 15 min first response, 2 hour resolution\n- High: 30 min first response, 4 hour resolution\n- Medium: 1 hour first response, 8 hour resolution\n- Low: 2 hour first response, 24 hour resolution\n\nSLA pauses during 'Pending Customer' status.\nBreaches trigger automatic escalation.", "sla,priority,response-time"),
    ("Identity Verification Script", "Scripts", "Opening: 'For your security, I need to verify your identity before we proceed.'\n\nStep 1: 'Could you please confirm your full name as registered?'\nStep 2: 'What are the last four digits of your National ID?'\nStep 3: 'Can you confirm the mobile number linked to your account?'\nStep 4: 'Can you tell me your current account status or last transaction?'\n\nIf failed: 'I'm unable to verify your identity at this time. For your security, I cannot proceed.'", "verification,script,identity,security"),
    ("OTP Troubleshooting Guide", "Technical", "Common OTP issues:\n1. OTP not received — check mobile number, network coverage, SMS blocking\n2. OTP expired — valid for 5 minutes, request new one\n3. Multiple OTP requests — rate limited to 3 per 10 minutes\n4. Wrong OTP — 3 attempts before lockout (30 min)\n\nEscalate if: OTP system appears down (affects multiple customers)", "otp,troubleshooting,technical,sms"),
    ("App Crash Triage", "Technical", "1. Ask for device model and OS version\n2. Ask when the crash occurs (login, trading, portfolio view)\n3. Check known issues board for matching pattern\n4. Request screenshot if possible\n5. Try: force close → clear cache → reinstall\n6. If persists, log a technical ticket with device details\n7. Offer web platform as alternative", "app,crash,technical,mobile,troubleshooting"),
    ("Fee Waiver Policy", "Billing", "Fee waivers can be granted for:\n- First-time occurrence (automatic approval)\n- Service disruption (requires incident reference)\n- Loyalty (5+ year customers, supervisor approval)\n- Competitive retention (supervisor approval)\n\nLimits:\n- Agent: up to EGP 100\n- Team Lead: up to EGP 500\n- Supervisor: up to EGP 2,000\n- Above EGP 2,000: Operations Manager approval", "fees,waiver,billing,policy,limits"),
    ("Dividend Query Handling", "Trading", "1. Check the dividend calendar for the relevant stock\n2. Verify ex-dividend date and record date\n3. Confirm the customer held shares on the record date\n4. Check if dividend has been credited (T+2 after payment date)\n5. If not credited and past payment date, escalate to Settlement\n6. Provide the customer with expected timeline", "dividend,trading,settlement,calendar"),
    ("Outbound Call Best Practices", "Skills", "Before the call:\n- Review customer history and case context\n- Prepare talking points\n- Have resolution ready\n\nDuring the call:\n- Identify yourself and company\n- State the purpose clearly\n- Be concise and respectful of their time\n- Confirm understanding before ending\n\nAfter the call:\n- Document outcome immediately\n- Update case status\n- Schedule follow-up if needed", "outbound,callback,skills,best-practices"),
]

article_id = 1
for title, category, content, tags in KB_ARTICLES:
    c.execute("INSERT INTO kb_articles VALUES (?,?,?,?,?,?,?,?,?)", (
        article_id, title, category, content, tags,
        random.choice(supervisor_ids),
        1, ts_str(random_ts(365)), ts_str(random_ts(90))
    ))
    article_id += 1

print(f"  → {article_id - 1} knowledge base articles")

print("Generating approval requests...")

APPROVAL_TYPES = ["refund", "account_closure", "data_correction", "fee_waiver", "escalation_override"]
APPROVAL_DESCRIPTIONS = {
    "refund": [
        "Customer overcharged EGP {amount} — refund requested",
        "Duplicate transaction EGP {amount} — needs reversal",
        "Service failure compensation — EGP {amount}",
    ],
    "account_closure": [
        "Customer requested account closure — final settlement pending",
        "Dormant account cleanup — investor confirmed closure",
    ],
    "data_correction": [
        "KYC data mismatch — national ID needs correction",
        "Customer name update from official document",
        "Mobile number change — verified via OTP",
    ],
    "fee_waiver": [
        "Late payment fee waiver — first-time occurrence EGP {amount}",
        "Annual fee waiver for loyal customer — EGP {amount}",
    ],
    "escalation_override": [
        "Priority upgrade to critical — high-value investor",
        "SLA breach override — external dependency",
    ],
}
REVIEWER_NOTES = [
    "Approved — documentation verified",
    "Approved — within policy limits",
    "Rejected — exceeds authority limit, escalate to operations",
    "Rejected — insufficient documentation",
    "Approved — exception granted per supervisor discretion",
]

approval_id = 1
resolved_cases = [c for c in case_data if c["status"] in ("resolved", "closed")]
approval_sample = random.sample(resolved_cases, min(300, len(resolved_cases)))

for case in approval_sample:
    atype = random.choice(APPROVAL_TYPES)
    amount = round(random.uniform(50, 5000), 2) if atype in ("refund", "fee_waiver") else None
    desc_templates = APPROVAL_DESCRIPTIONS[atype]
    desc = random.choice(desc_templates).format(amount=f"{amount:.2f}" if amount else "")
    requested_by = case["agent_id"]
    requested_at = case["created_at"] + timedelta(hours=random.randint(1, 48))

    status_roll = random.random()
    if status_roll < 0.55:
        status = "approved"
        reviewed_by = random.choice(supervisor_ids)
        reviewed_at = ts_str(requested_at + timedelta(hours=random.randint(1, 24)))
        notes = random.choice([n for n in REVIEWER_NOTES if "Approved" in n])
    elif status_roll < 0.75:
        status = "rejected"
        reviewed_by = random.choice(supervisor_ids)
        reviewed_at = ts_str(requested_at + timedelta(hours=random.randint(1, 24)))
        notes = random.choice([n for n in REVIEWER_NOTES if "Rejected" in n])
    else:
        status = "pending"
        reviewed_by = None
        reviewed_at = None
        notes = None

    c.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
        approval_id, case["case_id"], requested_by, reviewed_by,
        atype, amount, desc, status, notes,
        ts_str(requested_at), reviewed_at,
    ))
    approval_id += 1

print(f"  → {approval_id - 1} approval requests")

print("Setting agent presence statuses...")

PRESENCE_STATUSES = ["available", "available", "available", "available",
                     "on_break", "acw", "in_call", "in_call", "in_call",
                     "training", "offline"]

now_str = ts_str(datetime.now())
for aid in agent_ids + t2_agent_ids:
    status = random.choice(PRESENCE_STATUSES)
    c.execute("INSERT OR IGNORE INTO agent_presence VALUES (?,?,?)", (aid, status, now_str))

for tlid in team_lead_ids:
    c.execute("INSERT OR IGNORE INTO agent_presence VALUES (?,?,?)", (tlid, "available", now_str))

for sid in supervisor_ids:
    c.execute("INSERT OR IGNORE INTO agent_presence VALUES (?,?,?)", (sid, "available", now_str))

# ─── Indexes & Commit ───────────────────────────────────────────

print("Creating indexes...")

c.executescript("""
CREATE INDEX idx_calls_investor ON calls(investor_id);
CREATE INDEX idx_calls_agent ON calls(agent_id);
CREATE INDEX idx_calls_ani ON calls(ani);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_verif_investor ON verification_sessions(investor_id);
CREATE INDEX idx_verif_agent ON verification_sessions(agent_id);
CREATE INDEX idx_verif_status ON verification_sessions(status);
CREATE INDEX idx_cases_investor ON cases(investor_id);
CREATE INDEX idx_cases_agent ON cases(agent_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_call ON cases(call_id);
CREATE INDEX idx_cases_verif ON cases(verification_id);
CREATE INDEX idx_notes_case ON case_notes(case_id);
CREATE INDEX idx_history_case ON case_history(case_id);
CREATE INDEX idx_breaches_case ON sla_breaches(case_id);
CREATE INDEX idx_escalations_case ON escalations(case_id);
CREATE INDEX idx_qa_agent ON qa_evaluations(agent_id);
CREATE INDEX idx_qa_case ON qa_evaluations(case_id);
CREATE INDEX idx_outbound_status ON outbound_tasks(status);
CREATE INDEX idx_outbound_type ON outbound_tasks(task_type);
CREATE INDEX idx_outbound_agent ON outbound_tasks(agent_id);
CREATE INDEX idx_outbound_investor ON outbound_tasks(investor_id);
""")

cx.commit()
cx.close()

print(f"""
✅ CX Intelligent Layer Generated Successfully!
──────────────────────────────────────────────
  CX Staff:            {AGENT_COUNT} agents + {TEAM_LEAD_COUNT} team leads + {SUPERVISOR_COUNT} supervisors + {QA_COUNT} QA + {ADMIN_COUNT} admins
  Calls:               {CALL_COUNT:,}
  CTI Events:          {event_id - 1:,}
  Verifications:       {verification_id - 1:,}
  Cases:               {CASE_COUNT:,}
  Case Notes:          {note_id - 1:,}
  Case History:        {history_id - 1:,}
  SLA Breaches:        {breach_id - 1:,}
  Escalations:         {esc_id - 1:,}
  QA Evaluations:      {eval_id - 1:,}
""")
