"""Operational test suite — verifies business logic, role guards, and data integrity."""

import json
import time
import requests

BASE = "http://localhost:8100/api"
PASS = 0
FAIL = 0
ERRORS = []


def login(username, password):
    r = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def api(method, path, token, body=None, expect=None):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    r = requests.request(method, f"{BASE}{path}", headers=headers, json=body)
    return r


def check(desc, r, expect_code):
    global PASS, FAIL
    ok = r.status_code == expect_code
    tag = "PASS" if ok else "FAIL"
    if ok:
        PASS += 1
    else:
        FAIL += 1
        detail = ""
        try:
            detail = r.json().get("detail", "")[:80]
        except Exception:
            pass
        ERRORS.append(f"  {desc}: expected {expect_code}, got {r.status_code} {detail}")
    print(f"  {tag}: {desc} (got {r.status_code})")
    return r


def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# ─── Auth ────────────────────────────────────────────────────────
section("1. AUTH & ROLE VERIFICATION")

tokens = {}
users = {}
logins = [
    ("agent11", "agent123", "agent", "tier1"),
    ("agent1", "agent123", "senior_agent", "tier2"),
    ("tl1", "lead123", "team_lead", "tier2"),
    ("supervisor1", "super123", "supervisor", "tier2"),
    ("qa1", "qa1234", "qa_analyst", "tier2"),
    ("admin1", "admin123", "admin", "tier2"),
]

for uname, pw, expected_role, expected_tier in logins:
    tok = login(uname, pw)
    tokens[expected_role] = tok
    me = api("GET", "/users/me", tok).json()
    users[expected_role] = me
    actual_role = me.get("role_name") or (me.get("role", {}) or {}).get("name")
    role_ok = actual_role == expected_role
    tier_ok = me.get("tier") == expected_tier
    if role_ok and tier_ok:
        PASS += 1
        print(f"  PASS: {uname} → role={actual_role}, tier={me['tier']}, id={me['id']}")
    else:
        FAIL += 1
        ERRORS.append(f"  {uname}: expected role={expected_role}/tier={expected_tier}, got {actual_role}/{me.get('tier')}")
        print(f"  FAIL: {uname} role/tier mismatch")


# ─── Permission Guards ───────────────────────────────────────────
section("2. PERMISSION GUARDS")

# T1 Agent
print("  --- T1 Agent ---")
check("T1 CAN create case", api("POST", "/cases", tokens["agent"], {"subject": "T1 test case", "priority": "low"}), 201)
check("T1 CAN read cases", api("GET", "/cases", tokens["agent"]), 200)
check("T1 CANNOT see escalation queue", api("GET", "/escalations/case/1", tokens["agent"]), 403)
check("T1 CANNOT see SLA breaches", api("GET", "/cx/sla/breaches/1", tokens["agent"]), 403)
check("T1 CANNOT see org reports", api("GET", "/cx/reports/overview", tokens["agent"]), 403)
check("T1 CANNOT access audit", api("GET", "/audit/logs", tokens["agent"]), 403)
check("T1 CANNOT manage users", api("GET", "/users", tokens["agent"]), 403)
check("T1 CAN read KB", api("GET", "/cx/kb", tokens["agent"]), 200)
check("T1 CAN read own QA", api("GET", f"/cx/qa/agent/{users['agent']['id']}", tokens["agent"]), 200)

# Senior Agent
print("  --- Senior Agent ---")
check("Senior CAN see escalation queue", api("GET", "/escalations/case/1", tokens["senior_agent"]), 200)
check("Senior CAN see SLA", api("GET", "/cx/sla/breaches/1", tokens["senior_agent"]), 200)
check("Senior CAN see reports", api("GET", "/cx/reports/overview", tokens["senior_agent"]), 200)
check("Senior CANNOT access audit", api("GET", "/audit/logs", tokens["senior_agent"]), 403)
check("Senior CANNOT manage users", api("GET", "/users", tokens["senior_agent"]), 403)

# QA Analyst
print("  --- QA Analyst ---")
check("QA CAN read cases", api("GET", "/cases", tokens["qa_analyst"]), 200)
check("QA CAN read SLA", api("GET", "/cx/sla/breaches/1", tokens["qa_analyst"]), 200)
check("QA CAN read escalations", api("GET", "/escalations/case/1", tokens["qa_analyst"]), 200)
check("QA CAN read QA evals", api("GET", "/cx/qa/leaderboard", tokens["qa_analyst"]), 200)
check("QA CANNOT create case", api("POST", "/cases", tokens["qa_analyst"], {"subject": "QA fail", "priority": "low"}), 403)

# Team Lead
print("  --- Team Lead ---")
check("TL CAN see presence", api("GET", "/cx/presence", tokens["team_lead"]), 200)
check("TL CAN read approvals", api("GET", "/approvals", tokens["team_lead"]), 200)
check("TL CANNOT access audit", api("GET", "/audit/logs", tokens["team_lead"]), 403)

# Supervisor
print("  --- Supervisor ---")
check("Sup CAN access reports", api("GET", "/cx/reports/overview", tokens["supervisor"]), 200)
check("Sup CANNOT access audit", api("GET", "/audit/logs", tokens["supervisor"]), 403)

# Admin
print("  --- Admin ---")
check("Admin CAN access audit", api("GET", "/audit/logs", tokens["admin"]), 200)
check("Admin CAN manage users", api("GET", "/users", tokens["admin"]), 200)


# ─── Case Lifecycle ──────────────────────────────────────────────
section("3. CASE LIFECYCLE — Create & Transitions")

# Create a case as senior agent (no investor, so no verification needed)
r = check("Create case", api("POST", "/cases", tokens["senior_agent"], {
    "subject": "Lifecycle test case",
    "priority": "medium",
}), 201)
case = r.json()
cid = case["case_id"]
print(f"    Created case {cid}, status={case['status']}")

# Check valid transitions from open
r = api("GET", f"/cases/{cid}/transitions", tokens["senior_agent"])
transitions = r.json()
print(f"    Valid from open: {transitions['allowed']}")

# Invalid transition: open → resolved (must go through in_progress)
check("BLOCKED: open → resolved", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {
    "status": "resolved", "resolution_code": "fixed"
}), 422)

# Invalid transition: open → pending_customer
check("BLOCKED: open → pending_customer", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {
    "status": "pending_customer"
}), 422)

# Valid: open → in_progress
check("open → in_progress", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "in_progress"}), 200)

# Valid: in_progress → pending_customer (SLA pause)
check("in_progress → pending_customer", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "pending_customer"}), 200)

# Check pending_since is set
c = api("GET", f"/cases/{cid}", tokens["senior_agent"]).json()
has_pending_since = c.get("pending_since") is not None
print(f"    pending_since set: {has_pending_since}")
if has_pending_since:
    PASS += 1
else:
    FAIL += 1
    ERRORS.append("  pending_since not set when entering pending_customer")

# Wait a moment for SLA accumulation
time.sleep(1)

# Resume: pending_customer → in_progress
check("pending_customer → in_progress", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "in_progress"}), 200)
c = api("GET", f"/cases/{cid}", tokens["senior_agent"]).json()
pending_secs = c.get("pending_seconds", 0)
print(f"    pending_seconds accumulated: {pending_secs}")
if pending_secs > 0:
    PASS += 1
else:
    FAIL += 1
    ERRORS.append(f"  pending_seconds should be > 0, got {pending_secs}")

# Resolve without resolution_code → should fail
check("BLOCKED: resolve without resolution_code", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "resolved"}), 422)

# Resolve with resolution_code
check("in_progress → resolved (with code)", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {
    "status": "resolved", "resolution_code": "fixed"
}), 200)

# Reopen: resolved → in_progress
check("resolved → in_progress (reopen)", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "in_progress"}), 200)

# Resolve again
check("re-resolve with code", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "resolved", "resolution_code": "information_provided"}), 200)

# Close
check("resolved → closed", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "closed"}), 200)

# Closed is terminal — no transitions out
check("BLOCKED: closed → in_progress", api("PATCH", f"/cases/{cid}", tokens["senior_agent"], {"status": "in_progress"}), 422)


# ─── Ownership Guards ────────────────────────────────────────────
section("4. OWNERSHIP GUARDS")

# Create a case as agent11 (T1)
r = api("POST", "/cases", tokens["agent"], {"subject": "Agent11 case", "priority": "low"})
a11_case = r.json()
a11_cid = a11_case["case_id"]

# Senior agent (agent1, id=1) should NOT be able to modify agent11's case
check("Senior CANNOT modify another agent's case", api("PATCH", f"/cases/{a11_cid}", tokens["senior_agent"], {"status": "in_progress"}), 403)

# Senior agent CANNOT add note to another agent's case
check("Senior CANNOT add note to other's case", api("POST", f"/cases/{a11_cid}/notes", tokens["senior_agent"], {"content": "should fail"}), 403)

# Team lead CAN modify any case
check("TL CAN modify any case", api("PATCH", f"/cases/{a11_cid}", tokens["team_lead"], {"status": "in_progress"}), 200)

# QA analyst CANNOT modify case fields
check("QA CANNOT modify case fields", api("PATCH", f"/cases/{a11_cid}", tokens["qa_analyst"], {"status": "resolved", "resolution_code": "fixed"}), 403)

# QA analyst CAN add notes to any case
check("QA CAN add note to any case", api("POST", f"/cases/{a11_cid}/notes", tokens["qa_analyst"], {"content": "QA observation note", "is_internal": True}), 201)

# T1 agent CANNOT reassign
check("T1 CANNOT reassign case", api("POST", f"/cases/{a11_cid}/reassign", tokens["agent"], {"agent_id": 1}), 403)

# Supervisor CAN reassign
check("Supervisor CAN reassign", api("POST", f"/cases/{a11_cid}/reassign", tokens["supervisor"], {"agent_id": 1}), 200)


# ─── Escalation Logic ────────────────────────────────────────────
section("5. ESCALATION LOGIC")

# Create a fresh case for escalation test
r = api("POST", "/cases", tokens["agent"], {"subject": "Escalation test", "priority": "high"})
esc_case = r.json()
esc_cid = esc_case["case_id"]

# Move to in_progress first
api("PATCH", f"/cases/{esc_cid}", tokens["agent"], {"status": "in_progress"})

# Agent escalates own case
check("Agent CAN escalate own case", api("POST", "/escalations", tokens["agent"], {
    "case_id": esc_cid, "reason": "Complex dispute, needs T2 expertise"
}), 201)

# Case should now be in escalated status
esc_updated = api("GET", f"/cases/{esc_cid}", tokens["admin"]).json()
if esc_updated["status"] == "escalated":
    PASS += 1
    print(f"  PASS: Case status is 'escalated'")
else:
    FAIL += 1
    ERRORS.append(f"  Case status should be escalated, got {esc_updated['status']}")

# Re-escalate blocked
check("BLOCKED: re-escalate already-escalated case", api("POST", "/escalations", tokens["admin"], {
    "case_id": esc_cid, "reason": "double escalate"
}), 409)


# ─── Approval Workflow ───────────────────────────────────────────
section("6. APPROVAL WORKFLOW")

# Create an approval request as agent
r = check("Agent creates approval", api("POST", "/approvals", tokens["agent"], {
    "case_id": 1, "approval_type": "refund", "description": "Overcharge reversal EGP 250", "amount": 250
}), 201)
appr = r.json()
appr_id = appr.get("approval_id")
print(f"    Approval #{appr_id}, status={appr.get('status')}")

# Pending count
r = api("GET", "/approvals/pending/count", tokens["team_lead"])
print(f"    Pending approvals: {r.json().get('count')}")

# TL approves
check("TL CAN approve", api("PATCH", f"/approvals/{appr_id}", tokens["team_lead"], {
    "decision": "approved", "notes": "Verified — within policy"
}), 200)

# Double-review blocked
check("BLOCKED: re-review approved request", api("PATCH", f"/approvals/{appr_id}", tokens["supervisor"], {
    "decision": "rejected", "notes": "too late"
}), 422)

# Create another and reject it
r2 = api("POST", "/approvals", tokens["senior_agent"], {
    "case_id": 2, "approval_type": "fee_waiver", "description": "Fee waiver for loyal customer", "amount": 50
})
appr2 = r2.json()
appr2_id = appr2.get("approval_id")
check("Supervisor rejects approval", api("PATCH", f"/approvals/{appr2_id}", tokens["supervisor"], {
    "decision": "rejected", "notes": "Insufficient documentation"
}), 200)


# ─── Agent Presence ──────────────────────────────────────────────
section("7. AGENT PRESENCE")

agent_id = users["agent"]["id"]
# Set presence
check("Agent sets own presence", api("PUT", f"/cx/presence/{agent_id}", tokens["agent"], {"status": "available"}), 200)

# Get presence
r = api("GET", f"/cx/presence/{agent_id}", tokens["agent"])
pres = r.json()
if pres.get("status") == "available":
    PASS += 1
    print(f"  PASS: Presence is 'available'")
else:
    FAIL += 1
    ERRORS.append(f"  Presence should be available, got {pres}")

# Change to on_break
check("Change to on_break", api("PUT", f"/cx/presence/{agent_id}", tokens["agent"], {"status": "on_break"}), 200)

# Invalid presence
check("BLOCKED: invalid presence status", api("PUT", f"/cx/presence/{agent_id}", tokens["agent"], {"status": "sleeping"}), 422)

# Presence summary
r = api("GET", "/cx/presence/summary", tokens["team_lead"])
summary = r.json()
print(f"    Presence summary: {summary}")

# Agent cannot change another agent's presence
senior_id = users["senior_agent"]["id"]
check("Agent CANNOT change other's presence", api("PUT", f"/cx/presence/{senior_id}", tokens["agent"], {"status": "offline"}), 403)

# TL CAN change another's presence
check("TL CAN change agent presence", api("PUT", f"/cx/presence/{agent_id}", tokens["team_lead"], {"status": "available"}), 200)


# ─── Knowledge Base ──────────────────────────────────────────────
section("8. KNOWLEDGE BASE")

r = api("GET", "/cx/kb", tokens["agent"])
articles = r.json()
print(f"    Total articles: {len(articles)}")
check("KB returns articles", r, 200)

r = api("GET", "/cx/kb/categories", tokens["agent"])
cats = r.json()
print(f"    Categories: {cats}")
check("KB categories", r, 200)

# Search
r = api("GET", "/cx/kb?search=refund", tokens["agent"])
found = r.json()
print(f"    Search 'refund': {len(found)} results")
if len(found) > 0:
    PASS += 1
else:
    FAIL += 1
    ERRORS.append("  KB search for 'refund' returned 0 results")

# Filter by category
r = api("GET", "/cx/kb?category=Billing", tokens["agent"])
billing = r.json()
print(f"    Category 'Billing': {len(billing)} articles")


# ─── QA Feedback Loop ────────────────────────────────────────────
section("9. QA FEEDBACK LOOP")

# Agent can see QA evals for a case they handled
# Find a case that agent1 (senior) handled and has QA evals
r = api("GET", "/cx/qa/agent/1", tokens["senior_agent"])
qa_summary = r.json()
print(f"    Agent1 QA summary: avg_score={qa_summary.get('avg_score')}, evals={qa_summary.get('total_evaluations')}")
check("Agent CAN read own QA summary", r, 200)

# Agent can read case QA evals
r = api("GET", "/cx/qa/case/1", tokens["agent"])
check("Agent CAN read case QA evals", r, 200)


# ─── Data Integrity ──────────────────────────────────────────────
section("10. DATA INTEGRITY")

import os
import pymysql
import pymysql.cursors
db = pymysql.connect(
    host=os.environ.get("MYSQL_HOST", "localhost"),
    port=int(os.environ.get("MYSQL_PORT", "3306")),
    user=os.environ.get("MYSQL_USER", "mcdr"),
    password=os.environ.get("MYSQL_PASSWORD", "mcdr_pass"),
    database="mcdr_cx",
    cursorclass=pymysql.cursors.DictCursor,
)
_db_cursor = db.cursor()

class _DBExec:
    def execute(self, sql, params=None):
        _db_cursor.execute(sql, params or ())
        return _db_cursor
    def close(self):
        db.close()

db = _DBExec()

# Role distribution
roles = db.execute("SELECT r.name, COUNT(*) as cnt FROM users u JOIN roles r ON u.role_id = r.id GROUP BY r.name ORDER BY cnt DESC").fetchall()
print("    Role distribution:")
for row in roles:
    print(f"      {row['name']}: {row['cnt']}")

# CX users match
cx_count = db.execute("SELECT COUNT(*) as cnt FROM cx_users").fetchone()["cnt"]
user_count = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
if cx_count == user_count:
    PASS += 1
    print(f"  PASS: cx_users ({cx_count}) == users ({user_count})")
else:
    FAIL += 1
    ERRORS.append(f"  cx_users ({cx_count}) != users ({user_count})")

# Case counts
case_count = db.execute("SELECT COUNT(*) as cnt FROM cases").fetchone()["cnt"]
print(f"    Cases: {case_count}")

# No orphan escalations (every escalation references a valid case)
orphan_esc = db.execute("SELECT COUNT(*) as cnt FROM escalations WHERE case_id NOT IN (SELECT case_id FROM cases)").fetchone()["cnt"]
if orphan_esc == 0:
    PASS += 1
    print(f"  PASS: No orphan escalations")
else:
    FAIL += 1
    ERRORS.append(f"  {orphan_esc} orphan escalations")

# No orphan QA evals
orphan_qa = db.execute("SELECT COUNT(*) as cnt FROM qa_evaluations WHERE case_id NOT IN (SELECT case_id FROM cases)").fetchone()["cnt"]
if orphan_qa == 0:
    PASS += 1
    print(f"  PASS: No orphan QA evaluations")
else:
    FAIL += 1
    ERRORS.append(f"  {orphan_qa} orphan QA evaluations")

# All cases have valid agent_id
invalid_agent = db.execute("SELECT COUNT(*) as cnt FROM cases WHERE agent_id NOT IN (SELECT user_id FROM cx_users)").fetchone()["cnt"]
if invalid_agent == 0:
    PASS += 1
    print(f"  PASS: All cases have valid agent_id")
else:
    FAIL += 1
    ERRORS.append(f"  {invalid_agent} cases with invalid agent_id")

# Presence data covers all agent/senior_agent users
agent_count = db.execute("SELECT COUNT(*) as cnt FROM cx_users WHERE role IN ('agent', 'senior_agent')").fetchone()["cnt"]
presence_count = db.execute("SELECT COUNT(*) as cnt FROM agent_presence ap JOIN cx_users cu ON ap.agent_id = cu.user_id WHERE cu.role IN ('agent', 'senior_agent')").fetchone()["cnt"]
if presence_count >= agent_count:
    PASS += 1
    print(f"  PASS: Presence covers all agents ({presence_count}/{agent_count})")
else:
    FAIL += 1
    ERRORS.append(f"  Presence: only {presence_count}/{agent_count} agents have presence data")

# KB articles
kb_count = db.execute("SELECT COUNT(*) as cnt FROM kb_articles WHERE is_published = 1").fetchone()["cnt"]
print(f"    KB articles: {kb_count}")

# Approvals
appr_counts = db.execute("SELECT status, COUNT(*) as cnt FROM approvals GROUP BY status").fetchall()
print(f"    Approvals: {dict((r['status'], r['cnt']) for r in appr_counts)}")

db.close()


# ─── Final Report ────────────────────────────────────────────────
section("FINAL REPORT")
total = PASS + FAIL
print(f"\n  Results: {PASS} passed, {FAIL} failed out of {total} checks")
print(f"  Pass rate: {PASS/total*100:.1f}%")

if ERRORS:
    print(f"\n  FAILURES:")
    for e in ERRORS:
        print(f"    {e}")
else:
    print("\n  ALL CHECKS PASSED")

print()
