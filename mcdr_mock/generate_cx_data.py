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

fake = Faker()

# ─── Config ──────────────────────────────────────────────────────

AGENT_COUNT = 60
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


def random_ts(days_back=DAYS_OF_DATA):
    base = datetime.now() - timedelta(days=random.randint(0, days_back))
    return base.replace(
        hour=random.randint(8, 20),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
    )


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
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS case_notes;
DROP TABLE IF EXISTS case_history;
DROP TABLE IF EXISTS sla_breaches;
DROP TABLE IF EXISTS escalation_rules;
DROP TABLE IF EXISTS escalations;
DROP TABLE IF EXISTS qa_scorecards;
DROP TABLE IF EXISTS qa_evaluations;

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

-- Cases / Tickets
CREATE TABLE cases (
    case_id INTEGER PRIMARY KEY,
    case_number TEXT UNIQUE,
    call_id INTEGER,
    investor_id INTEGER,
    agent_id INTEGER,
    taxonomy_id INTEGER,
    priority TEXT,
    status TEXT,
    subject TEXT,
    description TEXT,
    sla_policy_id INTEGER,
    first_response_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    created_at TEXT,
    updated_at TEXT
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
""")

# ─── 1. CX Staff ────────────────────────────────────────────────

print("Generating CX staff...")

user_id = 1
agent_ids = []
supervisor_ids = []
qa_ids = []
t2_agent_ids = []

for i in range(AGENT_COUNT):
    tier = "tier2" if i < 10 else "tier1"
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"agent{i+1}", fake.name(), fake.company_email(),
        "agent", tier, 1, ts_str(random_ts(900))
    ))
    agent_ids.append(user_id)
    if tier == "tier2":
        t2_agent_ids.append(user_id)
    user_id += 1

for i in range(SUPERVISOR_COUNT):
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"supervisor{i+1}", fake.name(), fake.company_email(),
        "supervisor", "tier2", 1, ts_str(random_ts(900))
    ))
    supervisor_ids.append(user_id)
    user_id += 1

for i in range(QA_COUNT):
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"qa{i+1}", fake.name(), fake.company_email(),
        "qa_analyst", "tier2", 1, ts_str(random_ts(900))
    ))
    qa_ids.append(user_id)
    user_id += 1

for i in range(ADMIN_COUNT):
    c.execute("INSERT INTO cx_users VALUES (?,?,?,?,?,?,?,?)", (
        user_id, f"admin{i+1}", fake.name(), fake.company_email(),
        "admin", "tier2", 1, ts_str(random_ts(900))
    ))
    user_id += 1

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
    agent_id = random.choice(agent_ids)
    call_ts = random_ts()
    duration = random.randint(30, 1800) if random.random() > 0.08 else random.randint(5, 30)
    wait = random.randint(5, 300)
    status = random.choice(CALL_STATUSES)

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

# ─── 5. Cases / Tickets ─────────────────────────────────────────

print(f"Generating {CASE_COUNT:,} cases...")

case_data = []
for case_id in range(1, CASE_COUNT + 1):
    call = random.choice(call_data) if random.random() < 0.85 else None

    investor_id = call["investor_id"] if call else random.choice(investor_ids)
    agent_id = call["agent_id"] if call else random.choice(agent_ids)
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

    if status not in ["open"]:
        frt_minutes = random.randint(1, SLA_POLICIES[priority]["frt"] + 30)
        frt_at = ts_str(created_at + timedelta(minutes=frt_minutes))

    if status in ["resolved", "closed"]:
        rt_minutes = random.randint(10, SLA_POLICIES[priority]["rt"] + 200)
        resolved_at = ts_str(created_at + timedelta(minutes=rt_minutes))

    if status == "closed":
        closed_at = ts_str(created_at + timedelta(minutes=random.randint(
            int((datetime.strptime(resolved_at, "%Y-%m-%d %H:%M:%S") - created_at).total_seconds() / 60) + 1,
            int((datetime.strptime(resolved_at, "%Y-%m-%d %H:%M:%S") - created_at).total_seconds() / 60) + 1440
        ))) if resolved_at else None

    updated_at = resolved_at or frt_at or ts_str(created_at + timedelta(hours=random.randint(1, 48)))

    c.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        case_id, f"CAS-{case_id:06}", call["call_id"] if call else None,
        investor_id, agent_id, taxonomy_id,
        priority, status, subject,
        f"Customer reported: {subject.lower()}. Investor code: INV-{investor_id:06}",
        sla_policy_id, frt_at, resolved_at, closed_at,
        ts_str(created_at), updated_at
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
        author = case["agent_id"] if not is_internal else random.choice(supervisor_ids + [case["agent_id"]])

        c.execute("INSERT INTO case_notes VALUES (?,?,?,?,?,?)", (
            note_id, case["case_id"], author,
            random.choice(note_templates[template_key]),
            1 if is_internal else 0,
            ts_str(t)
        ))
        note_id += 1
        t += timedelta(minutes=random.randint(10, 480))

# ─── 7. Case History ────────────────────────────────────────────

print("Generating case history...")

history_id = 1
for case in case_data:
    t = case["created_at"] + timedelta(minutes=random.randint(1, 30))

    c.execute("INSERT INTO case_history VALUES (?,?,?,?,?,?,?)", (
        history_id, case["case_id"], "status", "open", "in_progress",
        case["agent_id"], ts_str(t)
    ))
    history_id += 1

    if case["status"] in ["escalated", "resolved", "closed"]:
        t += timedelta(minutes=random.randint(10, 120))
        c.execute("INSERT INTO case_history VALUES (?,?,?,?,?,?,?)", (
            history_id, case["case_id"], "status", "in_progress", case["status"],
            case["agent_id"], ts_str(t)
        ))
        history_id += 1

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

print("Generating escalations...")

esc_id = 1
escalated_cases = [c for c in case_data if c["status"] == "escalated" or random.random() < 0.05]
for case in escalated_cases[:4000]:
    rule_id = random.choice([1, 2, 3])
    from_agent = case["agent_id"]
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

# ─── Indexes & Commit ───────────────────────────────────────────

print("Creating indexes...")

c.executescript("""
CREATE INDEX idx_calls_investor ON calls(investor_id);
CREATE INDEX idx_calls_agent ON calls(agent_id);
CREATE INDEX idx_calls_ani ON calls(ani);
CREATE INDEX idx_calls_status ON calls(status);
CREATE INDEX idx_cases_investor ON cases(investor_id);
CREATE INDEX idx_cases_agent ON cases(agent_id);
CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_priority ON cases(priority);
CREATE INDEX idx_cases_call ON cases(call_id);
CREATE INDEX idx_notes_case ON case_notes(case_id);
CREATE INDEX idx_history_case ON case_history(case_id);
CREATE INDEX idx_breaches_case ON sla_breaches(case_id);
CREATE INDEX idx_escalations_case ON escalations(case_id);
CREATE INDEX idx_qa_agent ON qa_evaluations(agent_id);
CREATE INDEX idx_qa_case ON qa_evaluations(case_id);
""")

cx.commit()
cx.close()

print(f"""
✅ CX Intelligent Layer Generated Successfully!
──────────────────────────────────────────────
  CX Staff:       {AGENT_COUNT} agents + {SUPERVISOR_COUNT} supervisors + {QA_COUNT} QA + {ADMIN_COUNT} admins
  Calls:           {CALL_COUNT:,}
  CTI Events:      {event_id - 1:,}
  Cases:           {CASE_COUNT:,}
  Case Notes:      {note_id - 1:,}
  Case History:    {history_id - 1:,}
  SLA Breaches:    {breach_id - 1:,}
  Escalations:     {esc_id - 1:,}
  QA Evaluations:  {eval_id - 1:,}
""")
