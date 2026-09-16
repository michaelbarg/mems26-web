-- T-390: SituationVector decision logging table.
-- Stores DECISION rows (per setup) and optionally BAR rows (every RTH bar).
CREATE TABLE IF NOT EXISTS v9_decision_vectors (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    kind VARCHAR(20) NOT NULL,  -- 'DECISION' or 'BAR'
    system INT,
    classification VARCHAR(100),
    direction VARCHAR(10),
    entry NUMERIC,
    phase VARCHAR(5),
    blocked_by VARCHAR(100),
    reason TEXT,
    mode_result JSONB,
    vector JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_decision_vectors_ts ON v9_decision_vectors(ts);
CREATE INDEX IF NOT EXISTS idx_decision_vectors_kind ON v9_decision_vectors(kind);
