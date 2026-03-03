# MCDR Security & Compliance Reference

## Overview

MCDR is designed for **regulated financial services** environments where data access traceability, role-based access control, and comprehensive audit logging are mandatory.

---

## Authentication

### JWT Token Flow

```
Client                          Server
  │                               │
  ├── POST /auth/login ──────────▶│ 1. Rate-limit check (IP + username)
  │   { username, password }      │ 2. Lookup user by username
  │                               │ 3. bcrypt password verification
  │                               │ 4. Check is_active flag
  │◀── 200 { access_token, ──────┤ 5. Issue JWT (sub, role, exp)
  │         expires_in }          │ 6. Clear rate-limit counters
  │                               │
  ├── GET /api/... ──────────────▶│ 7. Decode JWT
  │   Authorization: Bearer xxx   │ 8. Load user from DB
  │                               │ 9. Verify is_active
  │                               │ 10. Set request.state (user_id, username, role)
  │                               │ 11. Check RBAC permission
  │◀── 200 Response ─────────────┤ 12. Execute endpoint
  │                               │ 13. Audit log entry written
```

### Token Details

| Property | Value |
|----------|-------|
| Algorithm | HS256 |
| Signing key | `SECRET_KEY` from environment |
| Default expiry | 30 minutes |
| Payload claims | `sub` (user ID), `role`, `exp` |
| Library | python-jose |

### Password Security

| Property | Value |
|----------|-------|
| Hashing | bcrypt with random salt |
| Minimum length | 8 characters (enforced by Pydantic) |
| Maximum length | 128 characters |

---

## Rate Limiting (Brute-Force Protection)

### Configuration

| Parameter | Value |
|-----------|-------|
| Max failed attempts | 5 |
| Time window | 5 minutes (sliding) |
| Lockout duration | 10 minutes |
| Scope | Per IP address AND per username |

### Behavior

1. Each failed login records a timestamp for both `ip:{client_ip}` and `user:{username}`
2. When either key accumulates 5 failures within 5 minutes, **both are locked**
3. During lockout, all login attempts (even with correct credentials) return 403
4. Successful login clears all counters for both IP and username
5. After lockout expires, counters reset automatically

### Implementation

In-memory (`dict` + `threading.Lock`). Resets on server restart. For multi-instance deployments, replace with Redis-backed implementation in `src/core/rate_limit.py`.

---

## Role-Based Access Control (RBAC)

### Permission Model

Permissions are defined as `resource:action` pairs. Roles are assigned a set of permissions.

### Full Permission Matrix

| Resource | Action | Agent | Supervisor | QA Analyst | Admin |
|----------|--------|:-----:|:----------:|:----------:|:-----:|
| case | create | ✓ | ✓ | | ✓ |
| case | read | ✓ | ✓ | ✓ | ✓ |
| case | update | ✓ | ✓ | | ✓ |
| case | delete | | | | ✓ |
| case | export | | | | ✓ |
| call | read | ✓ | ✓ | ✓ | ✓ |
| call | create | | | | ✓ |
| customer | read | ✓ (masked) | ✓ (masked) | ✓ (masked) | ✓ |
| user | read | | ✓ | | ✓ |
| user | create | | | | ✓ |
| user | update | | | | ✓ |
| user | delete | | | | ✓ |
| sla | read | | ✓ | | ✓ |
| sla | create | | | | ✓ |
| escalation | escalate | ✓ | ✓ | | ✓ |
| escalation | read | | ✓ | | ✓ |
| qa | read | | | ✓ | ✓ |
| qa | create | | | | ✓ |
| qa | evaluate | | | ✓ | ✓ |
| audit | read | | | | ✓ |
| report | read | | ✓ | ✓ | ✓ |

### Customer Field Masking

When accessing customer profiles, each role sees a different subset of fields:

| Role | Visible Fields |
|------|---------------|
| Agent | `id`, `name`, `phone_number`, `account_tier` |
| Supervisor | `id`, `name`, `phone_number`, `account_number`, `account_tier` |
| QA Analyst | `id`, `name` |
| Admin | All fields (no masking) |

### Ownership Enforcement

Beyond RBAC, agents have an additional constraint: they can only **modify cases assigned to them**. This is enforced at the API layer:

- `PATCH /cases/{id}` — agent must be the case owner
- `POST /cases/{id}/notes` — agent must be the case owner
- `POST /escalations` — agent must own the case being escalated

Supervisors and admins bypass ownership checks.

---

## Security Headers

Applied via `SecurityHeadersMiddleware` to every response:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevent MIME-type sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-XSS-Protection` | `1; mode=block` | XSS filter |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Control referrer leakage |
| `Cache-Control` | `no-store` | Prevent caching sensitive data |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | HSTS (production only) |
| `X-Request-ID` | UUID (12 chars) | Request correlation for logs |

---

## CORS Configuration

| Property | Development | Production |
|----------|------------|------------|
| Origins | `http://localhost:3000`, `http://127.0.0.1:3000` | Set via `CORS_ORIGINS` env var |
| Methods | `GET, POST, PATCH, DELETE, OPTIONS` | Same |
| Headers | `Authorization, Content-Type, X-Request-ID` | Same |
| Credentials | Allowed | Allowed |

---

## Input Validation

All user inputs are validated via Pydantic models with strict constraints:

| Input | Validation |
|-------|-----------|
| Case subject | 3–300 characters, required |
| Case description | Max 5,000 characters |
| Case priority | Literal enum: `low`, `medium`, `high`, `critical` |
| Case status | Literal enum: `open`, `in_progress`, `pending_customer`, `escalated`, `resolved`, `closed` |
| Note content | 1–5,000 characters, required |
| Escalation reason | 5–1,000 characters, required |
| Username | 3–50 chars, `^[a-zA-Z0-9_]+$` pattern |
| Password | 8–128 characters |
| Full name | 2–100 characters |
| Email | 5–255 characters |
| Pagination limit | 1–200 (endpoint specific) |
| Pagination offset | ≥ 0 |
| All ID fields | ≥ 1 |

### SQL Injection Protection

- CX data service uses parameterized queries (`?` placeholders)
- `_next_id()` function uses a strict whitelist of allowed table/column pairs
- SQLAlchemy ORM queries use parameterized binding automatically

### Sensitive Field Sanitization

Audit middleware masks these fields in logged request bodies: `password`, `hashed_password`, `access_token`, `token`, `secret` → replaced with `***`.

---

## Error Handling

### Global Exception Handler

Unhandled exceptions return a safe response without stack traces:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred. Please try again.",
    "request_id": "a1b2c3d4-e5f6"
  }
}
```

Full stack traces are logged server-side only.

### Standard Error Codes

| Status | Error Class | Usage |
|--------|------------|-------|
| 403 | `ForbiddenError` | Invalid credentials, insufficient permissions, ownership violation |
| 404 | `NotFoundError` | Resource not found |
| 409 | `ConflictError` | Duplicate resource, already escalated |
| 422 | Validation Error | Pydantic validation failure |
| 500 | Unhandled | Unexpected server error |

---

## Production Security Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `SECRET_KEY` to a strong random value (≥ 32 characters)
- [ ] Configure `CORS_ORIGINS` for production frontend domain only
- [ ] Use HTTPS (TLS termination at reverse proxy)
- [ ] Use PostgreSQL instead of SQLite
- [ ] Review and restrict database user permissions (read-only for customer DB)
- [ ] Set `LOG_LEVEL=WARNING`
- [ ] Implement Redis-backed rate limiting for multi-instance deployments
- [ ] Set up log aggregation for audit trail analysis
- [ ] Implement token refresh flow for long sessions
- [ ] Add IP allowlisting for admin endpoints if applicable
- [ ] Regular rotation of `SECRET_KEY` with token migration
