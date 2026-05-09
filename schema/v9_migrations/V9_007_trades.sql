-- V9_007: Trades — all 3 modes (SHADOW, DEMO/SIM, LIVE)
-- Core trade journal for MEMS26 V9

CREATE TABLE IF NOT EXISTS v9_trades (
    id                  BIGSERIAL PRIMARY KEY,
    mode                VARCHAR(10) NOT NULL,       -- SHADOW, SIM, LIVE
    dominant_system     INTEGER NOT NULL,            -- 1, 2, or 4 (firing system)
    direction           VARCHAR(10) NOT NULL,        -- LONG, SHORT
    entry_ts            TIMESTAMP WITH TIME ZONE,
    entry_price         DOUBLE PRECISION,
    stop_initial        DOUBLE PRECISION,
    stop_final          DOUBLE PRECISION,
    t1_price            DOUBLE PRECISION,
    t1_filled_at        TIMESTAMP WITH TIME ZONE,
    t2_price            DOUBLE PRECISION,
    t2_filled_at        TIMESTAMP WITH TIME ZONE,
    t3_price            DOUBLE PRECISION,
    exit_ts             TIMESTAMP WITH TIME ZONE,
    exit_price          DOUBLE PRECISION,
    exit_reason         VARCHAR(30),                 -- T1, T2, T3, STOP, TIME_STOP, MANUAL, REVERSAL
    pnl_usd             DOUBLE PRECISION,
    pnl_r               DOUBLE PRECISION,
    outcome             VARCHAR(10),                 -- WIN, LOSS, BE, SCRATCH
    quality_review      JSONB,
    sierra_bracket_id   VARCHAR(50),
    context_json        JSONB,                       -- full context at entry
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_trades_mode ON v9_trades (mode);
CREATE INDEX IF NOT EXISTS idx_v9_trades_system ON v9_trades (dominant_system);
CREATE INDEX IF NOT EXISTS idx_v9_trades_entry_ts ON v9_trades (entry_ts);
CREATE INDEX IF NOT EXISTS idx_v9_trades_mode_system ON v9_trades (mode, dominant_system, entry_ts);
