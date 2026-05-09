-- V9_003: 30-minute Woodies CCI bars
-- Source: Bridge (woodies_30min.json from DLL)

CREATE TABLE IF NOT EXISTS v9_bars_30min_woodies (
    id                  BIGSERIAL PRIMARY KEY,
    ts                  TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol              VARCHAR(20) NOT NULL DEFAULT 'MES',
    open                DOUBLE PRECISION NOT NULL,
    high                DOUBLE PRECISION NOT NULL,
    low                 DOUBLE PRECISION NOT NULL,
    close               DOUBLE PRECISION NOT NULL,
    volume              INTEGER NOT NULL DEFAULT 0,
    cci_14              DOUBLE PRECISION,
    cci_6_tcci          DOUBLE PRECISION,
    lsma_value          DOUBLE PRECISION,
    swi_value           DOUBLE PRECISION,
    czi_value           DOUBLE PRECISION,
    ema_34              DOUBLE PRECISION,
    trend_state         VARCHAR(10),  -- BLUE, RED, GRAY, YELLOW
    predictor_next_cci  DOUBLE PRECISION,
    zlr_detected        BOOLEAN DEFAULT FALSE,
    zlr_direction       VARCHAR(10),  -- UP, DOWN, NONE
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_woodies_ts ON v9_bars_30min_woodies (ts);
CREATE INDEX IF NOT EXISTS idx_v9_woodies_symbol_ts ON v9_bars_30min_woodies (symbol, ts);
