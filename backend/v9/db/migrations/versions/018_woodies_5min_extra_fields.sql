-- P31: Persist Sierra woodies_5min.json fields that were JSON-only (proj_hi/lo, HFE, lsma flag)
-- Safe to re-run: duplicate column errors are ignored by migration runner / manual apply.

ALTER TABLE v9_bars_5min_woodies ADD COLUMN proj_hi REAL;
ALTER TABLE v9_bars_5min_woodies ADD COLUMN proj_lo REAL;
ALTER TABLE v9_bars_5min_woodies ADD COLUMN hfe_detected INTEGER DEFAULT 0;
ALTER TABLE v9_bars_5min_woodies ADD COLUMN hfe_direction TEXT DEFAULT 'NONE';
ALTER TABLE v9_bars_5min_woodies ADD COLUMN hfe_extreme_bars_ago INTEGER DEFAULT 0;
ALTER TABLE v9_bars_5min_woodies ADD COLUMN lsma_above_price INTEGER DEFAULT 0;
