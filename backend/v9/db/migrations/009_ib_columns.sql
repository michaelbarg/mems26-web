-- P3.1: Add IB tracking columns to v9_tpo_sessions
-- Safe to re-run (uses ALTER TABLE ADD COLUMN which fails on duplicate)
ALTER TABLE v9_tpo_sessions ADD COLUMN ib_width REAL;
ALTER TABLE v9_tpo_sessions ADD COLUMN ib_class TEXT;
ALTER TABLE v9_tpo_sessions ADD COLUMN ib_locked_ts TEXT;
