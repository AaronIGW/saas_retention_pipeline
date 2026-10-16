-- User account dimension tracking registration dates and firmographic attributes.
CREATE TABLE IF NOT EXISTS dim_users (
    user_id TEXT PRIMARY KEY,
    signup_timestamp TIMESTAMP NOT NULL,
    signup_date DATE NOT NULL,
    cohort_week TEXT NOT NULL,
    company_size TEXT NOT NULL,
    plan_tier TEXT NOT NULL
);

-- Event-level telemetry capturing product interaction and resource utilization.
CREATE TABLE IF NOT EXISTS fact_product_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    event_date DATE NOT NULL,
    meeting_duration_minutes INTEGER,
    ai_tokens_consumed INTEGER,
    platform TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES dim_users(user_id)
);

-- Dead-letter table capturing records failing validation and schema integrity rules.
CREATE TABLE IF NOT EXISTS telemetry_quarantine (
    raw_payload TEXT,
    rejection_reason TEXT,
    flagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);