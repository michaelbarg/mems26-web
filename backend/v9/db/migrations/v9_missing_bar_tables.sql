CREATE TABLE IF NOT EXISTS v9_bars_woodies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  open REAL, high REAL, low REAL, close REAL,
  volume INTEGER,
  cci_14 REAL,
  payload TEXT,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_woodies_ts ON v9_bars_woodies(ts);

CREATE TABLE IF NOT EXISTS v9_bars_volume_profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  profile TEXT,
  poc REAL, vah REAL, val REAL,
  total_volume INTEGER,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_volume_profile_ts ON v9_bars_volume_profile(ts);

CREATE TABLE IF NOT EXISTS v9_bars_cumulative_delta (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  delta REAL,
  cumulative REAL,
  direction TEXT,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cumulative_delta_ts ON v9_bars_cumulative_delta(ts);

CREATE TABLE IF NOT EXISTS v9_bars_imbalance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  price REAL,
  ratio REAL,
  direction TEXT,
  bid_vol INTEGER, ask_vol INTEGER,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_imbalance_ts ON v9_bars_imbalance(ts);

CREATE TABLE IF NOT EXISTS v9_bars_stacked_imbalance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  count INTEGER,
  direction TEXT,
  start_price REAL, end_price REAL,
  session TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stacked_imbalance_ts ON v9_bars_stacked_imbalance(ts);
