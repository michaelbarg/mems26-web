# Chart Bug + Day Type Detection · 2026-06-01

**Date:** 2026-06-01 (RTH) · **Author:** CC

---

## Part A — Chart null crash (FIXED)

**Bug:** `Cannot read properties of null (reading 'setData')` at `ChartV5b.tsx:552`
**Root:** `candleRef.current` is null when `loadBars` runs before series created or after unmount.
**Fix:** Added `if (!candleRef.current) return;` guard before `setData` call.
**Commit:** `aa8291f`

---

## Part B — Day Type Detection Stuck at A1

### Live State (10:06 ET, ~36 min into RTH)
```
stage: A1
day_type: UNKNOWN
bar_count: 0
opening_type: UNKNOWN
ib_locked: false
ib_high: null
ib_low: null
confidence: 0.0
vote_history: []
```

### Root Cause: DayType `_day_type_on_bar` callback not firing after restart

**Evidence:**
- Before last restart: `_day_type_on_bar` WAS firing (SLOW handler warnings in log)
- After restart: ZERO `_day_type_on_bar` calls in log
- Other BarRouter subscribers (TPO, Footprint, FiveMin) ARE receiving bars
- Startup log shows only 6 lines (no system init messages due to suppressed logging)

**Hypothesis:** The DayType initialization block (main.py:141-339) throws an exception that's caught by its `try/except`, causing:
1. `day_type_machine` never created or partially created
2. `bar_router.subscribe("5min", _day_type_on_bar)` never executed
3. Silent failure — no error visible because `mems26` logger not at INFO level in LaunchAgent

**Contributing factor:** `.env` not loading in LaunchAgent → logging configuration missing → init errors suppressed.

### Classification: **BUG** (silent initialization failure)

### Recommended Fix
1. **Add explicit `print()` statements** to the DayType init block (not logger — print goes to stdout/stderr regardless of config)
2. **OR** add `logging.basicConfig(level=logging.INFO)` at top of main.py to ensure the mems26 logger works without `.env`
3. Restart and identify the specific exception

### POC/VAH/VAL = None
**Same root cause** as Woodies fix: `arr[sc.Index]` reads misaligned index from cross-chart study arrays. Fix committed (`4984cd1`) but Michael needs to do **Remote Build** for the TPO/IB study reading fix.

**Michael — please do Remote Build for the TPO fix** (already deployed to ACS_Source, just needs build + reload).

### Active Trade Status
Trade #18 (S3 SHORT @7588.25) **survived restart** — persisted in DB and active endpoint returns it. BarLevelDetector continues monitoring.

---

## Strategic Stop

Day Type logic change requires Michael's approval. The current issue is **infrastructure** (silent init failure), not spec deviation. Once the init error is fixed and the machine receives bars, it should classify per spec.

**Next steps (after Michael's Remote Build for TPO fix):**
1. Add diagnostic print to DayType init block
2. Restart and capture the specific error
3. Fix the init error
4. Verify DayType advances past A1 with real bar data

---

*Part A committed. Part B diagnosis complete — awaiting TPO Remote Build + init error diagnosis.*
