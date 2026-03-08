-- MCDR Mobile App — initial schema (MySQL)
-- Mobile app user accounts linked to investors

USE mcdr_mobile;

CREATE TABLE IF NOT EXISTS app_users (
    app_user_id   INT AUTO_INCREMENT PRIMARY KEY,
    investor_id   INT,
    username      VARCHAR(100) UNIQUE,
    mobile        VARCHAR(20),
    email         VARCHAR(255),
    password_hash VARCHAR(200),
    otp_verified  TINYINT(1) DEFAULT 0,
    status        VARCHAR(20) DEFAULT 'Active',
    last_login    DATETIME,
    created_at    VARCHAR(20)
) ENGINE=InnoDB;

CREATE INDEX idx_app_users_investor ON app_users(investor_id);
CREATE INDEX idx_app_users_mobile   ON app_users(mobile);
