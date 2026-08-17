-- 023 — a 5-minute view that includes the PRE-OPEN, not just RTH.
--
-- Michael 2026-08-17: "עלינו לייצר עוד טבלה במק של 5 דקות הכולל גם לפני פתיחה."
--
-- The data already exists: v9_bars_5min_woodies carries the full 24h (558
-- pre-open bars in the last 7 days alone, from 00:00 ET). What was missing is a
-- way to ASK for it — every consumer in the codebase filters
-- `time >= '09:30'`, so the overnight auction that sets up the open was there
-- and unread.
--
-- Deliberately a VIEW, not a table: a second copy of the bars would drift from
-- the canonical source the moment one of them was backfilled, and this repo has
-- already paid for that (v9_bars_5min vs v9_bars_5min_woodies — SOURCE_OF_TRUTH
-- exists because of it). A view cannot go stale.
--
-- Sessions use the exchange clock (America/New_York), per Rule 4 — no ambiguous
-- "assumed UTC" boundaries:
--   ASIA       18:00 → 03:00   (Globex reopen through the Tokyo session)
--   LONDON     03:00 → 08:00
--   PREOPEN    08:00 → 09:30   (the hour and a half that shapes the open)
--   RTH        09:30 → 16:00
--   POSTCLOSE  16:00 → 18:00
DROP VIEW IF EXISTS v9_bars_5min_sessions;

CREATE VIEW v9_bars_5min_sessions AS
SELECT
    b.ts,
    b.symbol,
    (b.ts AT TIME ZONE 'America/New_York')                       AS ts_et,
    (b.ts AT TIME ZONE 'America/New_York')::date                 AS session_date,
    (b.ts AT TIME ZONE 'America/New_York')::time                 AS et_time,
    CASE
        WHEN (b.ts AT TIME ZONE 'America/New_York')::time >= '18:00'
          OR (b.ts AT TIME ZONE 'America/New_York')::time <  '03:00' THEN 'ASIA'
        WHEN (b.ts AT TIME ZONE 'America/New_York')::time <  '08:00' THEN 'LONDON'
        WHEN (b.ts AT TIME ZONE 'America/New_York')::time <  '09:30' THEN 'PREOPEN'
        WHEN (b.ts AT TIME ZONE 'America/New_York')::time <  '16:00' THEN 'RTH'
        ELSE 'POSTCLOSE'
    END                                                          AS session,
    ((b.ts AT TIME ZONE 'America/New_York')::time <  '09:30'
     AND (b.ts AT TIME ZONE 'America/New_York')::time >= '03:00') AS is_preopen,
    ((b.ts AT TIME ZONE 'America/New_York')::time >= '09:30'
     AND (b.ts AT TIME ZONE 'America/New_York')::time <  '16:00') AS is_rth,
    b.open, b.high, b.low, b.close, b.volume,
    b.cci_14, b.cci_6_tcci, b.ema_34, b.lsma_value,
    b.swi_value, b.czi_value, b.trend_state
FROM v9_bars_5min_woodies b;

COMMENT ON VIEW v9_bars_5min_sessions IS
'5-min bars labelled by exchange session, including PREOPEN. Read-only view over
v9_bars_5min_woodies (the canonical source per docs/SOURCE_OF_TRUTH.md) — never
a second copy of the bars. Michael ruling 2026-08-17.';
