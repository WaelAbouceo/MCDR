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

## Data Security — At Rest

| Layer | Mechanism | Details |
|-------|-----------|---------|
| **Passwords** | bcrypt with random salt | Never stored in plaintext. `hashed_password` column, 255 chars. Schema `UserOut` excludes it from all API responses. |
| **JWT secrets** | Environment variable | `SECRET_KEY` validated ≥ 32 chars in production. Default POC key rejected. |
| **Audit log sanitization** | Deep recursive scrubbing | 30+ sensitive field names (`password`, `access_token`, `credit_card`, `ssn`, `national_id`, `otp`, `api_key`, etc.) masked as `***` at any nesting level up to 5 deep. |
| **Token storage (frontend)** | `sessionStorage` | Token cleared when browser tab/window closes. Not persisted across sessions (unlike `localStorage`). |
| **Database (POC)** | MySQL in Docker | No encryption at rest (acceptable for POC). |
| **Database (Production)** | PostgreSQL with SSL | `DATABASE_SSL` env var supports `require` and `verify-full` modes. `pool_pre_ping=True` detects stale connections. |
| **API responses** | Schema-level exclusion | `hashed_password` never returned. Customer fields masked per role (see Field Masking section). |

### Sensitive Fields Masked in Audit Logs

```
password, hashed_password, new_password, old_password, confirm_password,
access_token, refresh_token, token, api_key, apikey,
secret, secret_key, client_secret,
authorization, cookie,
credit_card, card_number, cvv, ssn, national_id,
pin, otp, verification_code
```

All fields are matched case-insensitively and recursively through nested JSON objects.

---

## Data Security — In Transit

| Layer | Header / Mechanism | Value |
|-------|-------------------|-------|
| **HSTS** | `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` (production only) |
| **CSP** | `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` |
| **Permissions-Policy** | `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` |
| **Cache-Control** | `Cache-Control` + `Pragma` | `no-store, no-cache, must-revalidate, private` + `no-cache` |
| **Frame protection** | `X-Frame-Options` | `DENY` |
| **MIME sniffing** | `X-Content-Type-Options` | `nosniff` |
| **XSS filter** | `X-XSS-Protection` | `1; mode=block` |
| **Referrer** | `Referrer-Policy` | `strict-origin-when-cross-origin` |
| **Request tracing** | `X-Request-ID` | Unique UUID per request for log correlation |
| **CORS** | `CORSMiddleware` | Origins from `CORS_ORIGINS` env, methods restricted to `GET, POST, PATCH, DELETE, OPTIONS`, headers restricted to `Authorization, Content-Type, X-Request-ID` |
| **Auth token** | `Authorization: Bearer` | Token sent in header only — never in URLs, cookies, or query params |
| **Database connections** | PostgreSQL SSL | Configurable via `DATABASE_SSL=require` or `DATABASE_SSL=verify-full` |

### Database SSL Configuration

Set via environment variable:

| `DATABASE_SSL` | Behavior |
|----------------|----------|
| *(empty)* | No SSL (default, suitable for local/POC) |
| `require` | Encrypted connection, no certificate verification |
| `verify-full` | Encrypted connection + full certificate verification (recommended for production) |

---

## OWASP Top 10 Compliance

The system has been tested against all OWASP Top 10 (2021) categories:

| # | Category | Status | Key Controls |
|---|----------|--------|-------------|
| A01 | Broken Access Control | **PASS** | RBAC, ownership enforcement, admin-only registration, 401/403 on all protected endpoints |
| A02 | Cryptographic Failures | **PASS** | bcrypt passwords, JWT signing, no secrets in responses or logs, deep audit sanitization |
| A03 | Injection | **PASS** | Parameterized SQL queries, Pydantic type validation, React JSX auto-escaping |
| A04 | Insecure Design | **PASS** | Whitelisted update fields, re-escalation prevention, input length/enum constraints |
| A05 | Security Misconfiguration | **PASS** | Full security headers (CSP, HSTS, Permissions-Policy), no stack trace leakage, CORS from env |
| A06 | Vulnerable Components | **INFO** | Current dependency versions (FastAPI, React 19, Vite 7) |
| A07 | Auth Failures | **PASS** | Rate limiting (5 attempts / 5 min / 10 min lockout), JWT validation, no user enumeration |
| A08 | Data Integrity | **PASS** | JWT signature verification rejects tampered tokens |
| A09 | Logging & Monitoring | **PASS** | 3-layer audit (HTTP requests + business actions + frontend navigation), admin-only log access |
| A10 | SSRF | **N/A** | No outbound HTTP requests from user input |

---

## Infrastructure Security (Deployment Configuration)

These items are not enforced in application code and must be configured during deployment:

| Item | How to Enable |
|------|--------------|
| **HTTPS / TLS termination** | Configure at reverse proxy (nginx, AWS ALB, Cloudflare). The app emits HSTS to enforce HTTPS after first visit. |
| **Database encryption at rest** | Enable at database/cloud level (AWS RDS encryption, Azure TDE, GCP Cloud SQL encryption). |
| **Redis TLS** | Use `rediss://` scheme in `REDIS_URL` when Redis is deployed for rate limiting. |
| **Disk encryption** | Enable OS-level encryption (FileVault on macOS, LUKS on Linux, BitLocker on Windows). |
| **Certificate pinning** | Configure at infrastructure/CDN layer for mobile or API clients. |
| **Network segmentation** | Place Customer Data Zone database on a separate network with read-only access from the CX zone. |
| **Log aggregation** | Ship audit logs to SIEM (Splunk, ELK, etc.) for real-time alerting and compliance reporting. |
| **Key rotation** | Rotate `SECRET_KEY` periodically. Existing tokens will expire naturally (30 min default). |

---

## Production Security Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `SECRET_KEY` to a strong random value (≥ 32 characters)
- [ ] Set `DATABASE_SSL=verify-full` for PostgreSQL
- [ ] Configure `CORS_ORIGINS` for production frontend domain only
- [ ] Use HTTPS with TLS 1.2+ at reverse proxy
- [ ] Verify HSTS header is present (`curl -I https://your-domain/health`)
- [ ] Use MySQL (via Docker) or PostgreSQL for production
- [ ] Review and restrict database user permissions (read-only for customer DB)
- [ ] Set `LOG_LEVEL=WARNING`
- [ ] Verify `/health/ready` returns 200 with all checks passing
- [ ] Test rate limiting (5 failed logins → 10 min lockout)
- [ ] Implement Redis-backed rate limiting for multi-instance deployments
- [ ] Set up log aggregation for audit trail analysis
- [ ] Enable database encryption at rest
- [ ] Enable OS-level disk encryption
- [ ] Add IP allowlisting for admin endpoints if applicable
- [ ] Schedule regular `SECRET_KEY` rotation
- [ ] Run OWASP ZAP or similar scanner against staging
