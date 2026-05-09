-- V9_004: TPO (Time Price Opportunity) bars
-- Source: System 5 — TPO data provider

CREATE TABLE IF NOT EXISTS v9_tpo_bars (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol      VARCHAR(20) NOT NULL DEFAULT 'MES',
    letter      CHAR(1) NOT NULL,       -- A-Z TPO letter
    price       DOUBLE PRECISION NOT NULL,
    level       INTEGER NOT NULL,        -- price level index
    period_id   INTEGER NOT NULL,        -- 30-min period within session
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_tpo_ts ON v9_tpo_bars (ts);
CREATE INDEX IF NOT EXISTS idx_v9_tpo_period ON v9_tpo_bars (period_id, ts);
CREATE INDEX IF NOT EXISTS idx_v9_tpo_symbol_ts ON v9_tpo_bars (symbol, ts);
