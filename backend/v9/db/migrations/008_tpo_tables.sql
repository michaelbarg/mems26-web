CREATE TABLE IF NOT EXISTS v9_tpo_sessions (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   TEXT    NOT NULL,
  session_type TEXT    NOT NULL,
  trading_date TEXT    NOT NULL,
  opened_ts    DATETIME NOT NULL,
  closed_ts    DATETIME,
  poc_price    REAL,
  vah_price    REAL,
  val_price    REAL,
  range_high   REAL,
  range_low    REAL,
  total_volume INTEGER,
  profile_shape TEXT,
  opening_type  TEXT,
  ib_high       REAL,
  ib_low        REAL,
  ib_locked     INTEGER DEFAULT 0,
  letter_count  INTEGER DEFAULT 0,
  UNIQUE(session_id)
);

CREATE TABLE IF NOT EXISTS v9_tpo_journal (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   TEXT    NOT NULL,
  ts           DATETIME NOT NULL,
  letter       TEXT    NOT NULL,
  price_low    REAL    NOT NULL,
  price_high   REAL    NOT NULL,
  is_single_print INTEGER DEFAULT 0,
  FOREIGN KEY (session_id) REFERENCES v9_tpo_sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_tpo_journal_session ON v9_tpo_journal(session_id);
CREATE INDEX IF NOT EXISTS idx_tpo_sessions_date ON v9_tpo_sessions(trading_date);
