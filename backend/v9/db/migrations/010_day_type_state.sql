-- P5.1.1: Create v9_day_type_state table (model already existed, table never created)
-- Run via: sqlite3 data/mems26_local.db < backend/v9/db/migrations/010_day_type_state.sql
CREATE TABLE IF NOT EXISTS v9_day_type_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts DATETIME NOT NULL,
    stage VARCHAR(20) NOT NULL,
    day_type VARCHAR(20),
    classification VARCHAR(30),
    confidence FLOAT,
    ib_width_class VARCHAR(10),
    opening_type VARCHAR(30),
    behavior VARCHAR(30),
    lock_state VARCHAR(20),
    meta JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_v9_day_type_state_ts ON v9_day_type_state(ts);
