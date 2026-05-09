-- V9_001: 5-minute OHLCV bars with volume profile data
-- Source: Bridge stream (5min bars from Sierra Chart DLL)

CREATE TABLE IF NOT EXISTS v9_bars_5min (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol          VARCHAR(20) NOT NULL DEFAULT 'MES',
    open            DOUBLE PRECISION NOT NULL,
    high            DOUBLE PRECISION NOT NULL,
    low             DOUBLE PRECISION NOT NULL,
    close           DOUBLE PRECISION NOT NULL,
    volume          INTEGER NOT NULL DEFAULT 0,
    poc_vol         INTEGER,
    vah             DOUBLE PRECISION,
    val             DOUBLE PRECISION,
    cumulative_delta DOUBLE PRECISION,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_bars_5min_ts ON v9_bars_5min (ts);
CREATE INDEX IF NOT EXISTS idx_v9_bars_5min_symbol_ts ON v9_bars_5min (symbol, ts);
