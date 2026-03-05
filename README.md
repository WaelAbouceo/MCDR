<p align="center">
  <img src="docs/mcdr-logo.png" alt="MCDR Logo" width="180" />
</p>

<h1 align="center">MCDR — Misr for Central Clearing, Depository and Registry</h1>

<p align="center">
  <strong>Contact Center Management System for Financial Institutions</strong><br/>
  A production-grade CX platform for regulated financial services. Handles inbound calls, case management, SLA tracking, escalation workflows, QA scoring, audit compliance, and operational reporting — built with data-zone segmentation and full regulatory traceability.
</p>

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Quick Start](#quick-start)
3. [Project Structure](#project-structure)
4. [Tech Stack](#tech-stack)
5. [Configuration](#configuration)
6. [Database Architecture](#database-architecture)
7. [Case Lifecycle](./docs/CASE_LIFECYCLE.md)
8. [API Reference](#api-reference)
9. [Security & RBAC](#security--rbac)
10. [Audit & Compliance](#audit--compliance)
11. [Frontend Application](#frontend-application)
12. [Role-Based User Guides](#role-based-user-guides)
13. [Production Deployment](#production-deployment)
14. [Development Guide](#development-guide)

---

## Architecture Overview

```
┌─────────────────┐     ┌──────────────────────────────────────────────┐     ┌──────────────────┐
│    Telephony     │────▶│         CX Operation Zone (FastAPI)          │────▶│  Customer Data   │
│  Cisco IVR/ACD   │ CTI │  Cases · SLA · Escalation · QA · Audit      │ R/O │  Zone (isolated) │
│   CTI Adapter    │     │  Users · RBAC · Rate Limiting                │     │  Investors       │
└─────────────────┘     └──────────────────────────────────────────────┘     │  Holdings        │
                              │                    ▲                          │  Securities      │
                              ▼                    │                          │  App Users       │
                        ┌──────────┐    ┌──────────────────┐                  └──────────────────┘
                        │ CX DB    │    │   React Frontend   │
                        │ (R/W)    │    │   (SPA + Vite)     │
                        └──────────┘    └──────────────────┘
```

**Design principles:**
- **Zone isolation** — Customer PII lives in a physically separate database with read-only access
- **RBAC + field masking** — Each role sees only the data they need
- **Full audit trail** — Every API call, data access, and navigation is logged
- **Production-hardened** — Rate limiting, input validation, security headers, ownership checks

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- SQLite (included, used for POC)

### Backend

```bash
# Install dependencies
pip install -r requirements.txt
pip install aiosqlite bcrypt

# Generate mock data (if not already present)
python mcdr_mock/generate_core_data.py
python mcdr_mock/generate_cx_data.py
python mcdr_mock/seed_poc.py

# Start the API server
uvicorn src.main:app --port 8100 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The application is available at:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8100
- **API Docs**: http://localhost:8100/docs (disabled in production)

### Demo Credentials

| Role | Username | Password | Name |
|------|----------|----------|------|
| Agent | `agent1` | `agent123` | Daniel Thompson |
| Supervisor | `supervisor1` | `super123` | Judy Martinez |
| QA Analyst | `qa1` | `qa1234` | Jonathon Reed |
| Admin | `admin1` | `admin123` | Ashley Roberts |

---

## Project Structure

```
MCDR/
├── src/                          # Backend (FastAPI)
│   ├── main.py                   # App entry point, middleware stack, health checks
│   ├── config.py                 # Environment-driven settings
│   ├── database.py               # Dual async engine setup (CX + Customer)
│   ├── core/
│   │   ├── security.py           # JWT token creation/verification, bcrypt
│   │   ├── permissions.py        # RBAC definitions, field masks
│   │   ├── exceptions.py         # HTTP exception classes
│   │   └── rate_limit.py         # Brute-force protection (in-memory)
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── user.py               # User, Role, Permission, RolePermission
│   │   ├── call.py               # Call, CTIEvent
│   │   ├── case.py               # Case, CaseNote, CaseHistory, CaseTaxonomy
│   │   ├── sla.py                # SLAPolicy, SLABreach
│   │   ├── escalation.py         # EscalationRule, Escalation
│   │   ├── audit.py              # AuditLog
│   │   ├── qa.py                 # QAScorecard, QAEvaluation
│   │   └── customer.py           # CustomerProfile (separate DB)
│   ├── schemas/                  # Pydantic request/response schemas
│   ├── services/                 # Business logic layer
│   │   ├── cx_data_service.py    # CX operational data (raw SQLite)
│   │   ├── call_simulator.py     # CTI simulation + in-memory call queue
│   │   ├── audit_service.py      # Audit logging service
│   │   └── rbac_service.py       # Permission checks
│   ├── middleware/
│   │   ├── auth.py               # JWT auth + RequirePermission dependency
│   │   └── audit.py              # Request-level audit middleware
│   └── api/                      # FastAPI route handlers
│       ├── router.py             # Central route registry
│       ├── auth.py               # Login, registration (admin-only)
│       ├── users.py              # User CRUD, roles list
│       ├── cases.py              # Case CRUD with ownership checks
│       ├── escalations.py        # Escalation with validation
│       ├── cx_data.py            # CX operational data endpoints
│       ├── registry.py           # Investor registry (read-only)
│       ├── telephony.py          # Call management, CTI events
│       ├── sla.py                # SLA policies and breaches
│       ├── qa.py                 # QA scorecards and evaluations
│       ├── audit.py              # Audit log queries, page-view logging
│       ├── simulate.py           # Call simulation + agent polling
│       └── reports.py            # Operational dashboards
├── frontend/                     # Frontend (React + Vite)
│   ├── src/
│   │   ├── App.jsx               # Routes, role guards
│   │   ├── lib/
│   │   │   ├── api.js            # API client (50+ functions)
│   │   │   └── auth.jsx          # Auth context provider
│   │   ├── components/
│   │   │   ├── Layout.jsx        # Sidebar, navigation, call polling
│   │   │   ├── IncomingCall.jsx   # Agent screen-pop modal
│   │   │   ├── Toast.jsx         # Toast notification system
│   │   │   ├── CaseTable.jsx     # Reusable case table
│   │   │   ├── StatCard.jsx      # Dashboard stat cards
│   │   │   └── StatusBadge.jsx   # Status badge component
│   │   └── pages/
│   │       ├── Dashboard.jsx      # Role-adaptive dashboard
│   │       ├── CaseList.jsx       # Case listing with filters
│   │       ├── CaseDetail.jsx     # Case detail with notes, escalation, QA
│   │       ├── CreateCase.jsx     # Case creation (URL param pre-fill)
│   │       ├── Escalations.jsx    # Escalated cases view
│   │       ├── SLAMonitor.jsx     # SLA breach monitoring
│   │       ├── Team.jsx           # Team performance
│   │       ├── QAEvaluations.jsx  # QA evaluation list
│   │       ├── Leaderboard.jsx    # QA leaderboard
│   │       ├── AuditLogs.jsx      # Audit trail viewer
│   │       ├── UserManagement.jsx # User CRUD (admin)
│   │       ├── SimulateCall.jsx   # Call simulation (supervisor)
│   │       ├── InvestorSearch.jsx # Investor lookup
│   │       └── Login.jsx          # Login page with demo shortcuts
│   └── package.json
├── mcdr_mock/                     # Mock data generators
├── requirements.txt
└── README.md
```

---

## Tech Stack

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115+ |
| Server | Uvicorn | 0.34+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Validation | Pydantic | 2.10+ |
| Auth | python-jose (JWT) + bcrypt | — |
| Database (POC) | SQLite + aiosqlite | — |
| Database (Prod) | PostgreSQL + asyncpg | — |

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 19.2 |
| Build Tool | Vite | 7.3 |
| Routing | React Router | 6.30 |
| Styling | Tailwind CSS | 4.2 |
| Icons | Lucide React | 0.576 |
| Date Utils | date-fns | 4.1 |

---

## Configuration

All configuration is via environment variables or `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `SECRET_KEY` | `poc-secret-key-...` | JWT signing key. **Must override in production** (≥32 chars) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT token expiry |
| `DATABASE_URL` | SQLite path | Main CX database connection |
| `CUSTOMER_DB_URL` | SQLite path | Customer database (read-only zone) |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (future use) |

### Production Validation

When `ENVIRONMENT=production`:
- `SECRET_KEY` must be ≥ 32 characters and not the default POC key (startup fails otherwise)
- Warning logged if `CORS_ORIGINS` contains `localhost`
- Swagger docs (`/docs`) are disabled

---

## Database Architecture

### Three-Database Design

| Database | File (POC) | Access | Contains |
|----------|-----------|--------|----------|
| **CX Database** | `mcdr_cx.db` | Read/Write | Cases, calls, users, roles, SLA, escalations, QA, audit logs |
| **Core Database** | `mcdr_core.db` | Read-Only | Investors, holdings, securities |
| **Mobile Database** | `mcdr_mobile.db` | Read-Only | App users, OTP records |

### Key Tables

#### CX Zone (Operational)
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | System users (agents, supervisors, admins) | id, username, role_id, is_active |
| `roles` | RBAC roles | id, name, field_mask_config |
| `permissions` | Granular permissions | id, resource, action |
| `cases` | Support cases | case_id, case_number, investor_id, agent_id, status, priority |
| `case_notes` | Case notes/comments | note_id, case_id, author_id, content, is_internal |
| `case_history` | Change audit trail | history_id, case_id, field_changed, old/new_value |
| `calls` | Call records | call_id, ani, investor_id, agent_id, duration_seconds |
| `cti_events` | Cisco CTI event chain | event_id, call_id, event_type, payload |
| `sla_policies` | SLA thresholds | policy_id, priority, first_response_minutes, resolution_minutes |
| `sla_breaches` | SLA violations | breach_id, case_id, breach_type |
| `escalations` | Case escalations | escalation_id, case_id, from/to_agent_id, reason |
| `escalation_rules` | Escalation triggers | rule_id, trigger_condition, from/to_tier |
| `qa_scorecards` | QA scoring templates | scorecard_id, name, criteria, max_score |
| `qa_evaluations` | QA scores for cases | evaluation_id, case_id, agent_id, total_score |
| `audit_logs` | Full audit trail | id, user_id, action, resource, detail, ip_address, timestamp |

#### Core Zone (Customer Data)
| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `investors` | Investor profiles | investor_id, investor_code, full_name, national_id, account_status |
| `holdings` | Stock holdings | holding_id, investor_id, security_id, quantity, market_value |
| `securities` | Listed securities | security_id, ticker, company_name, sector, last_price |

---

## API Reference

Base URL: `/api`

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | Public | Login → returns JWT + expires_in |
| POST | `/auth/register` | Admin | Create new user account |

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/users/me` | Any | Current user profile |
| GET | `/users` | Admin/Supervisor | List all users |
| GET | `/users/roles` | Admin/Supervisor | List available roles |
| PATCH | `/users/{id}` | Admin | Update user (name, role, tier, active) |

### Cases

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/cases` | Agent/Team Lead/Supervisor/Admin | Create case (validated: subject 3-300 chars, priority enum) |
| GET | `/cases` | Case readers | List cases (paginated: limit 1-200) |
| GET | `/cases/{id}` | Case readers | Get case detail |
| PATCH | `/cases/{id}` | Agent (own) / Team Lead / Supervisor / Admin | Update case (ownership enforced for agents) |
| POST | `/cases/{id}/notes` | Agent (own) / Team Lead / Supervisor / Admin | Add note (1-5000 chars) |

### Escalations

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/escalations` | Agent/Team Lead/Supervisor/Admin | Escalate case (reason 5-1000 chars, case must exist, not already escalated) |
| GET | `/escalations/case/{id}` | Supervisor/Admin | List escalations for case |

### CX Data (Reports & Search)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/cx/calls/stats` | Report readers | Call statistics |
| GET | `/cx/calls/{id}` | Call readers | Get call (audit-logged) |
| GET | `/cx/cases/stats` | Report readers | Case statistics |
| GET | `/cx/cases/search` | Case readers | Search cases with filters |
| GET | `/cx/cases/{id}` | Case readers | Get case (audit-logged) |
| GET | `/cx/agents/{id}/stats` | Case readers | Agent workload stats |
| GET | `/cx/agents/{id}/performance` | Report readers | Agent performance metrics |
| GET | `/cx/sla/stats` | Report readers | SLA breach statistics |
| GET | `/cx/qa/leaderboard` | QA readers | QA leaderboard |

### Registry (Investor Data)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/registry/investors` | Customer readers | Search investors (audit-logged) |
| GET | `/registry/investors/{id}` | Customer readers | Investor profile (audit-logged) |
| GET | `/registry/investors/{id}/holdings` | Customer readers | Portfolio holdings |
| GET | `/registry/investors/{id}/portfolio` | Customer readers | Portfolio summary |
| GET | `/registry/investors/{id}/app-user` | Customer readers | Mobile app user info |

### SLA

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/sla/policies` | Supervisor/Admin | List SLA policies |
| POST | `/sla/policies` | Admin | Create SLA policy |
| GET | `/sla/breaches/{case_id}` | Supervisor/Admin | SLA breaches for case |

### QA

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/qa/scorecards` | QA readers | List scorecards |
| POST | `/qa/scorecards` | Admin | Create scorecard |
| POST | `/qa/evaluations` | QA/Admin | Create evaluation |
| GET | `/qa/evaluations` | QA readers | List evaluations |

### Audit

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/audit/logs` | Admin only | Query audit trail (filterable by user, resource, action, date range) |
| POST | `/audit/page-view` | Any authenticated | Log frontend navigation |

### Simulation

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/simulate/incoming-call` | Supervisor/Admin | Simulate Cisco CTI call |
| GET | `/simulate/incoming` | Agent | Poll for incoming call |
| POST | `/simulate/incoming/accept` | Agent | Accept incoming call |
| POST | `/simulate/incoming/dismiss` | Agent | Dismiss incoming call |

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | Public | Liveness check |
| GET | `/health/ready` | Public | Readiness check (verifies DB connectivity, returns 503 if degraded) |

---

## Security & RBAC

### Role-Permission Matrix

| Resource | Agent (T1) | Senior Agent (T2) | Team Lead | Supervisor | QA Analyst | Admin |
|----------|:----------:|:-----------------:|:---------:|:----------:|:----------:|:-----:|
| **Case** | C R U | C R U | C R U | C R U | R U (notes only) | All |
| **Call** | R | R | R | R | R | All |
| **Customer** | R (masked) | R (masked) | R (masked) | R (masked) | R (masked) | R (all) |
| **User** | — | — | R | R | — | All |
| **SLA** | — | R | R | R | R | All |
| **Escalation** | Escalate | Escalate, R | Escalate, R | Escalate, R | R | All |
| **QA** | — | — | R | — | R, Evaluate | All |
| **Audit** | — | — | — | — | — | All |
| **Report** | R | R | R | R, Export | R | All |

### Customer Field Masking

| Role | Visible Fields |
|------|---------------|
| Agent | id, name, phone_number, account_tier |
| Team Lead | id, name, phone_number, account_number, account_tier |
| Supervisor | id, name, phone_number, account_number, account_tier |
| QA Analyst | id, name, phone_number, account_tier |
| Admin | All fields |

### Authentication Flow

1. `POST /auth/login` with username + password
2. Rate limiter checks IP and username (5 attempts / 5 min window → 10 min lockout)
3. Password verified with bcrypt
4. JWT issued with `sub` (user ID), `role`, `exp` (30 min default)
5. All protected endpoints require `Authorization: Bearer <token>`
6. `get_current_user` decodes JWT, loads user, sets `request.state` for audit
7. `RequirePermission(resource, action)` checks RBAC

### Security Headers

Every response includes:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Cache-Control` | `no-store, no-cache, must-revalidate, private` |
| `Pragma` | `no-cache` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` (production only) |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; ...` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` |
| `X-Request-ID` | Unique per request (for log correlation) |

### Data Security — At Rest

| Layer | Mechanism |
|-------|-----------|
| Passwords | bcrypt with random salt — never stored in plaintext |
| JWT secrets | `SECRET_KEY` env var, validated ≥ 32 chars in production |
| Audit logs | 30+ sensitive fields recursively masked as `***` up to 5 levels deep |
| Token storage | `sessionStorage` — cleared when browser tab closes |
| Database (POC) | SQLite on local disk |
| Database (Production) | PostgreSQL with SSL (`DATABASE_SSL=require` or `verify-full`) |

### Data Security — In Transit

| Control | Implementation |
|---------|---------------|
| HSTS with preload | Forces HTTPS after first visit, eligible for browser preload lists |
| CSP | Restricts script, style, frame, and connection origins to `self` |
| Permissions-Policy | Disables camera, microphone, geolocation, and payment APIs |
| CORS | Origins from env, restricted methods and headers |
| Auth token | Sent via `Authorization: Bearer` header only — never in URLs or cookies |
| DB connections | PostgreSQL SSL configurable via `DATABASE_SSL` env var |

> For the complete data security deep-dive, OWASP Top 10 compliance matrix, and production checklist, see **[docs/SECURITY.md](docs/SECURITY.md)**.

### Input Validation

| Field | Constraint |
|-------|-----------|
| Case subject | 3–300 characters |
| Case description | Max 5,000 characters |
| Case priority | `low` / `medium` / `high` / `critical` |
| Case status | `open` / `in_progress` / `pending_customer` / `escalated` / `resolved` / `closed` |
| Note content | 1–5,000 characters |
| Escalation reason | 5–1,000 characters |
| Username | 3–50 chars, alphanumeric + underscore |
| Password | 8–128 characters |
| Pagination limit | 1–200 |

### Ownership Enforcement

Agents and senior agents can only modify (update, add notes, escalate) **their own cases**. Team leads, supervisors, and admins bypass this restriction. QA analysts can add notes to any case but cannot modify case fields.

---

## Audit & Compliance

### What Is Captured

The system provides **three layers** of audit logging for regulatory compliance:

#### Layer 1 — HTTP Request Audit (Automatic)

Every API request is logged via middleware:
- **Who**: user_id, username, role
- **What**: HTTP method, URL path, resource ID, query parameters
- **When**: UTC timestamp
- **Where**: Client IP (supports `X-Forwarded-For`)
- **How**: Response status code, response time (ms)
- **Context**: Sanitized request body (passwords/tokens masked as `***`)

#### Layer 2 — Business-Level Audit (Per Endpoint)

Critical operations logged with business context:
- Case created (subject, investor, priority)
- Case updated (exact fields changed)
- Note added (case ID, internal flag)
- Case escalated (case ID, reason)
- Investor data accessed (investor ID, search terms)
- Call record viewed (call ID, ANI)

#### Layer 3 — Frontend Navigation

Every page transition logged via `POST /audit/page-view`:
- Page visited, referrer page, user identity, IP

### Who Can Access Audit Logs

Only the `admin` role can query audit logs via `GET /audit/logs`.

Supports filtering by: `user_id`, `resource`, `action`, `from_date`, `to_date`.

---

## Frontend Application

### Route Map

| Path | Page | Roles | Description |
|------|------|-------|-------------|
| `/login` | Login | Public | Login with demo user shortcuts |
| `/dashboard` | Dashboard | All | Role-adaptive dashboard |
| `/cases` | Case List | All | Cases with search/filters |
| `/cases/new` | Create Case | Agent, Team Lead, Supervisor, Admin | Case creation form (auto-fills from call context) |
| `/cases/:id` | Case Detail | All | Full case view with notes, escalation, QA |
| `/escalations` | Escalations | Agent (T2), Team Lead, Supervisor, Admin | Escalated cases overview |
| `/sla` | SLA Monitor | Agent (T2), Team Lead, Supervisor, Admin | SLA breach analytics |
| `/team` | Team | Team Lead, Supervisor, Admin | Team performance table |
| `/reports` | Reports | Team Lead, Supervisor, Admin | Operations KPI dashboard |
| `/qa` | QA Evaluations | QA Analyst, Admin | Evaluation list |
| `/leaderboard` | Leaderboard | QA Analyst, Admin | Agent quality rankings |
| `/investor-search` | Investor Lookup | Agent, Team Lead, Supervisor, Admin | Search and view investor profiles |
| `/admin/users` | User Management | Admin | Create, edit, activate/deactivate users |
| `/audit` | Audit Trail | Admin | Full audit log viewer with filters |
| `/simulate` | Simulate Call | Supervisor, Admin | CTI call simulation |

### Agent Workflow (Call → Case Resolution)

```
Call arrives → Screen-pop with investor context
  → Accept call → Minimized call bar
  → Click open case to review details
  → "Create Case" → investor + call pre-linked
  → Add notes → toast confirmation
  → Change status → toast confirmation
  → Escalate → reason required → toast confirmation
  → End call → bar disappears
```

### Key Features

- **Screen-pop**: Incoming call modal with full investor context, risk flags, open cases, portfolio
- **Minimized call bar**: Persistent call info while navigating other pages
- **Toast notifications**: Feedback on all agent actions (success/error/warning)
- **URL context linking**: Creating a case from a call pre-fills investor + call IDs
- **Responsive sidebar**: Role-based navigation with admin section separator
- **Audit trail viewer**: Expandable rows, color-coded actions, date range filters, pagination

---

## Role-Based User Guides

### Agent (T1)

As a front-line agent, you handle incoming customer calls and manage support cases.

**Your sidebar:** Dashboard → My Cases → New Case → Outbound Queue → Investor Lookup

**Key workflows:**
1. **Receive calls**: Incoming calls appear as a screen-pop with full investor context
2. **Accept/Decline**: Accept to connect, or decline if needed
3. **Review context**: See open cases, risk flags, portfolio while on call
4. **Create case**: Click "Create Case" from the call pop — investor and call are auto-linked
5. **Manage cases**: Add notes, change status, escalate with a reason
6. **Search investors**: Look up investor profiles and create cases from search results

### Senior Agent (T2)

As a senior agent, you handle escalated and complex cases that require deeper expertise.

**Your sidebar:** Dashboard → My Cases → New Case → Outbound Queue → Escalations → SLA Monitor → Investor Lookup

**Key workflows:**
1. **Escalation queue**: Pick up escalated cases from the queue
2. **Complex investigations**: Deep-dive into trading disputes, settlement issues, regulatory concerns
3. **SLA monitoring**: Watch for approaching breaches on your assigned cases
4. **Reassign cases**: Transfer cases to other T2 agents or supervisors
5. **Standard case work**: Create and manage cases like T1, with access to escalation context

### Team Lead

As a team lead, you manage a squad of ~10 agents, monitor their performance, and ensure SLA compliance.

**Your sidebar:** Dashboard → All Cases → New Case → Outbound Queue → Escalations → SLA Monitor → Reports → Team → Investor Lookup

**Key workflows:**
1. **Case oversight**: View and update any case in your team's queue
2. **Escalation triage**: Review escalated cases, reassign or pick up as needed
3. **SLA monitoring**: Watch for approaching SLA breaches and intervene early
4. **Team performance**: Track agent KPIs via Team and Reports pages
5. **QA review**: Read QA evaluation results for your agents (read-only)
6. **Reassign cases**: Redistribute workload when agents are overloaded

### Supervisor

As a supervisor, you oversee operations across teams, monitor SLA, and handle escalations.

**Your sidebar:** Dashboard → All Cases → Outbound Queue → Escalations → SLA Monitor → Reports → Team → Simulate Call → Investor Lookup

**Key workflows:**
1. **Monitor dashboard**: Track case volumes, SLA breaches, call statistics
2. **Handle escalations**: Review and reassign escalated cases
3. **SLA monitoring**: Track breach types and priorities
4. **Team performance**: View agent workload and quality scores
5. **Simulate calls**: Route test calls to specific agents

### QA Analyst

As a QA analyst, you evaluate agent performance and quality.

**Your sidebar:** Dashboard → Cases → QA Evaluations → Leaderboard

**Key workflows:**
1. **Review cases**: Access all cases to evaluate agent handling
2. **QA evaluations**: View evaluation scores and feedback
3. **Leaderboard**: Track agent quality rankings

### Admin

As an admin, you have full system access including user management and audit.

**Your sidebar:** Dashboard → All Cases → Escalations → SLA Monitor → Team → QA → Leaderboard → Investor Lookup → [Administration] → User Management → Audit Trail → Simulate Call

**Key workflows:**
1. **System overview**: Dashboard shows operations + user counts + recent audit activity
2. **User management**: Create users, edit roles/tiers, activate/deactivate accounts
3. **Audit trail**: Full system activity log with filtering by user, action, resource, date range
4. **All supervisor capabilities**: Escalations, SLA, team monitoring
5. **All QA capabilities**: Evaluations, leaderboard

---

## Production Deployment

### Environment Variables

```env
ENVIRONMENT=production
SECRET_KEY=your-strong-random-key-at-least-32-characters
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/mcdr_cx
CUSTOMER_DB_URL=postgresql+asyncpg://readonly:pass@host:5432/mcdr_customer
CORS_ORIGINS=https://your-frontend-domain.com
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=WARNING
```

### Health Checks

| Endpoint | Purpose | Healthy | Unhealthy |
|----------|---------|---------|-----------|
| `GET /health` | Liveness | 200 `{"status": "ok"}` | Process down |
| `GET /health/ready` | Readiness | 200 `{"status": "ok", "checks": {...}}` | 503 `{"status": "degraded"}` |

The readiness endpoint verifies connectivity to both the CX and Core databases.

### Production Checklist

- [ ] Set `ENVIRONMENT=production` (enforces secret key validation, disables /docs)
- [ ] Set strong `SECRET_KEY` (≥32 characters, high entropy)
- [ ] Configure `CORS_ORIGINS` for your frontend domain
- [ ] Use PostgreSQL (not SQLite) for both databases
- [ ] Configure reverse proxy (nginx) with TLS
- [ ] Set `LOG_LEVEL=WARNING` for production
- [ ] Verify `/health/ready` returns 200
- [ ] Test rate limiting (5 failed logins → 10 min lockout)
- [ ] Review audit logs regularly

---

## Development Guide

### Running Locally

```bash
# Backend
pip install -r requirements.txt
pip install aiosqlite bcrypt
uvicorn src.main:app --port 8100 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
pip install aiosqlite
pytest -v
```

### Key Design Decisions

1. **Dual-database architecture**: Customer PII lives in a separate database with read-only access, matching regulated financial services data-zone segmentation requirements.

2. **RBAC with field masking**: Permissions are defined at the resource-action level. Customer data is additionally masked per role — agents see only name and phone, admins see everything.

3. **In-memory rate limiting**: Login brute-force protection uses an in-memory store (thread-safe). For multi-instance deployments, replace with Redis-backed implementation.

4. **Ownership enforcement**: Agents can only modify their own cases. This is enforced at the API layer, not just the UI.

5. **Comprehensive audit**: Two parallel logging systems — middleware captures every HTTP request; service-layer logging captures business-level context. Frontend navigation is tracked separately.

6. **CTI simulation**: The call simulation system mimics Cisco IVR/ACD events with an in-memory call queue, allowing end-to-end testing of the agent screen-pop workflow without real telephony infrastructure.

7. **POC vs Production**: SQLite is used for the POC with raw SQL in `cx_data_service.py`. Production should use PostgreSQL with the SQLAlchemy models in `src/models/`.
