-- V9_008: Trade management log — tracks stop moves, partials, adjustments
-- FK to v9_trades

CREATE TABLE IF NOT EXISTS v9_trade_management_log (
    id          BIGSERIAL PRIMARY KEY,
    trade_id    BIGINT NOT NULL REFERENCES v9_trades(id) ON DELETE CASCADE,
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    action      VARCHAR(30) NOT NULL,   -- STOP_MOVED, T1_FILLED, T2_FILLED, TRAIL_ADJUSTED, MANUAL_EXIT
    value       JSONB,                  -- action-specific data (old_stop, new_stop, etc.)
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_v9_trade_log_trade ON v9_trade_management_log (trade_id);
CREATE INDEX IF NOT EXISTS idx_v9_trade_log_ts ON v9_trade_management_log (ts);
