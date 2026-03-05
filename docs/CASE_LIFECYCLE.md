# Case Lifecycle & Status Transitions

This document defines the six case statuses, the valid transitions between them, SLA implications, and who can perform each action.

---

## Team Structure — Tier 1 & Tier 2

The contact center operates on a two-tier model. Every CX user is assigned a `tier` value in the `cx_users` table.

### Tier 1 — Front-line Agents (`agent` role, 50 agents)

- Handle all incoming customer calls routed from the Cisco IVR/ACD
- Create cases, perform first-level troubleshooting, update case status
- Can escalate to Tier 2 when the issue exceeds their scope
- Cannot view escalation queue or SLA monitor (T2+ only)
- Typical issues: password resets, statement requests, basic billing questions

### Tier 2 — Senior Agents, Team Leads, Supervisors & Specialists

| Role | System Role | Count | Responsibilities |
|------|-------------|-------|------------------|
| Senior Agent | `senior_agent` | 10 | Handle escalated cases requiring deeper expertise — trading disputes, settlement issues, regulatory concerns |
| Team Lead | `team_lead` | 5 | Manage a squad of ~10 agents, monitor team SLA, reassign cases, review escalations, real-time queue oversight |
| Supervisor | `supervisor` | 12 | Operations oversight across teams, receive escalations, review SLA breaches, approve case closures, simulate calls |
| QA Analyst | `qa_analyst` | 8 | Evaluate call/case handling quality, score agents on criteria (greeting, empathy, resolution, compliance) |
| Admin | `admin` | 3 | System administration, user management, full platform access |

### UI Panel Differences

Each role sees a different sidebar panel reflecting their responsibilities:

| Feature | Agent (`agent`) | Senior Agent (`senior_agent`) | Team Lead (`team_lead`) | Supervisor (`supervisor`) |
|---------|----------------|------------------------------|------------------------|--------------------------|
| Dashboard | Yes | Yes | Yes | Yes |
| My Cases / All Cases | My Cases | My Cases | All Cases | All Cases |
| New Case | Yes | Yes | Yes | Yes |
| Outbound Queue | Yes | Yes | Yes | Yes |
| Escalations Queue | — | Yes | Yes | Yes |
| SLA Monitor | — | Yes | Yes | Yes |
| Reports | — | — | Yes | Yes |
| Team View | — | — | Yes | Yes |
| Investor Lookup | Yes | Yes | Yes | Yes |
| Simulate Call | — | — | — | Yes |

The sidebar badge shows the role label: **"Agent"**, **"Senior Agent"**, **"Team Lead"**, **"Supervisor"**, **"QA Analyst"**, or **"Administrator"**.

### Demo Logins

| Username | Password | System Role | Tier | Label |
|----------|----------|-------------|------|-------|
| `agent11` | `agent123` | `agent` | Tier 1 | Agent |
| `agent1` | `agent123` | `senior_agent` | Tier 2 | Senior Agent |
| `tl1` | `lead123` | `team_lead` | Tier 2 | Team Lead |
| `supervisor1` | `super123` | `supervisor` | Tier 2 | Supervisor |
| `qa1` | `qa1234` | `qa_analyst` | Tier 2 | QA Analyst |
| `admin1` | `admin123` | `admin` | Tier 2 | Administrator |

### Team Lead — Role & Responsibilities

The Team Lead sits between front-line agents and operations supervisors. Each team lead manages a squad of approximately 10 agents.

**Day-to-day responsibilities:**

1. **Case oversight** — Monitor all team cases, update or reassign as needed
2. **Escalation triage** — Review escalated cases, pick up or route to T2 specialists
3. **SLA monitoring** — Watch for approaching SLA breaches and intervene before they occur
4. **Team reporting** — Access Reports and Team views for performance tracking
5. **QA review** — Read QA evaluations for their agents (read-only, cannot evaluate)
6. **Investor lookup** — Access investor data for case review (supervisor-level field visibility)

**What team leads cannot do:**

- Simulate incoming calls (supervisor/admin only)
- Create or modify QA scorecards or evaluations
- Manage users or access audit logs
- Export reports

**Org hierarchy:**

```
T1 Agent → Team Lead → Supervisor → Admin
                ↑
           5 TLs, each managing ~10 agents
```

### Escalation Path

When a Tier 1 agent escalates a case, the system:

1. Sets the case status to `escalated`
2. Creates an escalation record with the reason, source agent, and target
3. Auto-assigns to a random active **supervisor** (or a T2 agent can pick it up)
4. Logs the transition in `case_history` (`from_tier: tier1 → to_tier: tier2`)

```
Customer Call → T1 Agent → [cannot resolve] → Escalate → T2 Agent / Supervisor → Resolve
```

The `tier` field is stored on each user and determines which escalation rules apply. The `escalation_rules` table defines three triggers:

| Rule | Trigger | From | To | Alert Channels |
|------|---------|------|----|----------------|
| T1→T2 SLA breach | `sla_breach` | tier1 | tier2 | email, slack |
| T1→T2 Critical | `priority=critical` | tier1 | tier2 | email, slack, sms |
| T1→T2 Manual | `manual` | tier1 | tier2 | email |

---

## Status Definitions

| Status | Label | Description |
|--------|-------|-------------|
| `open` | Open | Case has been created but no agent has started working on it. SLA first-response timer is running. |
| `in_progress` | In Progress | An agent is actively working the case. First response has been recorded. |
| `pending_customer` | Pending Customer | Agent is waiting on the customer (documents, callback, confirmation). SLA clock may pause depending on policy. |
| `escalated` | Escalated | Case has been transferred from Tier 1 to Tier 2 (supervisor or senior agent). An escalation record is created with a reason. |
| `resolved` | Resolved | The issue has been addressed. The case enters a review window — QA evaluation, customer confirmation, or supervisor sign-off may still occur. The `resolved_at` timestamp is recorded. |
| `closed` | Closed | Terminal state. The case is fully complete. The `closed_at` timestamp is recorded. No further transitions are allowed. |

---

## Transition Map

```
                    ┌──────────────────┐
                    │       open       │
                    └──┬───────────┬───┘
                       │           │
               ┌───────▼──┐       │
               │in_progress│◄─────┼──────────────────────┐
               └┬──┬──┬───┘      │                       │
                │  │  │          │                       │
    ┌───────────▼┐ │ ┌▼────────────┐                    │
    │  pending_   │ │ │  escalated  │                    │
    │  customer   │ │ └──────┬──────┘                    │
    └──────┬──────┘ │        │                           │
           │        │        │                           │
           └────────┼────────┘                           │
                    │                                    │
               ┌────▼─────┐                              │
               │ resolved  ├──────────────────────────────┘
               └────┬──────┘        (reopen)
                    │
               ┌────▼──────┐
               │  closed    │  ← terminal, no transitions out
               └────────────┘
```

### Valid Transitions Table

| From | Allowed Next Statuses | Notes |
|------|----------------------|-------|
| `open` | `in_progress`, `escalated`, `closed` | Agent picks up the case, or it gets immediately escalated/closed |
| `in_progress` | `pending_customer`, `escalated`, `resolved`, `closed` | Normal working state with all forward paths |
| `pending_customer` | `in_progress`, `escalated`, `resolved`, `closed` | Customer responded → resume, or resolve directly |
| `escalated` | `in_progress`, `resolved`, `closed` | T2 agent picks it up, resolves, or closes |
| `resolved` | `in_progress`, `closed` | Reopen if issue recurs, or close after confirmation |
| `closed` | *(none — terminal)* | Final state. No further transitions allowed |

### Invalid Transitions (rejected with HTTP 422)

Any transition not listed above is rejected. Common examples:

- `closed` → anything (terminal state)
- `open` → `resolved` (must go through `in_progress` first)
- `open` → `pending_customer` (must be in progress before waiting on customer)
- `resolved` → `escalated` (reopen to `in_progress` first, then escalate)

---

## Lifecycle Examples

### Example 1: Standard Resolution (happy path)

A customer calls about an incorrect charge. The agent handles it and resolves it.

```
open → in_progress → resolved → closed
```

| Step | Action | Who | Timestamp |
|------|--------|-----|-----------|
| 1 | Case created from incoming call | System | `created_at` |
| 2 | Agent picks up the case | Agent | `first_response_at` set |
| 3 | Agent investigates and fixes the issue | Agent | Notes added |
| 4 | Agent marks as resolved | Agent | `resolved_at` set |
| 5 | QA reviews, supervisor confirms, case closed | Supervisor/System | `closed_at` set |

### Example 2: Escalation Flow

A customer has a complex trading dispute that requires Tier 2 expertise.

```
open → in_progress → escalated → in_progress → resolved → closed
```

| Step | Action | Who |
|------|--------|-----|
| 1 | Case created | System |
| 2 | T1 agent starts working | T1 Agent |
| 3 | Agent escalates — reason: "Complex trading dispute, needs T2" | T1 Agent |
| 4 | T2 agent/supervisor picks up the case | T2 Agent |
| 5 | Issue resolved after back-office review | T2 Agent |
| 6 | Case closed | Supervisor |

### Example 3: Pending Customer

Agent needs additional documents from the customer before proceeding.

```
open → in_progress → pending_customer → in_progress → resolved → closed
```

| Step | Action | Who |
|------|--------|-----|
| 1 | Case created | System |
| 2 | Agent starts working | Agent |
| 3 | Agent requests KYC documents from customer | Agent |
| 4 | Customer provides documents, agent resumes | Agent |
| 5 | Issue resolved | Agent |
| 6 | Case closed | Supervisor |

### Example 4: Reopen After Resolution

Customer calls back saying the issue wasn't actually fixed.

```
open → in_progress → resolved → in_progress → resolved → closed
```

| Step | Action | Who |
|------|--------|-----|
| 1–4 | Normal flow through to resolved | Agent |
| 5 | Customer calls back — issue recurred | Agent reopens |
| 6 | Agent re-investigates and applies permanent fix | Agent |
| 7 | Resolved again, then closed | Agent/Supervisor |

### Example 5: Immediate Close

Duplicate case or test case — closed without working it.

```
open → closed
```

---

## Resolution Codes

When resolving a case, agents **must** select a resolution code. This enables root cause analysis, quality tracking, and accurate FCR measurement.

| Code | Label | Description |
|------|-------|-------------|
| `fixed` | Fixed | The issue was identified and corrected |
| `information_provided` | Information Provided | Customer query answered, no action needed |
| `account_updated` | Account Updated | Profile, KYC, or account settings changed per request |
| `duplicate` | Duplicate | Duplicate of an existing case |
| `cannot_reproduce` | Cannot Reproduce | Reported issue could not be replicated |
| `referred_third_party` | Referred to Third Party | Issue requires action by an external party |
| `customer_withdrew` | Customer Withdrew | Customer no longer requires assistance |
| `wont_fix` | Won't Fix | Issue acknowledged but no resolution planned |

Attempting to set `status: "resolved"` without a `resolution_code` returns HTTP 422.

---

## Case Reassignment

When a T2 agent or supervisor picks up an escalated case (moves `escalated → in_progress`), the system **automatically reassigns** the case:

1. The `agent_id` field updates to the T2 agent who picked it up
2. A `case_history` entry records the `agent_id` change (old → new)
3. Subsequent reports attribute the case to the agent who resolved it

Manual reassignment is also available via `POST /api/cases/{case_id}/reassign` (supervisors and admins only). T1 agents cannot reassign cases.

---

## SLA Implications

Each case has an SLA policy based on its priority level:

| Priority | First Response | Resolution Time |
|----------|---------------|-----------------|
| Critical | 15 minutes | 2 hours |
| High | 30 minutes | 4 hours |
| Medium | 1 hour | 8 hours |
| Low | 2 hours | 24 hours |

**SLA Breach Types:**

- **First Response Breach** — `first_response_at - created_at` exceeds the policy threshold. Checked when a case moves out of `open`.
- **Resolution Breach** — `resolved_at - created_at` exceeds the policy threshold. Checked when a case reaches `resolved`.

**SLA Pause on Pending Customer:**

When a case enters `pending_customer` status, the SLA resolution clock **pauses**. The system tracks:

- `pending_since` — timestamp when the case entered `pending_customer`
- `pending_seconds` — cumulative seconds spent waiting for the customer

When the case leaves `pending_customer`, the elapsed time is added to `pending_seconds` and `pending_since` is cleared. Multiple pending periods accumulate correctly.

The effective resolution time (for SLA purposes) is: `(resolved_at - created_at) - pending_seconds`.

SLA breaches are recorded in the `sla_breaches` table and trigger escalation rules when configured.

---

## Permissions by Role

| Action | Agent (T1) | Senior Agent (T2) | Team Lead | Supervisor | QA Analyst | Admin |
|--------|------------|-------------------|-----------|------------|------------|-------|
| Create case | Yes | Yes | Yes | Yes | No | Yes |
| Update own case | Yes | Yes | Yes | Yes | No | Yes |
| Update any case | No | No | Yes | Yes | No | Yes |
| Escalate own case | Yes | Yes | Yes | Yes | No | Yes |
| Escalate any case | No | No | Yes | Yes | No | Yes |
| Reassign case | No | Yes | Yes | Yes | No | Yes |
| Add notes | Own cases | Own cases | Any case | Any case | Any case | Any case |
| View escalation queue | No | Yes | Yes | Yes | Yes | Yes |
| View SLA monitor | No | Yes | Yes | Yes | Yes | Yes |
| View org reports | No | Yes | Yes | Yes | Yes | Yes |
| View own performance | Yes (dashboard) | Yes (dashboard) | — | — | — | — |
| Export reports | No | No | No | Yes | No | Yes |
| View team performance | No | No | Yes | Yes | No | Yes |
| View QA evaluations | Own cases | Own cases | Yes (read) | No | Yes | Yes |
| Request approval | Yes | Yes | Yes | No | No | Yes |
| Review approval | No | No | Yes | Yes | No | Yes |
| Knowledge base | Yes | Yes | Yes | Yes | No | Yes |
| Simulate calls | No | No | No | Yes | No | Yes |
| User management | No | No | No | No | No | Yes |
| Audit logs | No | No | No | No | No | Yes |

---

## API Endpoints

### Check Valid Transitions

```
GET /api/cases/{case_id}/transitions
```

**Response:**
```json
{
  "current_status": "in_progress",
  "allowed": ["closed", "escalated", "pending_customer", "resolved"]
}
```

### Update Case Status

```
PATCH /api/cases/{case_id}
```

**Request (resolving with code):**
```json
{
  "status": "resolved",
  "resolution_code": "fixed"
}
```

**Success (200):** Returns the updated case object with `resolved_at` timestamp and `resolution_code` set.

**Invalid Transition (422):**
```json
{
  "detail": "Invalid transition: closed → in_progress. Allowed: none (terminal)"
}
```

**Missing Resolution Code (422):**
```json
{
  "detail": "resolution_code is required when resolving a case. Valid codes: account_updated, cannot_reproduce, customer_withdrew, duplicate, fixed, information_provided, referred_third_party, wont_fix"
}
```

**Missing Verification (422):**
```json
{
  "detail": "Verification required: link a passed verification session before moving an investor case out of 'open'."
}
```

### Reassign Case

```
POST /api/cases/{case_id}/reassign
```

**Request:**
```json
{
  "agent_id": 5
}
```

**Access:** Supervisors and admins only. T1 agents are blocked. Records an `agent_id` change in `case_history`.

---

## Audit Trail

Every status change is recorded in two places:

1. **`case_history`** — Field-level audit showing old value, new value, who changed it, and when.
2. **`audit_logs`** — System-wide audit log with user ID, action, resource, and IP address.

Both are immutable and queryable for regulatory compliance.

---

## Comparison with Industry-Standard Ticketing Systems

### Status Mapping

| MCDR CX | Zendesk | Freshdesk | ServiceNow | ITIL |
|---------|---------|-----------|------------|------|
| `open` | New | Open | New | Logged |
| — | Open (assigned) | — | Assigned | Assigned |
| `in_progress` | Open (working) | Open | In Progress | In Progress |
| `pending_customer` | Pending | Pending | Awaiting User Info | Pending |
| — | On-hold | — | Awaiting Vendor / Change | On Hold |
| `escalated` | — (internal tag) | — (internal tag) | — (reassignment) | Escalated |
| `resolved` | Solved | Resolved | Resolved | Resolved |
| `closed` | Closed | Closed | Closed | Closed |
| — | — | — | Cancelled | Cancelled |

### What MCDR Does Differently

**1. Escalation as a first-class status**

Most ticketing systems (Zendesk, Freshdesk, ServiceNow) treat escalation as an internal action — reassigning the ticket to another group or adding a tag. The ticket stays "Open" or "In Progress."

MCDR promotes `escalated` to a dedicated status because the MCDR operates in a regulated financial environment where escalation is an auditable event. Every escalation records:
- Source agent (T1) and target agent (T2/supervisor)
- Reason for escalation
- Tier transition (`tier1 → tier2`)
- Timestamp and audit trail

This gives supervisors a filtered view of all escalated cases and enables SLA breach tracking specifically for escalation response time.

**2. No "New → Assigned" split**

Zendesk distinguishes between "New" (unread) and "Open" (assigned to agent). ServiceNow has both "New" and "Assigned." MCDR combines these into a single `open` status because cases in this system are typically created by the agent handling the call — the case is implicitly assigned at creation via `agent_id`. There is no unassigned queue.

**3. No "On-hold" or "Awaiting Vendor" status**

ServiceNow offers multiple "awaiting" substates (Awaiting User Info, Awaiting Change, Awaiting Vendor, Awaiting Problem). MCDR has a single `pending_customer` status. If a future need arises for vendor or internal holds, this could be extended.

**4. No "Cancelled" status**

Zendesk and ServiceNow allow cancelling tickets (duplicates, false reports). MCDR uses `open → closed` for this — a case can be immediately closed from open with a note explaining the reason (e.g. "Duplicate of CAS-001234").

**5. Resolved vs Closed — two-step closure**

This matches Zendesk and ServiceNow exactly:

| System | Resolved | Closed | Auto-close? |
|--------|----------|--------|-------------|
| **MCDR** | Agent marks resolved, QA review window | Manual close by agent/supervisor | No |
| **Zendesk** | Agent marks "Solved" | System auto-closes after 4 days | Yes (configurable) |
| **Freshdesk** | Agent marks "Resolved", reopens if customer replies | Manual or auto-close | Optional |
| **ServiceNow** | Agent marks "Resolved" | Auto-closes after confirmation period | Yes (configurable) |

MCDR currently requires manual closure. Auto-close after a configurable period could be added as an enhancement.

**6. SLA enforcement at the status level**

All systems tie SLA to status transitions. MCDR's approach is closest to ServiceNow:

| SLA Event | MCDR | Zendesk | ServiceNow |
|-----------|------|---------|------------|
| First response timer starts | Case created (`open`) | Ticket created (New) | Incident logged (New) |
| First response timer stops | Status leaves `open` | First public agent reply | Status changes to In Progress |
| Resolution timer starts | Case created | Ticket created | Incident logged |
| Resolution timer stops | Status reaches `resolved` | Status reaches Solved | Status reaches Resolved |
| SLA pause on pending | Yes (`pending_seconds` accumulates) | Yes (Pending pauses SLA) | Yes (On Hold pauses SLA) |

MCDR pauses the SLA resolution timer when a case is in `pending_customer` status, tracking cumulative pause time in the `pending_seconds` field.

### Summary

MCDR's lifecycle is lean (6 statuses vs ServiceNow's 9+) while covering the core CX workflow. The key differentiator is **escalation as an auditable status** rather than an internal reassignment, which is important for regulated financial services where every handoff must be traceable. The system is closest in philosophy to **Freshdesk** (simple, 4-core-status model) with the escalation rigor of **ServiceNow**.

---

## Business Hours & Operating Model

The CX unit operates **Sunday through Thursday, 09:00–22:00** (Egypt business days).

**Data Constraints:**
- All mock data (cases, calls, escalations) is generated within business hours only
- No cases are created on Friday or Saturday (Egyptian weekend)
- Each case has a unique call link (no duplicate `call_id` references)

---

## Outbound Support Module

The outbound module supports four structured task types, each logged as a case-linked record:

| Task Type | Description | Typical Trigger |
|-----------|-------------|-----------------|
| `broken_signup` | Recover users who abandoned the registration flow | App analytics: incomplete sign-ups |
| `inactive_user` | Re-engage dormant accounts | No login for 60–90+ days |
| `transaction_verification` | Verbal confirmation for flagged transactions | Compliance rules on large/unusual trades |
| `qa_callback` | Post-resolution satisfaction follow-up | QA sampling or investor request |

### Task Lifecycle

`pending` → `in_progress` → `completed` / `failed` / `cancelled`

Each task records: agent assignment, investor link, priority, scheduled time, attempt time, completion time, and outcome notes.

### API

- `GET /outbound` — list tasks (filter by status, type, agent)
- `GET /outbound/stats` — volume by status & type
- `POST /outbound` — create task
- `PATCH /outbound/{id}` — pick up, complete, or fail

---

## Identity Verification Protocol

Before handling a case, agents must verify the caller's identity using a structured 4-step protocol.

### Verification Steps

1. **Full Name** — Ask the caller to state their full name
2. **National ID** — Ask for the last 4 digits of their National ID
3. **Mobile Number** — Confirm the registered mobile number
4. **Account Status** — Confirm account activity details

### Verification Methods

| Method | Description |
|--------|-------------|
| `verbal` | Agent asks security questions over the phone (default) |
| `otp` | One-time password sent to registered mobile |
| `document` | Document upload verification |

### Verification Lifecycle

`pending` → `in_progress` → `passed` / `failed`

- Sessions auto-complete when all 4 steps are marked (pass or fail)
- If any step fails, the session status becomes `failed`
- Passed sessions are linked to the case via `verification_id`

### Enforcement Rules

1. **Mandatory for case progression** — A case with an `investor_id` cannot move from `open` → `in_progress` without a linked, passed verification session. The system returns HTTP 422 if:
   - No `verification_id` is linked to the case
   - The linked session status is not `passed` or `verified`
   - The linked session has expired (past `expires_at`)

2. **Link-time validation** — Only `passed` or `verified` sessions can be linked to a case. Expired sessions cannot be linked.

3. **Session expiry** — Verification sessions expire 30 minutes after creation (`expires_at`). Expired sessions must be replaced with a new verification.

4. **Unidentified callers** — Cases without an `investor_id` (walk-in, unidentified) bypass verification enforcement.

### Integration Points

- **IncomingCall** — "Verify Caller Identity" button appears after accepting a call
- **CaseDetail** — Verification wizard in the sidebar shows status and step-by-step progress
- **Audit** — Every step and status change is audit-logged

### API

- `POST /verification/start` — start a new verification session
- `GET /verification/{id}` — get session details
- `PATCH /verification/{id}/step` — mark a step as passed/failed
- `PATCH /verification/{id}/complete` — manually complete/fail
- `POST /verification/{id}/link` — link to a case
- `GET /verification/case/{case_id}` — get verification for a case

---

## Operations Report

The reports module provides a KPI dashboard covering the proposal's Track 2 requirements.

### KPIs

| KPI | Source | Description |
|-----|--------|-------------|
| FCR % | `escalations` table | Cases resolved without any escalation record |
| AHT (min) | `calls.duration_seconds` | Average handling time for completed calls |
| Escalation Rate % | `escalations` table | Percentage of cases that were ever escalated (not just current status) |
| Reopen Rate % | `case_history` | Cases reopened after resolution (`resolved → in_progress`) |
| Verification Pass Rate % | `verification_sessions` | Identity verification success rate |
| SLA Compliance % | `sla_breaches` vs `cases` | Per-policy compliance (average of FRT + Resolution met rates) |

### Report Sections

1. **Case Volume** — daily breakdown (total, active, resolved, escalated)
2. **SLA Compliance** — per-policy compliance with breach counts
3. **Category Breakdown** — case volume by taxonomy category with resolution rates
4. **Resolution Codes** — breakdown of how cases were resolved (fixed, duplicate, etc.)
5. **Agent Performance** — top agents ranked by cases handled, resolution time, QA score

### Access

- Supervisors and admins see the Reports page in the sidebar
- All data is filterable by period (7 / 14 / 30 / 90 days)
- CSV export available for offline analysis

### API

- `GET /cx/reports/overview?days=30` — full report payload
