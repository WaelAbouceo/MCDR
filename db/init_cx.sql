-- CX Operation Zone — initial schema & seed data (MySQL)
-- Runs automatically via docker-entrypoint-initdb.d

USE mcdr_cx;

-- ============================================================
-- CX STAFF (operational users within the CX platform)
-- ============================================================

CREATE TABLE IF NOT EXISTS cx_users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    full_name     VARCHAR(200) NOT NULL,
    email         VARCHAR(255),
    role          VARCHAR(50) NOT NULL,
    tier          VARCHAR(10) DEFAULT 'tier1',
    is_active     TINYINT(1) DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- ROLES & PERMISSIONS (for ORM-based auth)
-- ============================================================

CREATE TABLE IF NOT EXISTS roles (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    field_mask_config VARCHAR(2000)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS permissions (
    id       INT AUTO_INCREMENT PRIMARY KEY,
    resource VARCHAR(50) NOT NULL,
    action   VARCHAR(50) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INT,
    permission_id INT,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    tier            VARCHAR(10) DEFAULT 'tier1',
    is_active       TINYINT(1) DEFAULT 1,
    role_id         INT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
) ENGINE=InnoDB;

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email    ON users(email);

-- ============================================================
-- TELEPHONY
-- ============================================================

CREATE TABLE IF NOT EXISTS calls (
    call_id          INT AUTO_INCREMENT PRIMARY KEY,
    ani              VARCHAR(20) NOT NULL,
    dnis             VARCHAR(20),
    investor_id      INT,
    queue            VARCHAR(100),
    ivr_path         VARCHAR(500),
    agent_id         INT,
    status           VARCHAR(20) DEFAULT 'ringing',
    call_start       DATETIME DEFAULT CURRENT_TIMESTAMP,
    call_end         DATETIME,
    duration_seconds INT DEFAULT 0,
    wait_seconds     INT DEFAULT 0,
    recording_url    VARCHAR(500)
) ENGINE=InnoDB;

CREATE INDEX idx_calls_ani ON calls(ani);
CREATE INDEX idx_calls_agent ON calls(agent_id);
CREATE INDEX idx_calls_investor ON calls(investor_id);

CREATE TABLE IF NOT EXISTS cti_events (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    call_id     INT,
    event_type  VARCHAR(30) NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
    payload     TEXT,
    FOREIGN KEY (call_id) REFERENCES calls(call_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_cti_events_call ON cti_events(call_id);

-- ============================================================
-- CASE MANAGEMENT
-- ============================================================

CREATE TABLE IF NOT EXISTS case_taxonomy (
    taxonomy_id INT AUTO_INCREMENT PRIMARY KEY,
    category    VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    is_active   TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sla_policies (
    policy_id              INT AUTO_INCREMENT PRIMARY KEY,
    name                   VARCHAR(100) UNIQUE NOT NULL,
    priority               VARCHAR(20) NOT NULL,
    first_response_minutes INT NOT NULL,
    resolution_minutes     INT NOT NULL,
    is_active              TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

-- ============================================================
-- IDENTITY VERIFICATION
-- ============================================================

CREATE TABLE IF NOT EXISTS verification_sessions (
    verification_id INT AUTO_INCREMENT PRIMARY KEY,
    investor_id     INT,
    agent_id        INT,
    call_id         INT,
    method          VARCHAR(20) DEFAULT 'verbal',
    status          VARCHAR(20) DEFAULT 'pending',
    steps_completed TEXT,
    steps_required  TEXT,
    failure_reason  VARCHAR(500),
    notes           TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    verified_at     DATETIME,
    expires_at      DATETIME,
    FOREIGN KEY (call_id) REFERENCES calls(call_id)
) ENGINE=InnoDB;

CREATE INDEX idx_verif_investor ON verification_sessions(investor_id);
CREATE INDEX idx_verif_agent    ON verification_sessions(agent_id);
CREATE INDEX idx_verif_status   ON verification_sessions(status);

CREATE TABLE IF NOT EXISTS cases (
    case_id           INT AUTO_INCREMENT PRIMARY KEY,
    case_number       VARCHAR(20),
    call_id           INT,
    investor_id       INT,
    agent_id          INT,
    taxonomy_id       INT,
    verification_id   INT,
    priority          VARCHAR(20) DEFAULT 'medium',
    status            VARCHAR(20) DEFAULT 'open',
    subject           VARCHAR(300) NOT NULL,
    description       TEXT,
    sla_policy_id     INT,
    first_response_at DATETIME,
    resolved_at       DATETIME,
    closed_at         DATETIME,
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    pending_seconds   INT DEFAULT 0,
    pending_since     DATETIME,
    resolution_code   VARCHAR(50),
    FOREIGN KEY (call_id) REFERENCES calls(call_id),
    FOREIGN KEY (taxonomy_id) REFERENCES case_taxonomy(taxonomy_id),
    FOREIGN KEY (verification_id) REFERENCES verification_sessions(verification_id),
    FOREIGN KEY (sla_policy_id) REFERENCES sla_policies(policy_id)
) ENGINE=InnoDB;

CREATE INDEX idx_cases_status   ON cases(status);
CREATE INDEX idx_cases_agent    ON cases(agent_id);
CREATE INDEX idx_cases_investor ON cases(investor_id);

CREATE TABLE IF NOT EXISTS case_notes (
    note_id     INT AUTO_INCREMENT PRIMARY KEY,
    case_id     INT,
    author_id   INT,
    content     TEXT NOT NULL,
    is_internal TINYINT(1) DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_case_notes_case ON case_notes(case_id);

CREATE TABLE IF NOT EXISTS case_history (
    history_id    INT AUTO_INCREMENT PRIMARY KEY,
    case_id       INT,
    field_changed VARCHAR(100) NOT NULL,
    old_value     VARCHAR(500),
    new_value     VARCHAR(500),
    changed_by    INT,
    changed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_case_history_case ON case_history(case_id);

-- ============================================================
-- SLA BREACHES
-- ============================================================

CREATE TABLE IF NOT EXISTS sla_breaches (
    breach_id   INT AUTO_INCREMENT PRIMARY KEY,
    case_id     INT,
    policy_id   INT,
    breach_type VARCHAR(20) NOT NULL,
    breached_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (policy_id) REFERENCES sla_policies(policy_id)
) ENGINE=InnoDB;

CREATE INDEX idx_sla_breaches_case ON sla_breaches(case_id);

-- ============================================================
-- ESCALATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS escalation_rules (
    rule_id           INT AUTO_INCREMENT PRIMARY KEY,
    name              VARCHAR(100) UNIQUE NOT NULL,
    trigger_condition VARCHAR(500) NOT NULL,
    from_tier         VARCHAR(20) NOT NULL,
    to_tier           VARCHAR(20) NOT NULL,
    alert_channels    VARCHAR(200),
    is_active         TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS escalations (
    escalation_id  INT AUTO_INCREMENT PRIMARY KEY,
    case_id        INT,
    rule_id        INT,
    from_agent_id  INT,
    to_agent_id    INT,
    from_tier      VARCHAR(20) NOT NULL,
    to_tier        VARCHAR(20) NOT NULL,
    reason         TEXT NOT NULL,
    escalated_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE,
    FOREIGN KEY (rule_id) REFERENCES escalation_rules(rule_id)
) ENGINE=InnoDB;

CREATE INDEX idx_escalations_case ON escalations(case_id);

-- ============================================================
-- AUDIT
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT,
    action      VARCHAR(50) NOT NULL,
    resource    VARCHAR(50) NOT NULL,
    resource_id INT,
    detail      TEXT,
    ip_address  VARCHAR(45),
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_audit_user      ON audit_logs(user_id);
CREATE INDEX idx_audit_resource  ON audit_logs(resource);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);

-- ============================================================
-- QA
-- ============================================================

CREATE TABLE IF NOT EXISTS qa_scorecards (
    scorecard_id INT AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(200) UNIQUE NOT NULL,
    criteria     TEXT NOT NULL,
    max_score    INT DEFAULT 100,
    is_active    TINYINT(1) DEFAULT 1
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS qa_evaluations (
    evaluation_id INT AUTO_INCREMENT PRIMARY KEY,
    case_id       INT,
    call_id       INT,
    evaluator_id  INT,
    agent_id      INT,
    scorecard_id  INT,
    scores        TEXT NOT NULL,
    total_score   FLOAT NOT NULL,
    feedback      TEXT,
    evaluated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id),
    FOREIGN KEY (call_id) REFERENCES calls(call_id),
    FOREIGN KEY (scorecard_id) REFERENCES qa_scorecards(scorecard_id)
) ENGINE=InnoDB;

CREATE INDEX idx_qa_eval_agent ON qa_evaluations(agent_id);
CREATE INDEX idx_qa_eval_case  ON qa_evaluations(case_id);

-- ============================================================
-- KNOWLEDGE BASE
-- ============================================================

CREATE TABLE IF NOT EXISTS kb_articles (
    article_id   INT AUTO_INCREMENT PRIMARY KEY,
    title        VARCHAR(300) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    content      TEXT NOT NULL,
    tags         VARCHAR(500),
    author_id    INT,
    is_published TINYINT(1) DEFAULT 1,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_kb_category ON kb_articles(category);

-- ============================================================
-- APPROVALS
-- ============================================================

CREATE TABLE IF NOT EXISTS approvals (
    approval_id     INT AUTO_INCREMENT PRIMARY KEY,
    case_id         INT,
    requested_by    INT,
    reviewed_by     INT,
    approval_type   VARCHAR(50) NOT NULL,
    amount          DECIMAL(12, 2),
    description     TEXT NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    reviewer_notes  TEXT,
    requested_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at     DATETIME,
    FOREIGN KEY (case_id) REFERENCES cases(case_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_approvals_case   ON approvals(case_id);
CREATE INDEX idx_approvals_status ON approvals(status);

-- ============================================================
-- AGENT PRESENCE
-- ============================================================

CREATE TABLE IF NOT EXISTS agent_presence (
    agent_id    INT PRIMARY KEY,
    status      VARCHAR(20) DEFAULT 'offline',
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- OUTBOUND TASKS
-- ============================================================

CREATE TABLE IF NOT EXISTS outbound_tasks (
    task_id       INT AUTO_INCREMENT PRIMARY KEY,
    task_type     VARCHAR(50) NOT NULL,
    investor_id   INT,
    agent_id      INT,
    case_id       INT,
    status        VARCHAR(20) DEFAULT 'pending',
    priority      VARCHAR(20) DEFAULT 'medium',
    notes         TEXT,
    outcome       TEXT,
    scheduled_at  DATETIME,
    attempted_at  DATETIME,
    completed_at  DATETIME,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(case_id)
) ENGINE=InnoDB;

CREATE INDEX idx_outbound_status ON outbound_tasks(status);
CREATE INDEX idx_outbound_agent  ON outbound_tasks(agent_id);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT IGNORE INTO roles (id, name, description) VALUES
    (1, 'admin',       'Full system access'),
    (2, 'supervisor',  'Operations supervisor'),
    (3, 'agent',       'Front-line T1 agent'),
    (4, 'qa_analyst',  'Quality assurance evaluator'),
    (5, 'team_lead',   'Team lead — manages a squad of agents'),
    (6, 'senior_agent','Senior T2 agent — handles escalations and complex cases');

INSERT IGNORE INTO sla_policies (policy_id, name, priority, first_response_minutes, resolution_minutes) VALUES
    (1, 'Critical SLA', 'critical', 15,  120),
    (2, 'High SLA',     'high',     30,  240),
    (3, 'Medium SLA',   'medium',   60,  480),
    (4, 'Low SLA',      'low',      120, 1440);

INSERT IGNORE INTO case_taxonomy (taxonomy_id, category, subcategory, description) VALUES
    (1, 'Billing',     'Overcharge',       'Customer charged more than expected'),
    (2, 'Billing',     'Refund Request',   'Customer requesting a refund'),
    (3, 'Technical',   'App Crash',        'Mobile application crash or freeze'),
    (4, 'Technical',   'Login Issue',      'Unable to log in to the app'),
    (5, 'Account',     'Profile Update',   'Change of personal information'),
    (6, 'Account',     'Closure Request',  'Account closure / cancellation'),
    (7, 'Service',     'Coverage Issue',   'Network / service coverage problem'),
    (8, 'Service',     'Plan Change',      'Request to change service plan');

INSERT IGNORE INTO escalation_rules (rule_id, name, trigger_condition, from_tier, to_tier, alert_channels) VALUES
    (1, 'T1 to T2 — SLA breach',     'sla_breach',        'tier1', 'tier2', 'email,slack'),
    (2, 'T1 to T2 — Critical case',  'priority=critical',  'tier1', 'tier2', 'email,slack,sms'),
    (3, 'T1 to T2 — Manual',         'manual',            'tier1', 'tier2', 'email');

INSERT IGNORE INTO qa_scorecards (scorecard_id, name, criteria, max_score) VALUES
    (1, 'Standard Voice QA', 'greeting,identification,empathy,resolution,closing', 100);
