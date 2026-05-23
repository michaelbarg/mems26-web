-- P30 G8 (2026-05-20): enforce per-bar uniqueness on v9_bars_5min
-- so concurrent bridge POSTs cannot race two rows for the same minute.
--
-- Investigation: live cockpit at 2026-05-19 ~23:50 ET threw a
--   `lightweight-charts: data must be asc ordered by time, index=597,
--    time=1779198300, prev time=1779198300`
-- because v9_bars_5min held two rows with ts='2026-05-19 16:45:00.000000'.
-- The SELECT-then-INSERT path in bars.py:post_bars_5min could not see
-- the other bridge POST yet, so both POSTs added a row.
--
-- This migration:
--   (a) deletes any existing duplicates (keep smallest id per ts+symbol),
--   (b) creates a UNIQUE INDEX on (ts, symbol).
--
-- Companion app code change: backend/v9/api/v9/bars.py:post_bars_5min
-- now catches sqlalchemy.exc.IntegrityError on the race and retries as
-- an UPDATE.

BEGIN;

-- (a) dedupe
DELETE FROM v9_bars_5min
WHERE id NOT IN (
  SELECT MIN(id) FROM v9_bars_5min GROUP BY ts, symbol
);

-- (b) UNIQUE INDEX (idempotent — IF NOT EXISTS)
CREATE UNIQUE INDEX IF NOT EXISTS ux_v9_bars_5min_ts_symbol
  ON v9_bars_5min (ts, symbol);

COMMIT;
