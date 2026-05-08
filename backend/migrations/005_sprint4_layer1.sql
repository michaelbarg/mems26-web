-- MEMS26 Sprint 4 Layer 1 Migration
-- Adds Primitives fields to setup_attempts
-- Decisions: D-049, D-063, D-064, D-065
-- Date: 9 May 2026
-- Schema lock: docs/MEMS26_SPRINT4_SCHEMA.md V1.0

-- Add Day POC tracking
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS day_poc               FLOAT,
  ADD COLUMN IF NOT EXISTS day_poc_confidence     VARCHAR(10);

-- Add IB tracking
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS ib_width_pts           FLOAT,
  ADD COLUMN IF NOT EXISTS ib_width_class         VARCHAR(10),
  ADD COLUMN IF NOT EXISTS ib_locked              BOOLEAN;

-- Add Opening Type
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS opening_type           VARCHAR(30),
  ADD COLUMN IF NOT EXISTS opening_confidence     VARCHAR(10);

-- Add POC Migration
ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS poc_migration_direction VARCHAR(10),
  ADD COLUMN IF NOT EXISTS poc_migration_points    FLOAT;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_setup_attempts_day_poc
  ON setup_attempts(day_poc);
CREATE INDEX IF NOT EXISTS idx_setup_attempts_opening_type
  ON setup_attempts(opening_type);
CREATE INDEX IF NOT EXISTS idx_setup_attempts_ib_width_class
  ON setup_attempts(ib_width_class);

-- Verify
DO $$
BEGIN
  RAISE NOTICE 'Sprint 4 Layer 1 migration complete';
  RAISE NOTICE 'Added 9 columns to setup_attempts';
  RAISE NOTICE 'Added 3 indexes';
END $$;
