-- V9_002: Tick reversal bars (15-tick and 12-tick)
-- Source: Bridge streams tick_reversal_15, tick_reversal_12

CREATE TABLE IF NOT EXISTS v9_bars_tick_reversal (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol          VARCHAR(20) NOT NULL DEFAULT 'MES',
    tick_size       INTEGER NOT NULL,  -- 15 or 12
    open            DOUBLE PRECISION NOT NULL,
    high            DOUBLE PRECISION NOT NULL,
    low             DOUBLE PRECISION NOT NULL,
    close           DOUBLE PRECISION NOT NULL,
    volume          INTEGER NOT NULL DEFAULT 0,
    ask_vol         INTEGER,
    bid_vol         INTEGER,
    delta           DOUBLE PRECISION,
    direction       SMALLINT,  -- 1=up, -1=down
    footprint_json  JSONB,     -- bid×ask per price level
    cluster_data    JSONB,     -- cluster detection results
    empty_zones     JSONB,     -- empty zone detection results
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_bars_tr_ts ON v9_bars_tick_reversal (ts);
CREATE INDEX IF NOT EXISTS idx_v9_bars_tr_tick_ts ON v9_bars_tick_reversal (tick_size, ts);
CREATE INDEX IF NOT EXISTS idx_v9_bars_tr_symbol_ts ON v9_bars_tick_reversal (symbol, tick_size, ts);
