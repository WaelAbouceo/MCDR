# MCDR Database Schema Reference

## Database Architecture

The system uses **four MySQL databases** to enforce data-zone isolation:

| Database | MySQL Database | Access Pattern | Purpose |
|----------|----------------|----------------|---------|
| **CX Database** | `mcdr_cx` | Read/Write | Operational CX data |
| **Core Database** | `mcdr_core` | Read-Only | Investor profiles and holdings |
| **Mobile Database** | `mcdr_mobile` | Read-Only | Mobile app users |
| **Customer Database** | `mcdr_customer` | Read-Only | Additional customer data zone |

Cross-database queries use MySQL database names (`mcdr_cx`, `mcdr_core`, `mcdr_mobile`, `mcdr_customer`). The application connects to each database via separate connection URLs.

---

## CX Database — Operational Tables

### `cx_users`

Agent, supervisor, and admin accounts (mirrored from `users` for CX queries).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| user_id | INTEGER | PK | User ID |
| username | TEXT | UNIQUE | Login username |
| full_name | TEXT | | Display name |
| email | TEXT | | Email address |
| role | TEXT | | `agent` / `supervisor` / `qa_analyst` / `admin` |
| tier | TEXT | | `tier1` / `tier2` |
| is_active | INTEGER | Default: 1 | Active flag |
| created_at | TEXT | | ISO timestamp |

### `calls`

Inbound call records from the telephony system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| call_id | INTEGER | PK | Call ID |
| ani | TEXT | | Caller phone number (ANI) |
| dnis | TEXT | | Dialed number (DNIS) |
| investor_id | INTEGER | | Matched investor (if resolved) |
| queue | TEXT | | Call queue (`general`, `premium`, etc.) |
| ivr_path | TEXT | | IVR navigation path |
| agent_id | INTEGER | FK → cx_users | Assigned agent |
| status | TEXT | | `completed` / `abandoned` / `transferred` |
| call_start | TEXT | | Call start timestamp |
| call_end | TEXT | | Call end timestamp |
| duration_seconds | INTEGER | | Total call duration |
| wait_seconds | INTEGER | | Wait time in queue |
| recording_url | TEXT | | Call recording URL |

### `cti_events`

Cisco CTI event chain for each call.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| event_id | INTEGER | PK | Event ID |
| call_id | INTEGER | FK → calls | Associated call |
| event_type | TEXT | | `call_received`, `call_routed`, `call_offered`, etc. |
| timestamp | TEXT | | Event timestamp |
| payload | TEXT | | JSON event payload |

### `cases`

Support cases created from calls or manually.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| case_id | INTEGER | PK | Internal case ID |
| case_number | TEXT | UNIQUE | Display case number (`CAS-NNNNNN`) |
| call_id | INTEGER | FK → calls | Linked call (if any) |
| investor_id | INTEGER | | Linked investor |
| agent_id | INTEGER | FK → cx_users | Assigned agent |
| taxonomy_id | INTEGER | FK → case_taxonomy | Case category |
| priority | TEXT | | `low` / `medium` / `high` / `critical` |
| status | TEXT | | `open` / `in_progress` / `pending_customer` / `escalated` / `resolved` / `closed` |
| subject | TEXT | | Case subject line |
| description | TEXT | | Detailed description |
| sla_policy_id | INTEGER | FK → sla_policies | Applied SLA policy |
| first_response_at | TEXT | | First response timestamp |
| resolved_at | TEXT | | Resolution timestamp |
| closed_at | TEXT | | Closure timestamp |
| created_at | TEXT | | Creation timestamp |
| updated_at | TEXT | | Last update timestamp |

### `case_notes`

Notes and comments attached to cases.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| note_id | INTEGER | PK | Note ID |
| case_id | INTEGER | FK → cases | Parent case |
| author_id | INTEGER | FK → cx_users | Note author |
| content | TEXT | | Note content |
| is_internal | INTEGER | Default: 0 | Internal-only flag |
| created_at | TEXT | | Creation timestamp |

### `case_history`

Field-level change history for audit trail.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| history_id | INTEGER | PK | History ID |
| case_id | INTEGER | FK → cases | Parent case |
| field_changed | TEXT | | Changed field name |
| old_value | TEXT | | Previous value |
| new_value | TEXT | | New value |
| changed_by | INTEGER | FK → cx_users | User who made change |
| changed_at | TEXT | | Change timestamp |

### `case_taxonomy`

Case categorization hierarchy.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| taxonomy_id | INTEGER | PK | Taxonomy ID |
| category | TEXT | | Top-level category (Account, Billing, Service, Technical) |
| subcategory | TEXT | | Specific subcategory |
| description | TEXT | | Description |
| is_active | INTEGER | Default: 1 | Active flag |

### `sla_policies`

SLA threshold definitions by priority.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| policy_id | INTEGER | PK | Policy ID |
| name | TEXT | UNIQUE | Policy name |
| priority | TEXT | | Applied to cases with this priority |
| first_response_minutes | INTEGER | | Max time for first response |
| resolution_minutes | INTEGER | | Max time for resolution |
| is_active | INTEGER | Default: 1 | Active flag |

### `sla_breaches`

Recorded SLA violations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| breach_id | INTEGER | PK | Breach ID |
| case_id | INTEGER | FK → cases | Breached case |
| policy_id | INTEGER | FK → sla_policies | Violated policy |
| breach_type | TEXT | | `first_response` / `resolution` |
| breached_at | TEXT | | Breach timestamp |

### `escalation_rules`

Automatic escalation trigger definitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| rule_id | INTEGER | PK | Rule ID |
| name | TEXT | UNIQUE | Rule name |
| trigger_condition | TEXT | | Trigger logic |
| from_tier | TEXT | | Source tier |
| to_tier | TEXT | | Target tier |
| alert_channels | TEXT | | Notification channels |
| is_active | INTEGER | Default: 1 | Active flag |

### `escalations`

Case escalation records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| escalation_id | INTEGER | PK | Escalation ID |
| case_id | INTEGER | FK → cases | Escalated case |
| rule_id | INTEGER | FK → escalation_rules | Applied rule |
| from_agent_id | INTEGER | FK → cx_users | Originating agent |
| to_agent_id | INTEGER | FK → cx_users | Target agent/supervisor |
| from_tier | TEXT | | Source tier |
| to_tier | TEXT | | Target tier |
| reason | TEXT | | Escalation reason |
| escalated_at | TEXT | | Escalation timestamp |

### `qa_scorecards`

QA evaluation scoring templates.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| scorecard_id | INTEGER | PK | Scorecard ID |
| name | TEXT | UNIQUE | Template name |
| criteria | TEXT | | JSON criteria definition |
| max_score | INTEGER | Default: 100 | Maximum possible score |
| is_active | INTEGER | Default: 1 | Active flag |

### `qa_evaluations`

Agent quality evaluations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| evaluation_id | INTEGER | PK | Evaluation ID |
| case_id | INTEGER | FK → cases | Evaluated case |
| call_id | INTEGER | FK → calls | Evaluated call |
| evaluator_id | INTEGER | FK → cx_users | QA analyst |
| agent_id | INTEGER | FK → cx_users | Evaluated agent |
| scorecard_id | INTEGER | FK → qa_scorecards | Scorecard used |
| scores | TEXT | | JSON score breakdown |
| total_score | REAL | | Aggregate score |
| feedback | TEXT | | Written feedback |
| evaluated_at | TEXT | | Evaluation timestamp |

---

## Auth/RBAC Tables (SQLAlchemy ORM)

### `users`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | User ID |
| username | VARCHAR(100) | UNIQUE, INDEX | Login username |
| email | VARCHAR(255) | UNIQUE, INDEX, NULLABLE | Email |
| hashed_password | VARCHAR(255) | NULLABLE | Bcrypt hash |
| full_name | VARCHAR(200) | | Display name |
| tier | VARCHAR(20) | Default: `tier1` | Agent tier |
| is_active | INTEGER | Default: 1 | Active flag |
| role_id | INTEGER | FK → roles.id | Role assignment |
| created_at | VARCHAR(50) | NULLABLE | Timestamp |

### `roles`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Role ID |
| name | VARCHAR(50) | UNIQUE, INDEX | Role name |
| description | VARCHAR(255) | NULLABLE | Human-readable description |
| field_mask_config | VARCHAR(2000) | NULLABLE | JSON field mask config |

### `permissions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Permission ID |
| resource | VARCHAR(50) | | Resource name |
| action | VARCHAR(50) | | Action name |

### `role_permissions`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| role_id | INTEGER | PK, FK → roles.id | Role |
| permission_id | INTEGER | PK, FK → permissions.id | Permission |

### `audit_logs`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK | Log entry ID |
| user_id | INTEGER | FK → users.id, INDEX, NULLABLE | Acting user |
| action | VARCHAR(50) | INDEX | HTTP method or business action |
| resource | VARCHAR(50) | INDEX | URL path or resource name |
| resource_id | INTEGER | NULLABLE | Target resource ID |
| detail | TEXT | NULLABLE | Structured detail string |
| ip_address | VARCHAR(45) | NULLABLE | Client IP (IPv4/IPv6) |
| timestamp | DATETIME(TZ) | INDEX, Default: UTC now | Event timestamp |

---

## Core Database — Investor Data

### `investors`

| Column | Type | Description |
|--------|------|-------------|
| investor_id | INTEGER (PK) | Investor ID |
| investor_code | TEXT (UNIQUE) | Display code (`INV-NNNNNN`) |
| full_name | TEXT | Full name |
| national_id | TEXT | National ID |
| investor_type | TEXT | `Retail` / `Institutional` |
| account_status | TEXT | `Active` / `Suspended` |
| created_at | TEXT | Account creation date |

### `holdings`

| Column | Type | Description |
|--------|------|-------------|
| holding_id | INTEGER (PK) | Holding ID |
| investor_id | INTEGER (FK) | Owner investor |
| security_id | INTEGER (FK) | Held security |
| quantity | INTEGER | Share quantity |
| average_cost | REAL | Average purchase price |
| market_value | REAL | Current market value |
| last_updated | TEXT | Last valuation date |

### `securities`

| Column | Type | Description |
|--------|------|-------------|
| security_id | INTEGER (PK) | Security ID |
| ticker | TEXT (UNIQUE) | Stock ticker |
| company_name | TEXT | Company name |
| sector | TEXT | Industry sector |
| last_price | REAL | Latest trading price |
| currency | TEXT | Trading currency (SAR) |

---

## Entity Relationship Summary

```
investors ──┬── holdings ──── securities
             │
             ├── cases ──┬── case_notes
             │           ├── case_history
             │           ├── sla_breaches ──── sla_policies
             │           ├── escalations ──── escalation_rules
             │           └── qa_evaluations ──── qa_scorecards
             │
             └── calls ──── cti_events

users ──── roles ──── permissions (via role_permissions)
  │
  └── audit_logs
```
