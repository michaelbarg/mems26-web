-- V9_011: Account status — per-mode running PnL, trade count, margin

CREATE TABLE IF NOT EXISTS v9_account_status (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    mode            VARCHAR(10) NOT NULL,
    daily_pnl       DOUBLE PRECISION DEFAULT 0,
    trade_count     INTEGER DEFAULT 0,
    margin_used_pct DOUBLE PRECISION DEFAULT 0,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_account_ts ON v9_account_status (ts);
CREATE INDEX IF NOT EXISTS idx_v9_account_mode_ts ON v9_account_status (mode, ts);
