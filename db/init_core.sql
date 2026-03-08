-- MCDR Core Registry — initial schema (MySQL)
-- Investor registry, securities, and holdings

USE mcdr_core;

CREATE TABLE IF NOT EXISTS investors (
    investor_id    INT AUTO_INCREMENT PRIMARY KEY,
    investor_code  VARCHAR(20) UNIQUE,
    full_name      VARCHAR(200),
    national_id    VARCHAR(20),
    investor_type  VARCHAR(20),
    account_status VARCHAR(20),
    created_at     VARCHAR(20)
) ENGINE=InnoDB;

CREATE INDEX idx_investors_code ON investors(investor_code);
CREATE INDEX idx_investors_nid  ON investors(national_id);

CREATE TABLE IF NOT EXISTS securities (
    security_id  INT AUTO_INCREMENT PRIMARY KEY,
    isin         VARCHAR(20) UNIQUE,
    ticker       VARCHAR(20),
    company_name VARCHAR(200),
    sector       VARCHAR(100)
) ENGINE=InnoDB;

CREATE INDEX idx_securities_ticker ON securities(ticker);
CREATE INDEX idx_securities_isin   ON securities(isin);

CREATE TABLE IF NOT EXISTS holdings (
    holding_id   INT AUTO_INCREMENT PRIMARY KEY,
    investor_id  INT,
    security_id  INT,
    quantity     INT,
    avg_price    DOUBLE,
    last_updated VARCHAR(20),
    FOREIGN KEY (investor_id) REFERENCES investors(investor_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
) ENGINE=InnoDB;

CREATE INDEX idx_holdings_investor ON holdings(investor_id);
