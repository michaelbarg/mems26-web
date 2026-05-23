-- P31 Issue B (2026-05-22): enforce 1 row per 30-min TPO snapshot in v9_tpo_history
-- so the snapshot worker can safely INSERT OR REPLACE without duplicates.
--
-- Background: Issue B requires stepped pink POC/VAH/VAL on the chart, matching
-- Sierra Study ID:3 (developing TPO). Sierra writes only a single live `session`
-- block to tpo.json; per-letter history must be captured by the backend.
-- `TPOHistorySnapshotter` (backend/v9/services/tpo_history_snapshotter.py) takes
-- one snapshot every 30-min boundary during RTH and writes to v9_tpo_history.
--
-- This index lets the worker use INSERT OR REPLACE so re-running the same slot
-- (e.g., after restart catch-up) is idempotent without app-side existence checks.
--
-- See: docs/handoff/CC_INVESTIGATE_TPO_STEPPED_PERIODS.md
--      docs/handoff/SIERRA_STUDIES_CONFIG_2026-05-19.md (Study ID:3)

BEGIN;

-- v9_tpo_history is currently empty (0 rows live as of 2026-05-22 09:30 IL),
-- so no dedupe needed before creating the constraint. Idempotent if migration
-- is re-applied: CREATE INDEX IF NOT EXISTS is a no-op.
CREATE UNIQUE INDEX IF NOT EXISTS ux_v9_tpo_history_ts
  ON v9_tpo_history (ts);

COMMIT;
