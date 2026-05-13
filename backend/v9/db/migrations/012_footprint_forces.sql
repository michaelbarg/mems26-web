-- P-FP-1.1 v3: Footprint aggressive flow columns (passive NULL — Sierra L2 not available)
ALTER TABLE v9_footprint_journal ADD COLUMN agg_buy_vol REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN agg_sell_vol REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN pas_buy_vol REAL DEFAULT NULL;
ALTER TABLE v9_footprint_journal ADD COLUMN pas_sell_vol REAL DEFAULT NULL;
ALTER TABLE v9_footprint_journal ADD COLUMN delta REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN cumulative_delta REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN dominance TEXT;
ALTER TABLE v9_footprint_journal ADD COLUMN cot REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN amt REAL DEFAULT 0;
ALTER TABLE v9_footprint_journal ADD COLUMN forces_source TEXT;
