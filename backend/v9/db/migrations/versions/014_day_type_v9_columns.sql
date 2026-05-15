-- 3a-S4 REVISED: Add V9 columns to v9_day_type_history
-- Matches DayTypeClassification dataclass (13 fields)
-- Run via: sqlite3 data/mems26_local.db < backend/v9/db/migrations/versions/014_day_type_v9_columns.sql

-- V9 columns (nullable to preserve existing V1 rows)
ALTER TABLE v9_day_type_history ADD COLUMN probability FLOAT;
ALTER TABLE v9_day_type_history ADD COLUMN directional_certainty VARCHAR(8);
ALTER TABLE v9_day_type_history ADD COLUMN trading_confidence VARCHAR(8);
ALTER TABLE v9_day_type_history ADD COLUMN ib_width FLOAT;
ALTER TABLE v9_day_type_history ADD COLUMN ib_width_class VARCHAR(8);
ALTER TABLE v9_day_type_history ADD COLUMN active_zohar_rules JSON DEFAULT '[]';
ALTER TABLE v9_day_type_history ADD COLUMN last_updated_at DATETIME;
ALTER TABLE v9_day_type_history ADD COLUMN updated_at DATETIME;

-- Make status nullable (V1 legacy column, V9 rows won't set it)
-- SQLite doesn't support ALTER COLUMN, so status stays as-is (already has data)

-- Widen reasoning_notes from 512 to 1024 (SQLite ignores length constraints anyway)
