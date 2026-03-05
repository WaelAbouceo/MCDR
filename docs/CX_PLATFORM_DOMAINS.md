# MCDR CX Platform — Domain Coverage

> **Positioning:** Cisco handles telephony and routing, while the MCDR CX Platform manages the full customer interaction lifecycle including cases, SLA, escalation, QA, audit, and investor lookup — purpose-built for Egyptian capital market regulation.

---

## Platform Overview

In a Cisco Contact Center environment, the CX platform sits between telephony and business data, managing the customer interaction lifecycle. Enterprise equivalents include Salesforce Service Cloud, Microsoft Dynamics 365, Zendesk, and ServiceNow CSM.

The MCDR CX Platform is a **custom-built alternative** with advantages for a regulated financial infrastructure entity:

| Advantage | Description |
|-----------|-------------|
| **Data sovereignty** | All investor data stays on-premise within MCDR's infrastructure |
| **Regulatory control** | Audit trail, field masking, and RBAC designed for FRA/EGX compliance |
| **Integration flexibility** | Direct integration with Core Registry and Mobile App backend |
| **Cost efficiency** | No per-seat SaaS licensing; internal development and maintenance |

---

## 8 CX Platform Domains

### 1. Telephony Integration Layer

**Purpose:** Integrate with Cisco call infrastructure for screen-pop, call logging, and agent state management.

**Cisco Stack:**
- Cisco Unified Contact Center Enterprise (UCCE)
- Cisco Finesse (Agent Desktop)
- Cisco Unified Communications Manager (CUCM)

**CTI Events Supported:**

| Event | Implementation | Effect |
|-------|---------------|--------|
| `call_offered` | `src/services/call_simulator.py` | Screen-pop pushed to agent console |
| `call_answered` | `src/models/telephony.py` | Call timer starts, case creation enabled |
| `call_held` | CTI event model + mock data | Hold metrics tracked |
| `call_resumed` | CTI event model + mock data | Hold duration calculated |
| `call_ended` | CTI event model + mock data | Call logged, wrap-up (ACW) begins |
| `call_transferred` | CTI event model | Transfer chain tracked |
| `agent_ready` | Agent presence API | ACD availability updated |
| `agent_not_ready` | Agent presence API | Agent removed from queue |

**Implementation:**

| Layer | File | Key Functions |
|-------|------|--------------|
| API | `src/api/simulate.py` | `simulate_call()`, `check_incoming()`, `accept_call()`, `dismiss_call()` |
| API | `src/api/telephony.py` | `create_call()`, `record_event()`, `get_screen_pop()` |
| Service | `src/services/call_simulator.py` | `simulate_incoming_call()`, `push_incoming_call()`, `poll_incoming_call()` |
| Service | `src/services/cti_service.py` | `build_screen_pop()` |
| Frontend | `IncomingCall.jsx` | Accept/decline, screen-pop display, investor details, risk flags |
| Frontend | `Layout.jsx` | 3-second polling for incoming calls, presence status picker |
| DB | `mcdr_cx.db` | `calls`, `cti_events` |

**Screen-Pop Payload:**
```
call_id, ANI, queue, call_reason
investor profile (name, code, account status, type)
app user (mobile, email, OTP status, last login)
portfolio summary (positions, total value, sectors)
open cases + recent cases
recent calls
risk flags (SUSPENDED, DORMANT, LOCKED, FREQUENT_CALLER, etc.)
```

**Current State:** Telephony is fully simulated. In production, replace the simulator with a real Cisco CTI adapter (JTAPI/REST) that fires the same events.

---

### 2. Customer Data Lookup

**Purpose:** Instantly retrieve investor profile, portfolio, and history when a call arrives.

**Lookup Methods:**

| Method | Endpoint | Source |
|--------|----------|--------|
| Mobile number (ANI) | `GET /api/registry/app-users/by-mobile/{mobile}` | `mcdr_mobile.db → app_users` |
| Investor code | `GET /api/registry/investors/by-code/{code}` | `mcdr_core.db → investors` |
| National ID | `GET /api/registry/investors?national_id=...` | `mcdr_core.db → investors` |
| Investor ID | `GET /api/registry/investors/{id}` | `mcdr_core.db → investors` |

**Data Flow:**
```
Call arrives → ANI detected → Mobile App DB lookup → investor_id
    → Core Registry: investor profile + account status
    → Core Registry: holdings + securities → portfolio summary
    → CX DB: open cases + recent calls
    → Risk flags computed
    → Screen-pop assembled → pushed to agent console
```

**Implementation:**

| Layer | File | Key Functions |
|-------|------|--------------|
| API | `src/api/registry.py` | `get_investor()`, `search_investors()`, `get_holdings()`, `get_portfolio()` |
| Service | `src/services/registry_service.py` | `get_full_investor_profile()`, `get_app_user_by_mobile()` |
| Middleware | `src/middleware/field_mask.py` | Role-based field filtering |
| Frontend | `InvestorSearch.jsx` | Search, profile, holdings, create case |
| DB | `mcdr_core.db` | `investors` (50K), `securities` (250), `holdings` |
| DB | `mcdr_mobile.db` | `app_users` (~30K) |

**Data Zone Isolation:** Core Registry and Mobile App databases are read-only from the CX platform. Customer PII is physically separated with field-level masking per role.

---

### 3. Case Management Engine

**Purpose:** Manage the entire lifecycle of customer issues from call to closure.

**Status Workflow:**
```
open → in_progress → pending_customer → in_progress → resolved → closed
                   → escalated → in_progress → resolved → closed
```

**Features:**

| Feature | Implementation | Endpoint |
|---------|---------------|----------|
| Case creation | Agent creates during/after call | `POST /api/cases` |
| Auto-numbering | `CAS-XXXXXX` sequential | `cx_data_service.create_case()` |
| Assignment | Auto-assigned to creator | `agent_id` set on create |
| Reassignment | Team lead/supervisor/admin | `POST /api/cases/{id}/reassign` |
| Status transitions | Validated state machine | `PATCH /api/cases/{id}` |
| Valid transitions | Dynamic per current status | `GET /api/cases/{id}/transitions` |
| Notes | Agent documentation (internal/external) | `POST /api/cases/{id}/notes` |
| History | Field-level change tracking | `case_history` table |
| Resolution codes | Structured closure reasons | 8 codes: fixed, duplicate, info_provided, etc. |
| Priority levels | low, medium, high, critical | Affects SLA timers |
| Taxonomy | Category/subcategory classification | `case_taxonomy` table |
| Ownership guard | Agents can only modify their own cases | IDOR protection |

**Implementation:**

| Layer | File |
|-------|------|
| API | `src/api/cases.py` — 7 endpoints |
| Service | `src/services/cx_data_service.py` — `create_case()`, `update_case()`, `reassign_case()`, `add_case_note()` |
| Async | `src/services/async_cx.py` — thread-safe wrapper |
| Frontend | `CaseList.jsx`, `CaseDetail.jsx`, `CreateCase.jsx` |
| DB | `cases`, `case_notes`, `case_history`, `case_taxonomy` |

---

### 4. SLA & Escalation Engine

**Purpose:** Enforce service commitments and escalation rules for regulatory accountability.

**SLA Policies:**

| Priority | First Response | Resolution |
|----------|---------------|------------|
| Critical | 15 min | 2 hours |
| High | 30 min | 4 hours |
| Medium | 1 hour | 8 hours |
| Low | 2 hours | 24 hours |

**SLA Features:**

| Feature | Implementation |
|---------|---------------|
| SLA timer start | Case creation timestamp |
| First response tracking | Status change from `open` → `in_progress` |
| Resolution tracking | Status change to `resolved` |
| Pending pause | SLA timer pauses during `pending_customer` (tracked in `pending_seconds`) |
| Breach detection | Computed on case update |
| Breach types | `first_response`, `resolution` |

**Escalation:**

| Trigger | Action |
|---------|--------|
| Agent manual | `POST /api/escalations` with reason |
| SLA breach | Escalation rule in DB (not yet automated) |
| Priority critical | Escalation rule in DB |
| Customer request | Agent initiates manually |

**Implementation:**

| Layer | File |
|-------|------|
| SLA API | `src/api/sla.py` — policies, breaches |
| SLA Service | `src/services/sla_service.py` — `check_breach()`, `match_policy()` |
| Escalation API | `src/api/escalations.py` — escalate, view |
| CX Data | `src/api/cx_data.py` — `GET /cx/sla/stats` |
| Frontend | SLA Monitor page, Escalation list, CaseDetail escalate action |
| DB | `sla_policies`, `sla_breaches`, `escalation_rules`, `escalations` |

---

### 5. Compliance & Audit

**Purpose:** Full traceability for FRA (Financial Regulatory Authority) and EGX compliance.

**What Gets Logged:**

| Audit Item | Implementation |
|------------|---------------|
| API calls | `AuditMiddleware` — every `/api/*` request (method, path, status, user, IP, elapsed) |
| Case changes | `audit_service.log_action()` on create/update/reassign/escalate |
| Note additions | Logged with `action="add_note"` |
| Data access | Investor profile/holding reads logged |
| Login/session | Login events, refresh token rotation |
| Page views | Frontend fires `audit.pageView()` on route change |
| Presence changes | Agent status updates logged |
| Approval decisions | Approval create/approve/reject logged |

**Security:**
- Sensitive fields sanitized before logging (password, token, national_id)
- Token revocation tracked via JTI
- Failed login attempts tracked with lockout

**Implementation:**

| Layer | File |
|-------|------|
| Middleware | `src/middleware/audit.py` — `AuditMiddleware` |
| Service | `src/services/audit_service.py` — `log_action()` |
| API | `src/api/audit.py` — `GET /api/audit/logs`, `POST /api/audit/page-view` |
| Frontend | `Layout.jsx` — route change logging, `AuditLogs.jsx` — log viewer |
| DB | `audit_logs` (user_id, action, resource, resource_id, detail, ip_address, timestamp) |

---

### 6. QA & Agent Performance

**Purpose:** Quality monitoring, evaluation scorecards, and performance tracking.

**Features:**

| QA Feature | Implementation |
|------------|---------------|
| Evaluation scorecards | Configurable criteria and weights |
| Agent evaluation | QA analyst scores agent per case |
| Leaderboard | Top agents ranked by avg QA score (min 5 evaluations) |
| Agent performance | Cases handled, avg resolution time, SLA compliance, QA score |
| Case-level QA | QA evaluations linked to specific cases |

**Implementation:**

| Layer | File |
|-------|------|
| QA API | `src/api/qa.py` — scorecards, evaluations |
| CX Data | `src/api/cx_data.py` — `GET /cx/qa/leaderboard`, `GET /cx/qa/agent/{id}` |
| Service | `src/services/qa_service.py`, `cx_data_service.py` |
| Frontend | Team page (leaderboard + presence), Dashboard (agent self-performance) |
| DB | `qa_scorecards`, `qa_evaluations` |

---

### 7. Operational Analytics

**Purpose:** Supervisor dashboards and KPIs for operational decision-making.

**KPIs Tracked:**

| KPI | Calculation |
|-----|-------------|
| Average Handling Time (AHT) | Mean call duration |
| First Contact Resolution (FCR) | Cases resolved without escalation |
| SLA Compliance | % cases within SLA thresholds |
| Escalation Rate | % cases escalated vs total |
| Verification Pass Rate | % identity verifications passed |
| Reopen Rate | % resolved cases reopened |
| Agent Utilization | Cases per agent |
| Case Backlog | Open cases count |

**Implementation:**

| Layer | File |
|-------|------|
| API | `src/api/cx_data.py` — `GET /cx/reports/overview`, stats endpoints |
| Service | `cx_data_service.py` — `reports_overview()`, `agent_performance()` |
| Frontend | `Dashboard.jsx` (role-based), `Reports.jsx` (overview + CSV export) |
| DB | Aggregated from `cases`, `calls`, `sla_breaches`, `qa_evaluations`, `escalations` |

---

### 8. Agent Desktop

**Purpose:** Single unified interface for agents combining call control, customer profile, case management, notes, and history.

**Desktop Components:**

| Component | File | Function |
|-----------|------|----------|
| Sidebar navigation | `Layout.jsx` | Role-based nav, presence picker |
| Incoming call popup | `IncomingCall.jsx` | Screen-pop, accept/decline, investor details, risk flags |
| Dashboard | `Dashboard.jsx` | Personal stats, open cases, QA scores |
| Case list | `CaseList.jsx` | My cases (agent), all cases (supervisor) |
| Case detail | `CaseDetail.jsx` | Status, notes, history, escalations, QA, verification |
| Case creation | `CreateCase.jsx` | New case from call or manual |
| Investor search | `InvestorSearch.jsx` | Profile, portfolio, holdings, app user |
| Identity verification | `VerificationWizard.jsx` | 4-step verbal verification protocol |
| Knowledge base | `KnowledgeBase.jsx` | Searchable articles with categories |
| Outbound queue | `OutboundQueue.jsx` | Task management for callbacks |
| SLA monitor | SLA page | Breach tracking dashboard |
| Reports | `Reports.jsx` | Operational analytics with export |

**Role-Based Views:**

| Role | Desktop Features |
|------|-----------------|
| Agent (T1) | Dashboard, my cases, new case, outbound, investor search, KB |
| Senior Agent (T2) | + escalations, SLA monitor |
| Team Lead | + team management, approval review |
| Supervisor | + all cases, reports, agent presence |
| QA Analyst | + QA evaluations, case review |
| Admin | Full access to all features |

---

## Coverage Summary

| Domain | Status | Maturity |
|--------|--------|----------|
| 1. Telephony Integration | Simulated (production-ready interface) | CTI adapter needed for Cisco |
| 2. Customer Data Lookup | Fully implemented | ANI, code, NID, search |
| 3. Case Management | Fully implemented | 6-status workflow, notes, history, ownership |
| 4. SLA & Escalation | Implemented (manual escalation) | Auto-escalation planned |
| 5. Compliance & Audit | Fully implemented | Full traceability, field masking |
| 6. QA & Performance | Fully implemented | Scorecards, evaluations, leaderboard |
| 7. Analytics | Implemented | Dashboards, KPIs, CSV export |
| 8. Agent Desktop | Fully implemented | React SPA, role-based, screen-pop |

### Production Readiness Checklist

| Item | Status |
|------|--------|
| Replace CTI simulator with Cisco JTAPI/REST adapter | Planned |
| Connect to real Core Registry (Oracle/PostgreSQL) | Planned |
| Connect to real Mobile App backend API | Planned |
| PostgreSQL for CX database | Configured in docker-compose |
| Redis for rate limiting + token store | Configured in docker-compose |
| Nginx reverse proxy | Configured |
| Docker multi-stage build | Done |
| Alembic migrations | Initialized |
| JWT refresh token rotation | Done |
| RBAC + IDOR protection | Done |
| Structured JSON logging | Done |
