-- V9_009: Daily quality reports — EOD aggregated stats per system/mode

CREATE TABLE IF NOT EXISTS v9_daily_quality_reports (
    id                  BIGSERIAL PRIMARY KEY,
    date                DATE NOT NULL,
    mode                VARCHAR(10) NOT NULL,
    system_id           INTEGER NOT NULL,
    trade_count         INTEGER DEFAULT 0,
    win_rate            DOUBLE PRECISION,
    profit_factor       DOUBLE PRECISION,
    max_dd              DOUBLE PRECISION,
    recommendations     JSONB,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_v9_quality_unique ON v9_daily_quality_reports (date, mode, system_id);
CREATE INDEX IF NOT EXISTS idx_v9_quality_date ON v9_daily_quality_reports (date);
