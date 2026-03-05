-- CX Operation Zone — initial schema & seed data
-- Runs automatically via docker-entrypoint-initdb.d

-- ============================================================
-- ROLES & PERMISSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    field_mask_config VARCHAR(2000)
);

CREATE TABLE IF NOT EXISTS permissions (
    id       SERIAL PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action   VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INT REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    tier            VARCHAR(10) DEFAULT 'tier1',
    is_active       BOOLEAN DEFAULT TRUE,
    role_id         INT REFERENCES roles(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users(email);

-- ============================================================
-- TELEPHONY
-- ============================================================

CREATE TABLE IF NOT EXISTS calls (
    id          SERIAL PRIMARY KEY,
    ani         VARCHAR(20) NOT NULL,
    dnis        VARCHAR(20) NOT NULL,
    queue       VARCHAR(100),
    ivr_path    VARCHAR(500),
    agent_id    INT REFERENCES users(id),
    status      VARCHAR(20) DEFAULT 'ringing',
    call_start  TIMESTAMPTZ DEFAULT NOW(),
    call_end    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_calls_ani ON calls(ani);

CREATE TABLE IF NOT EXISTS cti_events (
    id          SERIAL PRIMARY KEY,
    call_id     INT REFERENCES calls(id) ON DELETE CASCADE,
    event_type  VARCHAR(30) NOT NULL,
    timestamp   TIMESTAMPTZ DEFAULT NOW(),
    payload     TEXT
);

CREATE INDEX IF NOT EXISTS idx_cti_events_call ON cti_events(call_id);

-- ============================================================
-- CASE MANAGEMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS case_taxonomy (
    id          SERIAL PRIMARY KEY,
    category    VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    is_active   BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS sla_policies (
    id                     SERIAL PRIMARY KEY,
    name                   VARCHAR(100) UNIQUE NOT NULL,
    priority               VARCHAR(20) NOT NULL,
    first_response_minutes INT NOT NULL,
    resolution_minutes     INT NOT NULL,
    is_active              BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- IDENTITY VERIFICATION
-- ============================================================

CREATE TABLE IF NOT EXISTS verification_sessions (
    id              SERIAL PRIMARY KEY,
    investor_id     INT,
    agent_id        INT REFERENCES users(id) NOT NULL,
    call_id         INT REFERENCES calls(id),
    method          VARCHAR(20) DEFAULT 'verbal',
    status          VARCHAR(20) DEFAULT 'pending',
    steps_completed TEXT DEFAULT '{}',
    steps_required  TEXT DEFAULT '["full_name","national_id","mobile_number","account_status"]',
    failure_reason  VARCHAR(500),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    verified_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_verif_investor ON verification_sessions(investor_id);
CREATE INDEX IF NOT EXISTS idx_verif_agent    ON verification_sessions(agent_id);
CREATE INDEX IF NOT EXISTS idx_verif_status   ON verification_sessions(status);

CREATE TABLE IF NOT EXISTS cases (
    id                SERIAL PRIMARY KEY,
    call_id           INT REFERENCES calls(id),
    customer_id       INT,
    agent_id          INT REFERENCES users(id) NOT NULL,
    taxonomy_id       INT REFERENCES case_taxonomy(id),
    verification_id   INT REFERENCES verification_sessions(id),
    priority          VARCHAR(20) DEFAULT 'medium',
    status            VARCHAR(20) DEFAULT 'open',
    subject           VARCHAR(300) NOT NULL,
    description       TEXT,
    sla_policy_id     INT REFERENCES sla_policies(id),
    first_response_at TIMESTAMPTZ,
    resolved_at       TIMESTAMPTZ,
    closed_at         TIMESTAMPTZ,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    pending_seconds   INT DEFAULT 0,
    pending_since     TIMESTAMPTZ,
    resolution_code   VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_cases_status   ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_agent    ON cases(agent_id);
CREATE INDEX IF NOT EXISTS idx_cases_customer ON cases(customer_id);

CREATE TABLE IF NOT EXISTS case_notes (
    id          SERIAL PRIMARY KEY,
    case_id     INT REFERENCES cases(id) ON DELETE CASCADE,
    author_id   INT REFERENCES users(id),
    content     TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_notes_case ON case_notes(case_id);

CREATE TABLE IF NOT EXISTS case_history (
    id            SERIAL PRIMARY KEY,
    case_id       INT REFERENCES cases(id) ON DELETE CASCADE,
    field_changed VARCHAR(100) NOT NULL,
    old_value     VARCHAR(500),
    new_value     VARCHAR(500),
    changed_by    INT REFERENCES users(id),
    changed_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_history_case ON case_history(case_id);

-- ============================================================
-- SLA BREACHES
-- ============================================================

CREATE TABLE IF NOT EXISTS sla_breaches (
    id          SERIAL PRIMARY KEY,
    case_id     INT REFERENCES cases(id) ON DELETE CASCADE,
    policy_id   INT REFERENCES sla_policies(id),
    breach_type VARCHAR(20) NOT NULL,
    breached_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sla_breaches_case ON sla_breaches(case_id);

-- ============================================================
-- ESCALATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS escalation_rules (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(100) UNIQUE NOT NULL,
    trigger_condition VARCHAR(500) NOT NULL,
    from_tier         VARCHAR(20) NOT NULL,
    to_tier           VARCHAR(20) NOT NULL,
    alert_channels    VARCHAR(200),
    is_active         BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS escalations (
    id             SERIAL PRIMARY KEY,
    case_id        INT REFERENCES cases(id) ON DELETE CASCADE,
    rule_id        INT REFERENCES escalation_rules(id),
    from_agent_id  INT REFERENCES users(id),
    to_agent_id    INT REFERENCES users(id),
    from_tier      VARCHAR(20) NOT NULL,
    to_tier        VARCHAR(20) NOT NULL,
    reason         TEXT NOT NULL,
    escalated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_escalations_case ON escalations(case_id);

-- ============================================================
-- AUDIT
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES users(id),
    action      VARCHAR(50) NOT NULL,
    resource    VARCHAR(50) NOT NULL,
    resource_id INT,
    detail      TEXT,
    ip_address  VARCHAR(45),
    timestamp   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user      ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource  ON audit_logs(resource);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);

-- ============================================================
-- QA
-- ============================================================

CREATE TABLE IF NOT EXISTS qa_scorecards (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(200) UNIQUE NOT NULL,
    criteria  TEXT NOT NULL,
    max_score INT DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS qa_evaluations (
    id            SERIAL PRIMARY KEY,
    case_id       INT REFERENCES cases(id),
    call_id       INT REFERENCES calls(id),
    evaluator_id  INT REFERENCES users(id),
    agent_id      INT REFERENCES users(id),
    scorecard_id  INT REFERENCES qa_scorecards(id),
    scores        TEXT NOT NULL,
    total_score   FLOAT NOT NULL,
    feedback      TEXT,
    evaluated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_eval_agent ON qa_evaluations(agent_id);
CREATE INDEX IF NOT EXISTS idx_qa_eval_case  ON qa_evaluations(case_id);

-- ============================================================
-- KNOWLEDGE BASE
-- ============================================================

CREATE TABLE IF NOT EXISTS kb_articles (
    id          SERIAL PRIMARY KEY,
    title       VARCHAR(300) NOT NULL,
    category    VARCHAR(100) NOT NULL,
    content     TEXT NOT NULL,
    tags        VARCHAR(500),
    author_id   INT REFERENCES users(id),
    is_published BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_category ON kb_articles(category);

-- ============================================================
-- APPROVALS
-- ============================================================

CREATE TABLE IF NOT EXISTS approvals (
    id              SERIAL PRIMARY KEY,
    case_id         INT REFERENCES cases(id) ON DELETE CASCADE,
    requested_by    INT REFERENCES users(id),
    reviewed_by     INT REFERENCES users(id),
    approval_type   VARCHAR(50) NOT NULL,
    amount          NUMERIC(12, 2),
    description     TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    reviewer_notes  TEXT,
    requested_at    TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approvals_case   ON approvals(case_id);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

-- ============================================================
-- AGENT PRESENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_presence (
    agent_id    INT PRIMARY KEY REFERENCES users(id),
    status      VARCHAR(20) DEFAULT 'offline',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO roles (name, description) VALUES
    ('admin',       'Full system access'),
    ('supervisor',  'Operations supervisor'),
    ('agent',       'Front-line T1 agent'),
    ('qa_analyst',  'Quality assurance evaluator'),
    ('team_lead',   'Team lead — manages a squad of agents'),
    ('senior_agent','Senior T2 agent — handles escalations and complex cases')
ON CONFLICT (name) DO NOTHING;

INSERT INTO sla_policies (name, priority, first_response_minutes, resolution_minutes) VALUES
    ('Critical SLA', 'critical', 15,  120),
    ('High SLA',     'high',     30,  240),
    ('Medium SLA',   'medium',   60,  480),
    ('Low SLA',      'low',      120, 1440)
ON CONFLICT (name) DO NOTHING;

INSERT INTO case_taxonomy (category, subcategory, description) VALUES
    ('Billing',     'Overcharge',       'Customer charged more than expected'),
    ('Billing',     'Refund Request',   'Customer requesting a refund'),
    ('Technical',   'App Crash',        'Mobile application crash or freeze'),
    ('Technical',   'Login Issue',      'Unable to log in to the app'),
    ('Account',     'Profile Update',   'Change of personal information'),
    ('Account',     'Closure Request',  'Account closure / cancellation'),
    ('Service',     'Coverage Issue',   'Network / service coverage problem'),
    ('Service',     'Plan Change',      'Request to change service plan')
ON CONFLICT DO NOTHING;

INSERT INTO escalation_rules (name, trigger_condition, from_tier, to_tier, alert_channels) VALUES
    ('T1 to T2 — SLA breach',     'sla_breach',     'tier1', 'tier2', 'email,slack'),
    ('T1 to T2 — Critical case',  'priority=critical', 'tier1', 'tier2', 'email,slack,sms'),
    ('T1 to T2 — Manual',         'manual',         'tier1', 'tier2', 'email')
ON CONFLICT (name) DO NOTHING;

INSERT INTO qa_scorecards (name, criteria, max_score) VALUES
    ('Standard Voice QA', 'greeting,identification,empathy,resolution,closing', 100)
ON CONFLICT (name) DO NOTHING;
