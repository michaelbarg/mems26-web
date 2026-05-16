-- PROMPT 4 · 4.1: Woodies Trade Terminal States table
-- Records every terminal state emission from the 21-stage decision tree.
-- 18 distinct terminal states per Decision Tree V1 § Section 6.

CREATE TABLE IF NOT EXISTS woodies_trade_terminals (
    id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(40) NOT NULL,
    terminal_state VARCHAR(40) NOT NULL,
    phase VARCHAR(10) NOT NULL,
    priority_class VARCHAR(20),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bar_context JSONB NOT NULL DEFAULT '{}',
    stage_id VARCHAR(40) NOT NULL,
    direction VARCHAR(10),
    entry_price NUMERIC(10,2),
    exit_price NUMERIC(10,2),
    pnl_points NUMERIC(10,2),
    classification VARCHAR(20),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_terminals_trade_id ON woodies_trade_terminals(trade_id);
CREATE INDEX IF NOT EXISTS idx_terminals_state ON woodies_trade_terminals(terminal_state);
CREATE INDEX IF NOT EXISTS idx_terminals_triggered ON woodies_trade_terminals(triggered_at);
