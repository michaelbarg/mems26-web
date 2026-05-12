CREATE TABLE IF NOT EXISTS v9_footprint_journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  cluster_data TEXT,
  empty_zone_data TEXT,
  accumulation INTEGER DEFAULT 0,
  jumps_count INTEGER DEFAULT 0,
  jumps_direction TEXT,
  otf_state INTEGER,
  pattern_detected TEXT,
  zohar_signals TEXT,
  industry_signals TEXT,
  confluence_total INTEGER DEFAULT 0,
  classification TEXT NOT NULL,
  would_be_entry REAL,
  would_be_stop REAL,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_journal_ts ON v9_footprint_journal(ts);
CREATE INDEX IF NOT EXISTS idx_fp_journal_classification ON v9_footprint_journal(classification);

CREATE TABLE IF NOT EXISTS v9_footprint_setups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  journal_id INTEGER,
  ts TEXT NOT NULL,
  classification TEXT NOT NULL,
  pattern_type TEXT,
  direction TEXT,
  confluence INTEGER,
  entry_price REAL,
  stop_price REAL,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_fp_setups_ts ON v9_footprint_setups(ts);
