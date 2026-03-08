# MCDR CX Platform — What This Application Does

This document describes in detail what the MCDR CX Platform is, whom it serves, and how it works. It is based on the current codebase and supporting documentation.

---

## 1. What Is MCDR?

**MCDR** stands for **Misr for Central Clearing, Depository and Registry** — Egypt’s central securities depository and clearing house. The organization operates the infrastructure for the Egyptian Exchange (EGX): clearing, settlement, custody, and registry of securities.

This application is the **MCDR CX (Customer Experience) Platform** — a contact center management system used by MCDR’s support staff to handle investor inquiries received by phone (and related channels). It is built for a **regulated financial environment**: data is segregated, access is role-based, and every action is auditable for compliance (e.g. FRA, EGX).

---

## 2. Purpose and Positioning

The platform sits between **telephony** (e.g. Cisco IVR/ACD) and **business data** (investor registry, mobile app, cases). It:

- Receives call/CTI events and shows agents a **screen-pop** with caller identity and context.
- Lets agents **create and manage cases** (tickets) linked to calls and investors.
- Enforces **SLA** (first response and resolution times) and supports **escalation** from Tier 1 to Tier 2.
- Tracks **identity verification**, **QA evaluations**, **approvals**, and **outbound tasks**.
- Keeps a **full audit trail** of API calls, data access, and navigation.

In production, telephony would be Cisco (IVR, ACD, Finesse). In the current POC, telephony is **simulated**: supervisors can “simulate” an incoming call to test the screen-pop and case-creation flow without real Cisco infrastructure.

---

## 3. End-to-End Call Flow

Typical flow from investor call to case closure:

```
Investor dials MCDR hotline
    → Cisco IVR (e.g. "Mobile App Support" → "Login / Password Issues")
    → Call routed to an available agent (ACD queue)
    → CTI "call_offered" event sent to MCDR CX
    → Platform looks up caller by phone (ANI) in Mobile App DB → investor_id
    → Fetches from Core Registry: investor profile, account status, portfolio summary
    → Fetches from CX DB: open cases, recent calls, risk flags
    → Builds screen-pop and pushes it to the agent’s browser (IncomingCall modal)
    → Agent accepts call → can create a case linked to the call and investor
    → Agent performs 4-step identity verification (verbal) if handling investor data
    → Agent works the case (notes, status changes), escalates if needed
    → Agent resolves with a resolution code; case can then be closed
```

**Screen-pop** includes: caller name, investor code, account status, portfolio summary (positions, value), open/recent cases, recent calls, and risk flags (e.g. FREQUENT_CALLER, OTP_NOT_VERIFIED). All of this is shown in the **IncomingCall** component so the agent has context before answering.

---

## 4. The Eight CX Domains

The platform is organized into eight functional domains. The following table summarizes each; more detail is in `docs/CX_PLATFORM_DOMAINS.md`.

| # | Domain | What it does |
|---|--------|---------------|
| **1** | **Telephony integration** | Receives CTI events (call_offered, call_answered, call_ended, etc.), builds screen-pop, tracks call state. Currently **simulated** via `call_simulator.py` and `/api/simulate/*`; production would use a Cisco CTI adapter. |
| **2** | **Customer data lookup** | Read-only access to investor data: profile (Core Registry), holdings, portfolio, app user (mobile, email, OTP status). Used for screen-pop and **Investor Search**. Data lives in separate DBs with role-based field masking. |
| **3** | **Case management** | Full lifecycle of support cases: create, update status, add notes, reassign, escalate. Cases have priority, taxonomy (category/subcategory), SLA policy, resolution code, and ownership (agent can only modify own cases unless TL/supervisor/admin). |
| **4** | **SLA and escalation** | SLA policies by priority (e.g. critical: 15 min first response, 2 h resolution). Breaches recorded; escalation from T1 to T2 with reason and audit. Escalation can be manual or (in future) rule-based (e.g. on SLA breach). |
| **5** | **Compliance and audit** | Every API request logged (method, path, user, IP, status, duration). Business events (case create/update, note, escalation, investor access, login, page view) logged with context. Sensitive fields sanitized; only admins can query audit logs. |
| **6** | **QA and agent performance** | QA scorecards and evaluations per case; leaderboard by average score; agent-level stats (cases handled, avg resolution time, SLA compliance, QA score). |
| **7** | **Operational analytics** | Dashboards and reports: case volume, SLA compliance, category/resolution breakdown, agent performance. Filterable by period; supervisors/admins can export (e.g. CSV). |
| **8** | **Agent desktop** | Single React SPA: sidebar (role-based), incoming call popup, dashboard, case list/detail/create, investor search, verification wizard, knowledge base, outbound queue, SLA monitor, escalations, team, QA, reports, and (for admin) user management and audit log viewer. |

---

## 5. Case Management in Detail

### Statuses and lifecycle

Cases move through six statuses:

| Status | Meaning |
|--------|--------|
| `open` | Just created; first-response SLA timer running. |
| `in_progress` | Agent is working it; first response recorded. |
| `pending_customer` | Waiting on customer (e.g. documents, callback); resolution SLA can pause. |
| `escalated` | Handed from T1 to T2; escalation record with reason. |
| `resolved` | Issue addressed; `resolved_at` set; may still be reviewed/closed. |
| `closed` | Terminal; no further transitions. |

Valid transitions are enforced (e.g. `open` → `in_progress` or `escalated` or `closed`; `closed` → none). Resolving a case **requires a resolution code** (e.g. fixed, information_provided, duplicate, account_updated). For cases with an investor, moving from `open` to `in_progress` typically requires a **passed identity verification** session linked to the case.

### Case data

Each case has: case number (e.g. CAS-XXXXXX), linked call (optional), investor (optional), assigned agent, taxonomy (category/subcategory), priority, SLA policy, status, timestamps (created, first_response, resolved, closed), notes, and full **field-level history** (who changed what, when). Agents can only update their **own** cases unless they are team lead, supervisor, or admin.

### Escalation

When an agent escalates, the case status becomes `escalated`, an escalation record is created (from/to agent, reason), and the case can be picked up by a senior agent or supervisor. Reassignment updates `agent_id` and is recorded in case history. See `docs/CASE_LIFECYCLE.md` for the full transition map and role permissions.

---

## 6. Roles and Capabilities

Users have one role each. The UI (sidebar, routes) and API (permissions) both enforce role-based access.

| Role | Typical use | Notable capabilities |
|------|-------------|------------------------|
| **Agent (T1)** | Front-line; handles incoming calls and own cases. | Dashboard, My Cases, New Case, Outbound Queue, Investor Lookup, Knowledge Base. Cannot see Escalations queue or SLA Monitor. |
| **Senior agent (T2)** | Handles escalated and complex cases. | Same as agent plus Escalations, SLA Monitor. |
| **Team lead** | Manages a squad of agents. | All Cases, Escalations, SLA Monitor, Reports, Team; can reassign cases and review approvals. Cannot simulate calls or manage users. |
| **Supervisor** | Operations across teams. | All of the above plus Simulate Call (for testing screen-pop). Cannot manage users or see full audit. |
| **QA analyst** | Quality evaluation. | Cases (read/notes), QA Evaluations, Leaderboard. Does not create cases or access Simulate/Reports/Team in the same way as supervisors. |
| **Admin** | Full system access. | User Management, Audit Trail, Simulate Call, and all other features. |

Permissions are enforced in the API via `RequirePermission(Resource, Action)` and in the frontend via `ProtectedRoute` and role checks. Customer data is **field-masked** by role (e.g. agents see limited PII; admins see full profile).

---

## 7. Identity Verification

Before handling investor-related cases, agents must complete a **4-step verbal verification** (full name, national ID digits, mobile, account status). The app provides a **Verification Wizard**; when all steps pass, the session is linked to the case. A case with an `investor_id` cannot move from `open` to `in_progress` without a linked **passed** verification (enforced by API). Sessions expire after a set time; expired sessions cannot be linked.

---

## 8. SLA and Breach Tracking

Each case has a **priority** (low, medium, high, critical). An SLA policy defines:

- **First response:** time from creation until the case leaves `open` (e.g. 15 minutes for critical).
- **Resolution:** time from creation to `resolved`, with **pending_customer** time subtracted (tracked in `pending_seconds`).

Breaches are stored in `sla_breaches` (first_response vs resolution). The **SLA Monitor** page and reports show breach counts and compliance. Escalation rules (e.g. auto-escalate on breach) can be extended in the data model.

---

## 9. QA Evaluations and Leaderboard

QA analysts (and admins) can create **evaluations** for cases: score against a scorecard (criteria and weights). Evaluations are tied to case and agent. The **Leaderboard** ranks agents by average QA score (with minimum evaluation count). Agents see their own QA summary on the Dashboard.

---

## 10. Outbound Queue

The **Outbound** module manages callback/follow-up tasks: broken sign-up, inactive user, transaction verification, QA callback. Tasks have status (pending → in_progress → completed/failed/cancelled), optional investor/case link, priority, and outcome notes. Agents and supervisors use the **Outbound Queue** page to pick up, complete, or fail tasks. Stats and list APIs support filtering and pagination.

---

## 11. Knowledge Base

Agents can search **knowledge base articles** by category and keyword. Articles are stored in the CX database; the **Knowledge Base** page lists and opens them. Used for standard procedures and answers during calls.

---

## 12. Approvals

Certain actions (e.g. financial or sensitive) can require **approval**. Agents request approval; team leads or supervisors review (approve/reject). Approval requests and decisions are logged and linked to cases where applicable.

---

## 13. Data Architecture (Three Databases)

The POC uses three SQLite databases; production can use PostgreSQL for all.

| Database | Purpose | Access from CX |
|----------|---------|----------------|
| **CX database** (`mcdr_cx.db`) | Operational data owned by the contact center: users, roles, cases, notes, history, calls, CTI events, SLA policies/breaches, escalations, QA, audit logs, outbound tasks, verification sessions, KB articles, approvals, presence. | Read/write. |
| **Core registry** (`mcdr_core.db`) | Investor master data: investors, securities, holdings. | Read-only (attached or separate connection). |
| **Mobile app DB** (`mcdr_mobile.db`) | App users: link phone to investor_id, email, OTP status, etc. | Read-only. |

**Zone isolation:** Customer PII lives in Core and Mobile; the CX layer only reads it and applies field masking per role. All writes go to the CX database. This supports regulatory requirements for data segregation and traceability.

---

## 14. Security and Audit

- **Authentication:** Login returns JWT (and optional refresh token). APIs expect `Authorization: Bearer <token>`.
- **Authorization:** RBAC per resource/action (e.g. case:read, case:update, audit:read). Ownership checks ensure agents only modify their own cases where applicable.
- **Field masking:** Customer profile fields are filtered by role before response (e.g. agent sees name/phone; admin sees full profile).
- **Audit:** Middleware logs every request; business events and page views are logged with user, resource, action, and detail. Passwords and tokens are never logged in clear form.
- **Rate limiting:** Login is rate-limited to reduce brute-force risk; lockout after repeated failures.

---

## 15. Frontend Pages (Summary)

| Route | Page | Main purpose |
|-------|------|--------------|
| `/login` | Login | Authenticate; demo shortcuts for each role. |
| `/dashboard` | Dashboard | Role-based stats (cases, calls, SLA, QA), recent cases, admin panel if admin. |
| `/cases` | Case list | My cases (agents) or all cases (TL/supervisor/admin); filters and pagination. |
| `/cases/new` | Create case | New case form; can pre-fill from call/investor context. |
| `/cases/:id` | Case detail | Full case view: notes, history, escalation, QA, verification, actions. |
| `/escalations` | Escalations | List of escalated cases. |
| `/sla` | SLA Monitor | SLA breach overview. |
| `/team` | Team | Team presence and performance (leaderboard). |
| `/reports` | Reports | Operational KPIs and export. |
| `/qa` | QA evaluations | List of QA evaluations. |
| `/leaderboard` | Leaderboard | Agent rankings by QA score. |
| `/investor-search` | Investor lookup | Search investors; view profile, holdings, portfolio; create case from result. |
| `/outbound` | Outbound queue | List and manage outbound tasks. |
| `/kb` | Knowledge base | Search and read KB articles. |
| `/simulate` | Simulate call | Trigger a test incoming call (supervisor/admin). |
| `/admin/users` | User management | CRUD users, assign roles (admin only). |
| `/audit` | Audit logs | Query and view audit trail (admin only). |

---

## 16. Technology Stack

- **Backend:** FastAPI, Uvicorn, SQLAlchemy (async), Pydantic. Auth: JWT (python-jose), bcrypt. Optional Redis for rate limiting and token store.
- **Frontend:** React 19, Vite, React Router, Tailwind CSS, Lucide icons. API client and auth context call `/api` (and `/api/v1`) endpoints.
- **Data (POC):** SQLite (three DBs). Production: PostgreSQL (and optional Redis) as in `docker-compose.yml`.
- **Deployment:** Backend can serve the built frontend (SPA) from `frontend/dist`; alternatively Nginx can serve static assets and proxy `/api` to the backend.

---

## 17. Production vs POC

- **POC (current):** SQLite for all three DBs; mock data generators create investors, app users, cases, calls, and auth users. Telephony is simulated. Suitable for development and demos.
- **Production:** PostgreSQL for CX and customer data; real Cisco CTI adapter; Redis for rate limiting/token store; Nginx (or similar) in front; strong `SECRET_KEY` and CORS; `/docs` disabled. See `docker-compose.yml` and `docs/AWS_DEPLOYMENT.md` for deployment patterns.

---

## 18. Related Documentation

- **Run the app:** [HOW_TO_USE.md](HOW_TO_USE.md)
- **Eight domains in depth:** [docs/CX_PLATFORM_DOMAINS.md](docs/CX_PLATFORM_DOMAINS.md)
- **Case statuses and transitions:** [docs/CASE_LIFECYCLE.md](docs/CASE_LIFECYCLE.md)
- **API reference:** [docs/API_REFERENCE.md](docs/API_REFERENCE.md)
- **Security:** [docs/SECURITY.md](docs/SECURITY.md)
