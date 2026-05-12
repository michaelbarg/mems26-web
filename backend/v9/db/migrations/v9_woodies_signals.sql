CREATE TABLE IF NOT EXISTS v9_woodies_signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  cci_14 REAL,
  cci_prev REAL,
  signal_type TEXT,
  direction TEXT,
  strength INTEGER,
  reasoning TEXT,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woodies_signals_ts ON v9_woodies_signals(ts);
