# MCDR API Reference

Base URL: `/api`

All endpoints return JSON. Authentication via `Authorization: Bearer <JWT>` header.

Error responses follow this structure:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [...],
    "request_id": "a1b2c3d4-e5f6"
  }
}
```

---

## Authentication

### POST `/auth/login`

Authenticate and receive a JWT token.

**Auth:** Public (rate-limited: 5 attempts / 5 min, 10 min lockout)

**Request:**
```json
{
  "username": "agent1",
  "password": "agent123"
}
```

**Response (200):**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:** 403 Invalid credentials, 403 Too many login attempts, 403 Account disabled

---

### POST `/auth/register`

Create a new user account.

**Auth:** `user:create` (admin only)

**Request:**
```json
{
  "username": "newagent",
  "email": "newagent@company.com",
  "password": "securepass123",
  "full_name": "Jane Doe",
  "role_id": 3,
  "tier": "tier1"
}
```

**Validation:**
| Field | Rule |
|-------|------|
| username | 3–50 chars, `^[a-zA-Z0-9_]+$` |
| email | 5–255 chars |
| password | 8–128 chars |
| full_name | 2–100 chars |
| role_id | ≥ 1, must exist |

**Response (201):**
```json
{
  "id": 84,
  "username": "newagent",
  "email": "newagent@company.com",
  "full_name": "Jane Doe",
  "tier": "tier1",
  "is_active": true,
  "role": { "id": 3, "name": "agent", "description": "Front-line CX agent" },
  "created_at": null
}
```

**Errors:** 409 Username already taken

---

## Users

### GET `/users/me`

**Auth:** Any authenticated user

**Response:** `UserOut` (current user profile)

### GET `/users`

**Auth:** `user:read` (supervisor, admin)

**Response:** `UserOut[]` sorted by username

### GET `/users/roles`

**Auth:** `user:read` (supervisor, admin)

**Response:**
```json
[
  { "id": 1, "name": "admin", "description": "Full system administrator" },
  { "id": 3, "name": "agent", "description": "Front-line CX agent" },
  { "id": 4, "name": "qa_analyst", "description": "Quality assurance evaluator" },
  { "id": 2, "name": "supervisor", "description": "Team lead / supervisor" }
]
```

### PATCH `/users/{user_id}`

**Auth:** `user:update` (admin)

**Request:** (all fields optional)
```json
{
  "full_name": "Updated Name",
  "role_id": 2,
  "tier": "tier2",
  "is_active": false
}
```

---

## Cases

### POST `/cases`

**Auth:** `case:create` (agent, supervisor, admin)

**Request:**
```json
{
  "subject": "Customer needs password reset",
  "description": "Customer called requesting account access help",
  "priority": "medium",
  "investor_id": 12345,
  "call_id": 67890,
  "taxonomy_id": 3
}
```

**Validation:**
| Field | Rule |
|-------|------|
| subject | 3–300 chars (required) |
| description | max 5,000 chars |
| priority | `low` / `medium` / `high` / `critical` |
| investor_id | ≥ 1 |
| call_id | ≥ 1 |
| taxonomy_id | ≥ 1 |

### GET `/cases`

**Auth:** `case:read`

**Query params:** `agent_id`, `status`, `priority`, `limit` (1–200, default 50), `offset` (≥ 0)

### GET `/cases/{case_id}`

**Auth:** `case:read`

**Errors:** 404 Case not found

### PATCH `/cases/{case_id}`

**Auth:** `case:update` — agents can only update their own cases

**Request:** (all fields optional)
```json
{
  "status": "in_progress",
  "priority": "high",
  "subject": "Updated subject",
  "description": "Updated description"
}
```

**Validation:**
| Field | Rule |
|-------|------|
| status | `open` / `in_progress` / `pending_customer` / `escalated` / `resolved` / `closed` |
| priority | `low` / `medium` / `high` / `critical` |
| subject | 3–300 chars |
| description | max 5,000 chars |

**Errors:** 403 Agents can only modify their own cases, 404 Case not found

### POST `/cases/{case_id}/notes`

**Auth:** `case:update` — agents can only add notes to their own cases

**Request:**
```json
{
  "content": "Called customer back, issue resolved",
  "is_internal": false
}
```

**Validation:** `content` 1–5,000 chars

**Errors:** 403, 404

---

## Escalations

### POST `/escalations`

**Auth:** `escalation:escalate` (agent, supervisor, admin)

**Request:**
```json
{
  "case_id": 198,
  "reason": "Customer threatening regulatory complaint, needs supervisor attention"
}
```

**Validation:**
| Field | Rule |
|-------|------|
| case_id | ≥ 1, must exist |
| reason | 5–1,000 chars |

**Business rules:**
- Case must exist
- Case must not already be escalated (409 Conflict)
- Agents can only escalate their own cases (403)
- Auto-assigns to a random active supervisor

### GET `/escalations/case/{case_id}`

**Auth:** `escalation:read` (supervisor, admin)

---

## CX Data

### GET `/cx/calls/stats`
**Auth:** `report:read` | Returns call volume, average duration, status distribution

### GET `/cx/calls/{call_id}`
**Auth:** `call:read` | Audit-logged with ANI

### GET `/cx/calls/investor/{investor_id}`
**Auth:** `call:read` | Call history for investor

### GET `/cx/calls/agent/{agent_id}`
**Auth:** `call:read` | Call history for agent

### GET `/cx/cases/stats`
**Auth:** `report:read` | Case volume, status distribution

### GET `/cx/cases/search`
**Auth:** `case:read` | Query: status, priority, category, investor_id, limit, offset

### GET `/cx/cases/{case_id}`
**Auth:** `case:read` | Audit-logged with investor_id

### GET `/cx/cases/agent/{agent_id}`
**Auth:** `case:read` | Agent case queue

### GET `/cx/agents/{agent_id}/stats`
**Auth:** `case:read` | Agent workload stats (cases, calls, by status)

### GET `/cx/agents/{agent_id}/performance`
**Auth:** `report:read` | Agent performance metrics

### GET `/cx/sla/stats`
**Auth:** `report:read` | SLA breach stats by type and policy

### GET `/cx/qa/leaderboard`
**Auth:** `qa:read` | Agent quality rankings

---

## Registry (Investor Data)

All registry endpoints are **audit-logged** for regulatory compliance.

### GET `/registry/investors`
**Auth:** `customer:read` | Search by name, national_id, investor_type, status

### GET `/registry/investors/{investor_id}`
**Auth:** `customer:read` | Full investor profile with app user and portfolio

### GET `/registry/investors/{id}/holdings`
**Auth:** `customer:read` | Stock holdings with market values

### GET `/registry/investors/{id}/portfolio`
**Auth:** `customer:read` | Portfolio summary (positions, total value)

### GET `/registry/investors/{id}/app-user`
**Auth:** `customer:read` | Mobile app user info (OTP status, last login)

---

## SLA

### GET `/sla/policies`
**Auth:** `sla:read` | List all SLA policies

### POST `/sla/policies`
**Auth:** `sla:create` (admin) | Create SLA policy

### GET `/sla/breaches/{case_id}`
**Auth:** `sla:read` | SLA breaches for a case

---

## QA

### GET `/qa/scorecards`
**Auth:** `qa:read` | List QA scoring templates

### POST `/qa/scorecards`
**Auth:** `qa:create` (admin) | Create scorecard

### POST `/qa/evaluations`
**Auth:** `qa:evaluate` (qa_analyst, admin) | Submit QA evaluation

### GET `/qa/evaluations`
**Auth:** `qa:read` | List evaluations (filter by agent_id, case_id)

---

## Audit

### GET `/audit/logs`

**Auth:** `audit:read` (admin only)

**Query params:**
| Param | Type | Description |
|-------|------|-------------|
| user_id | int | Filter by user |
| resource | string | Filter by resource path |
| action | string | Filter by action (GET, POST, page_view, etc.) |
| from_date | datetime | Start date |
| to_date | datetime | End date |
| limit | int (≤500) | Page size |
| offset | int | Pagination offset |

### POST `/audit/page-view`

**Auth:** Any authenticated user

**Request:**
```json
{
  "page": "/cases/198",
  "referrer": "/dashboard"
}
```

**Response:** 204 No Content

---

## Simulation

### POST `/simulate/incoming-call`
**Auth:** `call:read` (supervisor, admin) | Query: ani, queue, agent_id

Simulates a Cisco IVR call: generates CTI events, resolves ANI to investor, builds screen-pop with customer context, open cases, and portfolio summary.

### GET `/simulate/incoming`
**Auth:** Authenticated agent | Polls for incoming calls in agent's queue

### POST `/simulate/incoming/accept`
**Auth:** Authenticated | Accepts and clears queued call

### POST `/simulate/incoming/dismiss`
**Auth:** Authenticated | Dismisses queued call

---

## Health

### GET `/health`
**Auth:** Public | Liveness probe

### GET `/health/ready`
**Auth:** Public | Readiness probe (checks CX DB + Core DB)

Returns 503 with degraded status if any database is unreachable.
