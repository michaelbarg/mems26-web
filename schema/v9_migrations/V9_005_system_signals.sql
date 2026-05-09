-- V9_005: System signals (all 6 systems)
-- Stores classification, direction, confidence per signal event

CREATE TABLE IF NOT EXISTS v9_system_signals (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL,
    system_id       INTEGER NOT NULL,          -- 1-6
    classification  VARCHAR(30),               -- NO_SETUP, TACTICAL, STRATEGIC, etc.
    direction       VARCHAR(10),               -- LONG, SHORT, NEUTRAL
    confidence      DOUBLE PRECISION,          -- 0.0-1.0
    payload         JSONB,                     -- system-specific data
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_signals_system_ts ON v9_system_signals (system_id, ts);
CREATE INDEX IF NOT EXISTS idx_v9_signals_ts ON v9_system_signals (ts);
CREATE INDEX IF NOT EXISTS idx_v9_signals_classification ON v9_system_signals (classification);
