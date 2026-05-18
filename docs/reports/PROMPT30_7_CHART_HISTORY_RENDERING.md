# P30.7 — Chart History Rendering Fix

**Date:** 2026-05-18  
**Status:** GREEN — detached live candle blocked; all available 5m history loaded on open  
**No bridge started. No SHADOW/DEMO/LIVE activation. No trade command writes.**

---

## Root Cause

The chart data endpoint was healthy, but the visual chart looked wrong because:

1. `ChartV5b` created a forming candle using `Date.now()` whenever a price tick
   arrived, even if the latest DB bar was stale.
2. The local DB history is incomplete. Current `v9_bars_5min` state:
   - count: `556`
   - min: `2026-05-12 07:50:00.000000`
   - max: `2026-05-17 16:15:00.000000`
   - recent rows have real gaps, e.g. `16:10` -> `15:15` -> `15:10`.
3. The initial chart request loaded only 240 bars, so the visible history was
   smaller than the data available locally.

---

## Fix

- `ChartV5b` now tracks the latest historical DB bar timestamp.
- It skips detached forming candles when the live bucket is more than 3 chart
  buckets ahead of the latest DB bar.
- Initial 5m history load now requests `600` bars, the backend maximum, so all
  currently available 556 local bars are loaded.

---

## Verification

Endpoint verification:

```text
/api/v9/chart/bars5min?limit=600
latency_ms=119.49
endpoint_count=556
db_count=556
bad_count=0
latest_ts=2026-05-17 16:15:00.000000
recency_match=True
```

Browser verification:

- Chart reload succeeded.
- 5m candles are visible.
- More historical candles are visible after loading `600` instead of `240`.
- The remaining gaps reflect missing DB bars, not a rendering failure.

History continuity audit:

```text
v9_bars_5min rows: 556
min_ts: 2026-05-12 07:50:00.000000
max_ts: 2026-05-17 16:15:00.000000
gaps_gt_5m: 38
largest_gap: 2026-05-16 11:05:00 -> 2026-05-17 14:00:00 (1615 minutes)
recent_gap_examples:
  2026-05-17 15:15:00 -> 2026-05-17 16:10:00 (55 minutes)
  2026-05-17 14:40:00 -> 2026-05-17 15:10:00 (30 minutes)
```

Available local exports checked:

- `/Users/michael/SierraChart_Data/v9_export/woodies_5min.json` contains only
  `total_bars=3`, not enough for chart history.
- `/Users/michael/SierraChart_Data/v9_export/cumulative_delta.json` is point
  data, not OHLC history.
- `/Users/michael/SierraChart_Data/v9_export/mes_ai_data.json` contains current
  MTF snapshots, not historical 5m bars.
- No `5min.json` history export was present in `v9_export`.

---

## Residual

To make the chart truly continuous, the missing Sierra/DB bars must be collected
or backfilled. The frontend now displays all available local 5m data honestly;
it does not synthesize missing trading bars.

Do not fill gaps with synthetic candles. A real fix requires one of:

- Sierra/SCID historical export/import for 5m OHLCV.
- A dedicated DLL export that writes enough 5m history.
- A controlled backfill script that upserts validated bars into `v9_bars_5min`
  and then reruns the four UAT axes.
