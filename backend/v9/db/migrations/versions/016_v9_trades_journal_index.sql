-- P31-04: journal /trades/log — filter by mode + sort by entry_ts
CREATE INDEX IF NOT EXISTS ix_v9_trades_mode_entry_ts
    ON v9_trades (mode, entry_ts DESC, id DESC);
