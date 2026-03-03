-- Customer Data Zone — isolated read-only database
-- This DB is on a separate host with restricted network access

CREATE TABLE IF NOT EXISTS customer_profiles (
    id             SERIAL PRIMARY KEY,
    phone_number   VARCHAR(20) UNIQUE NOT NULL,
    name           VARCHAR(200) NOT NULL,
    account_number VARCHAR(50) UNIQUE NOT NULL,
    account_tier   VARCHAR(20) DEFAULT 'standard',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cp_phone   ON customer_profiles(phone_number);
CREATE INDEX IF NOT EXISTS idx_cp_account ON customer_profiles(account_number);

-- Sample data
INSERT INTO customer_profiles (phone_number, name, account_number, account_tier) VALUES
    ('+1-555-0101', 'Alice Johnson',    'ACCT-10001', 'premium'),
    ('+1-555-0102', 'Bob Williams',     'ACCT-10002', 'standard'),
    ('+1-555-0103', 'Carol Martinez',   'ACCT-10003', 'premium'),
    ('+1-555-0104', 'David Lee',        'ACCT-10004', 'standard'),
    ('+1-555-0105', 'Eve Thompson',     'ACCT-10005', 'enterprise')
ON CONFLICT DO NOTHING;

-- Read-only enforcement: revoke write on the table for the app role
-- (The DB user 'mcdr_readonly' should only have SELECT privilege)
REVOKE INSERT, UPDATE, DELETE ON customer_profiles FROM PUBLIC;
