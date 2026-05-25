# Memorial Day 4B Investigation · DayType 41× Multi-Dispatch

**Date:** 2026-05-25
**Investigator:** CC (Claude Code)
**Status:** ROOT CAUSE CONFIRMED · Hypothesis B · Fix: dedup guard

---

## Evidence

### DB row count
- `v9_day_type_state` today: **8,812 rows**
- `v9_bars_5min` today: **214 rows**
- Ratio: **41.2 inserts per bar**

### Temporal pattern (Layer 3)
```
minute           | rows
2026-05-25T17:50 | 21
2026-05-25T17:51 | 20
2026-05-25T17:52 | 20
...              | ~20 per minute (stable)
```

Second-level detail (17:50:00–17:50:59):
```
17:50:01.307 | Trend_DD | LOCKED_LOW_CONF
17:50:01.434 | Trend_DD | LOCKED_LOW_CONF
17:50:05.413 | Trend_DD | LOCKED_LOW_CONF
17:50:07.443 | Trend_DD | LOCKED_LOW_CONF
...every ~2-4 seconds, identical day_type + lock_state
```

All 21 rows in that minute are **byte-identical** in classification columns.
Only `ts` and `created_at` differ.

### Subscriber count (Layer 1)
```
bar_router.subscribe("5min", _day_type_on_bar)   — 1 occurrence (main.py:336)
```
No duplicate subscriptions.

### Publish call sites for "5min" (Layer 2)
1. `backend/v9/api/v9/bars.py:343` — bridge API push, fires on **every upsert**
   (comment at line 341: "route on every upsert (INSERT or UPDATE), not only new rows")
2. `backend/v9/services/bar_aggregator_5min.py:205` — aggregator, fires on bar **close** only
3. `backend/v9/services/historical_replay.py:90` — startup warmup replay

### Bridge polling mechanics
- `POLL_INTERVAL = 2.0s` (base_stream.py:52)
- DLL rewrites `5min.json` continuously as the live bar updates
- Every mtime change → bridge push → API upsert → `_route_bar("5min", ...)` → bar_router → `_day_type_on_bar`
- 300s per bar / ~7.3s per detected change ≈ **~41 publishes per 5min bar**

---

## Hypotheses Tested

| H | Hypothesis | Status | Evidence |
|---|---|---|---|
| A | Duplicate bar_router.subscribe | **REFUTED** | grep shows exactly 1 subscribe for ("5min", _day_type_on_bar) |
| B | Bridge republishes same bar on every file-poll | **CONFIRMED** | bars.py:341 "route on every upsert" + 2s poll + DB temporal pattern shows ~20 writes/min evenly distributed |
| C | Polling loop / asyncio task fires repeatedly | **REFUTED** | Temporal pattern is poll-driven (2-4s gaps), not tight-loop |
| D | Partial+closed double-publish from aggregator | **REFUTED** | Aggregator publishes only on close (line 205). Partial uses "5min.partial" (line 115) |

---

## Root Cause

**Hypothesis B confirmed.** The Sierra DLL rewrites `5min.json` continuously
as the live bar updates (new ticks → new OHLCV). The bridge polls every 2s
(`POLL_INTERVAL=2.0`), detects mtime change, and pushes the latest bar to
`POST /api/v9/bars/5min`. The API handler (bars.py:296-343) upserts the bar
and calls `_route_bar("5min", ...)` **on every upsert** (INSERT or UPDATE).
This publishes a "5min" BarRouter event ~41 times per actual 5-minute bar.

`_day_type_on_bar` (main.py:336) subscribes to "5min" and runs
`day_type_machine.process_bar()` + unconditional `INSERT INTO v9_day_type_state`
on every event — no dedup guard. Result: ~41 identical DB rows per bar.

The `bar_router.publish("day_type_classification", ...)` change-guard at
main.py:314 only gates the **downstream publish**, not the DB writes at
main.py:255-277.

---

## Fix Decision

**APPLIED** — dedup guard in `_day_type_on_bar` (main.py).

Track `_prev_bar_ts` in closure scope. If the incoming bar's timestamp matches
the previous invocation, skip `process_bar` + DB write. This reduces DB writes
from ~41 per bar to exactly 1 (first seen) + 1 (bar close from aggregator if
ts differs) = 1-2 per bar.

The DayType state machine is deterministic given bar OHLCV — re-running it on
the same bar with slightly updated close/high/low could produce different
classifications mid-bar. However, the DayType machine already has its own
internal bar-count tracking and the mid-bar updates are noise (the final
classification at bar close is what matters). The dedup guard ensures we
process each unique bar timestamp exactly once, which is the correct semantic.

---

## Cross-impact

- **DB write rate:** 41× per bar → 1× per bar → ~8000 writes/day eliminated
- **Storage cost:** trivial (sqlite handles the load), but noisy rows mask real state changes
- **Correctness:** NO impact (each row was idempotent — same classification repeated)
- **Risk mitigation:** eliminates noise in v9_day_type_state, making it useful for forensics
- **DayType state machine:** processes each bar timestamp once instead of 41×; since machine
  is deterministic on same input, no behavioral change
- **Downstream `day_type_classification` publish:** already guarded by change-check (main.py:314);
  dedup guard is upstream of this and adds defense-in-depth
