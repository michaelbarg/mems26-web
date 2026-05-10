-- V9_012: Dedicated footprint bars table (was incorrectly stored in v9_bars_tick_reversal with tick_size=0)

CREATE TABLE IF NOT EXISTS v9_bars_footprint (
    id            BIGSERIAL PRIMARY KEY,
    ts            TIMESTAMPTZ NOT NULL,
    symbol        VARCHAR(20) NOT NULL DEFAULT 'MES',
    open          DOUBLE PRECISION NOT NULL,
    high          DOUBLE PRECISION NOT NULL,
    low           DOUBLE PRECISION NOT NULL,
    close         DOUBLE PRECISION NOT NULL,
    volume        INTEGER NOT NULL DEFAULT 0,
    delta         DOUBLE PRECISION,
    poc_price     DOUBLE PRECISION,
    poc_vol       INTEGER,
    levels        JSONB,
    stacked_buy   INTEGER,
    stacked_sell  INTEGER,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_v9_bars_footprint_ts ON v9_bars_footprint (ts);
CREATE INDEX idx_v9_bars_footprint_symbol_ts ON v9_bars_footprint (symbol, ts);
