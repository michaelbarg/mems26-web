-- MEMS26 Sprint 4 — Gate Decisions Log
-- Adds JSONB column to track gate decisions per setup attempt
-- Decision: D-049 (Suffering Side Veto implementation)
-- Date: 9 May 2026

ALTER TABLE setup_attempts
  ADD COLUMN IF NOT EXISTS gate_decisions JSONB DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS idx_setup_attempts_gate_decisions
  ON setup_attempts USING gin(gate_decisions);

DO $$
BEGIN
  RAISE NOTICE 'Migration 006: gate_decisions column added';
END $$;
