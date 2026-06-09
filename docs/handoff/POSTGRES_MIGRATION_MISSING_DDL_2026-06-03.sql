-- v9_bars_cumulative_delta
CREATE TABLE v9_bars_cumulative_delta (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  delta REAL,
  cumulative REAL,
  direction TEXT,
  session TEXT,
  created_at TEXT NOT NULL
);

-- v9_bars_imbalance
CREATE TABLE v9_bars_imbalance (
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

-- v9_bars_stacked_imbalance
CREATE TABLE v9_bars_stacked_imbalance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  count INTEGER,
  direction TEXT,
  start_price REAL, end_price REAL,
  session TEXT,
  created_at TEXT NOT NULL
);

-- v9_bars_volume_profile
CREATE TABLE v9_bars_volume_profile (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  bar_id TEXT UNIQUE,
  profile TEXT,
  poc REAL, vah REAL, val REAL,
  total_volume INTEGER,
  session TEXT,
  created_at TEXT NOT NULL
);

-- v9_bars_woodies
CREATE TABLE v9_bars_woodies (
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

-- v9_build_status_archive
CREATE TABLE v9_build_status_archive (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            trading_date TEXT NOT NULL,
            snapshot_ts  TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            archived_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

-- v9_chop_score
CREATE TABLE v9_chop_score (
  ts TEXT PRIMARY KEY,
  vegas_flips_60m INTEGER,
  cci_zl_crossings_30m INTEGER,
  poc_migration_stuck INTEGER,
  ib_breakouts_recent INTEGER,
  range_atr_ratio REAL,
  poc_vwap_distance REAL,
  composite_score REAL
);

-- v9_day_type_archive
CREATE TABLE v9_day_type_archive (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            date                  DATE    NOT NULL,
            day_type              VARCHAR(32) NOT NULL,
            status                VARCHAR(16),
            confidence            FLOAT,
            ib_high               FLOAT,
            ib_low                FLOAT,
            ib_width_ticks        INTEGER,
            opening_type          VARCHAR(32),
            locked_at             DATETIME,
            reasoning_notes       VARCHAR(1024),
            created_at            DATETIME,
            probability           FLOAT,
            directional_certainty VARCHAR(8),
            trading_confidence    VARCHAR(8),
            ib_width              FLOAT,
            ib_width_class        VARCHAR(8),
            active_zohar_rules    TEXT,
            last_updated_at       DATETIME,
            updated_at            DATETIME,
            archived_at           TEXT NOT NULL DEFAULT (datetime('now'))
        );

-- v9_day_type_shadow_transitions
CREATE TABLE v9_day_type_shadow_transitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        session_date TEXT NOT NULL,
        session_min INTEGER,
        from_type TEXT NOT NULL,
        to_type TEXT NOT NULL,
        trigger TEXT NOT NULL,
        e_up REAL, e_dn REAL, r_total REAL,
        ib_w REAL, ib_h REAL, ib_l REAL,
        vah REAL, val REAL, poc REAL, cvd REAL, price REAL,
        created_at TEXT
    );

-- v9_day_type_state
CREATE TABLE v9_day_type_state (
	id INTEGER NOT NULL, 
	ts DATETIME NOT NULL, 
	stage VARCHAR(20) NOT NULL, 
	day_type VARCHAR(20), 
	classification VARCHAR(30), 
	confidence FLOAT, 
	ib_width_class VARCHAR(10), 
	opening_type VARCHAR(30), 
	behavior VARCHAR(30), 
	lock_state VARCHAR(20), 
	meta JSON, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id)
);

-- v9_footprint_journal
CREATE TABLE v9_footprint_journal (
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
, agg_buy_vol REAL DEFAULT 0, agg_sell_vol REAL DEFAULT 0, delta REAL DEFAULT 0, cumulative_delta REAL DEFAULT 0, dominance REAL DEFAULT 0, cot REAL DEFAULT 0, amt REAL DEFAULT 0, forces_source REAL DEFAULT 0, pas_buy_vol REAL DEFAULT NULL, pas_sell_vol REAL DEFAULT NULL, initiative_type TEXT, combined_class TEXT, reactive_flag INTEGER DEFAULT 0);

-- v9_footprint_setups
CREATE TABLE v9_footprint_setups (
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

-- v9_reversal_enrichment
CREATE TABLE v9_reversal_enrichment (
  bar_ts TEXT PRIMARY KEY,
  bar_type TEXT,
  cluster_top REAL,
  cluster_bottom REAL,
  cluster_volume REAL,
  empty_zone_top REAL,
  empty_zone_bottom REAL,
  empty_zone_volume REAL,
  poc_price REAL
);

-- v9_session_meta
CREATE TABLE v9_session_meta (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        );

-- v9_tpo_journal
CREATE TABLE v9_tpo_journal (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   TEXT    NOT NULL,
  ts           DATETIME NOT NULL,
  letter       TEXT    NOT NULL,
  price_low    REAL    NOT NULL,
  price_high   REAL    NOT NULL,
  is_single_print INTEGER DEFAULT 0,
  FOREIGN KEY (session_id) REFERENCES v9_tpo_sessions(session_id)
);

-- v9_tpo_sessions
CREATE TABLE v9_tpo_sessions (
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
  letter_count  INTEGER DEFAULT 0, ib_width REAL, ib_class TEXT, ib_locked_ts TEXT, poc_migration TEXT, hvn_zones TEXT, lvn_zones TEXT, volume_cluster TEXT, previous_poc TEXT, poc_stuck_since TEXT,
  UNIQUE(session_id)
);

-- v9_tpo_sessions_archive
CREATE TABLE v9_tpo_sessions_archive (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    TEXT    NOT NULL,
            session_type  TEXT    NOT NULL,
            trading_date  TEXT    NOT NULL,
            opened_ts     DATETIME NOT NULL,
            closed_ts     DATETIME,
            poc_price     REAL,
            vah_price     REAL,
            val_price     REAL,
            range_high    REAL,
            range_low     REAL,
            total_volume  INTEGER,
            profile_shape TEXT,
            opening_type  TEXT,
            ib_high       REAL,
            ib_low        REAL,
            ib_locked     INTEGER DEFAULT 0,
            letter_count  INTEGER DEFAULT 0,
            archived_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

-- v9_woodies_signals
CREATE TABLE v9_woodies_signals (
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
, czi_state TEXT, swi_state TEXT, persistence_bars INTEGER DEFAULT 0, signal_type_core TEXT, signal_confidence REAL DEFAULT 0, is_synthetic INTEGER NOT NULL DEFAULT 0);

-- v9_woodies_signals_archive
CREATE TABLE v9_woodies_signals_archive (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            bar_id      TEXT,
            cci_14      REAL,
            cci_prev    REAL,
            signal_type TEXT,
            direction   TEXT,
            strength    INTEGER,
            reasoning   TEXT,
            session     TEXT,
            created_at  TEXT NOT NULL,
            archived_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

