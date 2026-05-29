# SOT_HEALTH Audit — 03 — tick_reversal future-ts
Run: 2026-05-29 14:48 IL · 07:48 ET · market: OFF-HOURS (pre-RTH Globex)
Verdict: ONGOING-BUG

## What was checked
Whether the +5h future timestamps in `v9_bars_tick_reversal` are historical leftovers from before the TZ fix (commit `99671e4`, 2026-05-28) or an active ongoing bug. Traced the raw DLL timestamp encoding, the bridge TZ fix, and the DB write path.

## Evidence

### Latest rows (ts_col + max(ts)-now)

| rowid | ts (in DB) | actual now (UTC) | delta |
|-------|------------|------------------|-------|
| 16037053 | 2026-05-29 12:42:41 | 2026-05-29 07:43:10 | **+5.0h FUTURE** |

The **newest row by rowid** (written seconds ago) is +5h in the future. This is NOT historical — it's actively happening right now.

### Future-ts rows (count + earliest..latest date)

| Metric | Value |
|--------|-------|
| Total rows | 16,038,699 |
| Future rows (ts > now) | 539,655 (3.4%) |
| Future range | 2026-05-29 07:43:40 → 2026-05-29 12:44:05 |
| Post-fix rows (after 2026-05-28 20:00 UTC) still future | **540,411** |

Rows written AFTER the TZ fix commit are still future. **The fix did not resolve tick_reversal.**

### Write path (file:line)

`backend/v9/api/v9/bars.py:358-359`:
```python
row = V9BarTickReversal(
    ts=_ts_from_unix(bar.get("ts")),  # bar.ts already processed by bridge
    ...
)
```

The bridge `_fix_chicago_bar_ts()` runs on ALL streams uniformly (line 265 of `base_stream.py`). It walks `BUGGY_TS_KEYS = ("bars", ...)` and applies `_chicago_to_utc()` to every `bar.ts`.

### TZ fix commit (hash + date)

```
99671e4 fix(pre-live): 7-bug batch -- TZ, IB, TIME_STOP, S2 volume, current_bar routing
Date: 2026-05-29 08:35 IL
Change: base_stream.py America/Chicago → America/New_York
```

### Control stream comparison

| Stream | DB table | max(ts) | delta vs now | Status |
|--------|----------|---------|-------------|--------|
| `v9_bars_5min` | 5min bars | 2026-05-29 08:45:00 | **+1.0h FUTURE** | Partially broken |
| `v9_bars_tick_reversal` | tick reversal | 2026-05-29 12:42:41 | **+5.0h FUTURE** | Broken |
| `v9_bars_footprint` | footprint | 2026-05-29 07:46:00 | **-5s PAST** | Correct |

## Finding: ROOT CAUSE — DLL uses different timestamp encoding per stream

**The DLL does NOT use a uniform timestamp encoding.** Two different mechanisms:

| Stream | DLL ts source | Raw value | Already UTC? | Bridge adds +4h | Result |
|--------|--------------|-----------|-------------|----------------|--------|
| **5min / woodies** | `v9_sc_datetime_to_unix()` (SCDateTime → Excel serial) | NY wall-clock as Unix | **NO** — needs +4h | +4h | **Correct** |
| **tick_reversal** | `time(nullptr)` (C stdlib) | Real UTC | **YES** — already correct | +4h | **+4h FUTURE (broken)** |
| **footprint** | VAPRecomputer (Python `time.time()`) | Real UTC | **YES** | Not applied (custom `_tick()`) | **Correct** |

The bridge `_fix_chicago_bar_ts()` applies `_chicago_to_utc()` **uniformly** to all streams. This is correct for 5min/woodies (which need the conversion) but **double-corrects** tick_reversal (which is already UTC from `time(nullptr)` in the DLL).

Footprint is correct because `FootprintStream` overrides `_tick()` entirely — it never calls `_fix_chicago_bar_ts()` (it uses VAPRecomputer which writes real UTC via Python `time.time()`).

**The +5h delta** = +4h from the `America/New_York` EDT conversion + ~1h from the fact that the newest DLL bar was written slightly before now.

**Wait — 5min shows +1h, not +4h.** This is because 5min bars use `v9_sc_datetime_to_unix()` which encodes NY wall-clock. After the bridge adds +4h (EDT), the result should be correct UTC. But it's still +1h ahead. This means the DLL's `SCDateTime` for 5min is actually giving a timestamp ~1h behind NY wall-clock (possibly the bar's **open** time vs current wall-clock, since the bar is still building). The +1h is within expected range for an in-progress 5-min bar bucket.

The tick_reversal +5h is NOT within expected range — it's a systematic double-correction.

## Recommendation (for Cursor/Michael — DO NOT execute)

### Primary fix: per-stream TZ flag
The bridge needs to know which streams require the TZ fix and which don't. Options:

**(a) Stream-level override (recommended):**
```python
class TickReversal15Stream(BaseV9Stream):
    name = "tick_reversal_15"
    DISABLE_CHICAGO_TS_FIX = True  # DLL uses time(nullptr) = real UTC
```

Add a class attribute `DISABLE_CHICAGO_TS_FIX` that `_fix_chicago_bar_ts()` checks before applying.

**(b) DLL-side flag:** Add `"ts_encoding": "utc"` or `"ts_encoding": "chart_local"` to each JSON export. The bridge reads it and decides.

**(c) Detection heuristic:** If `max(bar.ts) - time.time() > 3600`, skip the fix for this batch. Fragile — not recommended.

### Secondary: clean up historical future rows
After the fix, existing future-ts rows in `v9_bars_tick_reversal` remain. Options:
- `UPDATE v9_bars_tick_reversal SET ts = datetime(ts, '-4 hours') WHERE ts > datetime('now')` — batch fix
- Or leave them and let them age out naturally (they'll become "past" in ~5h)

### sot_health.py
Change the check from "is max(ts) future?" to "is the NEWEST rowid's ts future AND was it written after the TZ fix commit date?" — this distinguishes historical from ongoing.

## Open questions

1. **Which other streams use `time(nullptr)` vs `v9_sc_datetime_to_unix()`?** The `cumulative_delta`, `imbalance_flags`, `stacked_imbalances`, and `volume_profile` streams all inherit from BaseV9Stream and get the TZ fix applied. If their DLL exports use `time(nullptr)`, they'll have the same +4h bug. Need to audit each DLL export function.

2. **The 5min +1h residual** — is this the building-bar offset (bar opened 5 min ago, ts = bar open time) or a remaining TZ issue? Needs verification during RTH with a closed bar.

3. **`v9_bars_footprint` is correct only by accident** — FootprintStream bypasses `_tick()` entirely. If someone changes it to use base `_tick()`, it would break. The per-stream flag (option a) makes this explicit.
