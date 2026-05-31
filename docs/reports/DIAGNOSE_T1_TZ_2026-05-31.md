# Diagnosis: T1 TZ Bug in BarLevelDetector

**Date:** 2026-05-31  
**Agent:** Claude Code (Opus 4.6)  
**Type:** DIAGNOSE ONLY — zero code changes  
**Violates:** CLAUDE.md Rule 4 (TZ ambiguity is forbidden)

---

## 1 · Root Cause (verified)

**Naive-vs-aware datetime comparison** at `bar_level_detector.py:91`.

```python
# Line 87-92 (current code):
if bar_ts is not None and trade.entry_ts is not None:
    trade_entry = trade.entry_ts
    if not hasattr(trade_entry, "tzinfo"):  # ← BUG: always True (every datetime has tzinfo attr)
        trade_entry = None
    if trade_entry is not None and bar_ts < trade_entry:  # ← TypeError here
        continue
```

**Chain:**
1. `_market_now_utc()` → returns **tz-aware** datetime (UTC) → stored to `trade.entry_ts`
2. SQLite round-trip strips tzinfo → `trade.entry_ts` comes back **naive**
3. `_parse_ts(bar_ts_string)` → parses ISO with `+00:00` → returns **tz-aware**
4. `bar_ts < trade_entry` → **TypeError: can't compare offset-naive and offset-aware datetimes**
5. Caught by outer `except Exception` (line 127) → silently returns → **T1 never detected**

---

## 2 · Types on Both Sides (empirical)

| Side | Source | Value | tzinfo |
|------|--------|-------|--------|
| `bar_ts` | `_parse_ts("2026-05-31T13:42:18+00:00")` | `datetime(2026,5,31,13,42,18,tzinfo=UTC)` | **aware** |
| `trade.entry_ts` | SQLite read-back of `_market_now_utc()` | `datetime(2026,5,31,13,42,8)` | **naive** (None) |

---

## 3 · Source of Mismatch

| Component | Writes | Reads back as |
|-----------|--------|---------------|
| `TradeManager.on_fill()` | `trade.entry_ts = _market_now_utc()` (aware UTC) | — |
| SQLAlchemy/SQLite | stores ISO string | returns naive datetime (SQLite has no TZ type) |
| `_parse_ts()` | — | parses `+00:00` suffix → aware |
| Bridge bar ts | always UTC with offset (`+00:00` or `Z`) | — |

**SQLite is the TZ-stripper.** It stores aware datetimes as text but reads them back naive.

---

## 4 · Scope: Test-Only or SHADOW Live?

### **SHADOW LIVE IS AFFECTED.**

In production SHADOW mode:
- Bridge sends bars with UTC timestamps (`+00:00`)
- `_parse_ts` produces **aware** datetime
- `trade.entry_ts` from SQLite is **naive**
- TypeError at line 91 → caught silently → **no targets/stops detected**

**This means: BarLevelDetector is currently a no-op in SHADOW.** T1/T2/T3/stop are never detected by this component. (Other components may detect targets via different paths, but BarLevelDetector specifically is broken.)

### Evidence from production DB:

The error message `can't compare offset-naive and offset-aware datetimes` was observed in the diagnostic run with the live DB (334 active trades). Every single one triggered the same TypeError.

---

## 5 · Relationship to Fix 1.6 (commit 9410279)

Fix 1.6 added **subscription to woodies_5min** channel + dedup logic. It solved the problem of BarLevelDetector **not receiving bars at all** (it was only subscribed to the 5min channel, not the woodies_5min channel which fires first).

**It did NOT address the TZ mismatch.** Once bars arrive, the entry guard (lines 87-92) still blocks processing due to TypeError. Fix 1.6 solved "no bars reach the detector" but left "bars that arrive can't be compared" untouched.

---

## 6 · Blast Radius

```
rg "_parse_ts" backend/v9/services/trade_manager/bar_level_detector.py
→ Lines 43, 57, 138 (definition)

rg "bar_ts.*entry_ts|entry_ts.*bar_ts" backend/
→ Only bar_level_detector.py:91
```

**Isolated.** Only `bar_level_detector.py` uses this comparison pattern. No other file compares bar timestamps against trade timestamps this way.

`_parse_ts` is a private method within the class — not exported or used elsewhere.

---

## 7 · Proposed Fix (NOT implemented)

**File:** `backend/v9/services/trade_manager/bar_level_detector.py`  
**Lines:** 87-92

**Option A — Normalize both to naive-UTC (simpler, per Rule 4: explicit TZ at boundary):**
```python
if bar_ts is not None and trade.entry_ts is not None:
    trade_entry = trade.entry_ts
    # Normalize: strip tzinfo for comparison (both are UTC by construction)
    bar_ts_naive = bar_ts.replace(tzinfo=None) if bar_ts.tzinfo else bar_ts
    entry_naive = trade_entry.replace(tzinfo=None) if trade_entry.tzinfo else trade_entry
    if bar_ts_naive < entry_naive:
        continue
```

**Option B — Normalize both to aware-UTC (stricter Rule 4 compliance):**
```python
from datetime import timezone
...
if bar_ts is not None and trade.entry_ts is not None:
    trade_entry = trade.entry_ts
    if trade_entry.tzinfo is None:
        trade_entry = trade_entry.replace(tzinfo=timezone.utc)
    if bar_ts.tzinfo is None:
        bar_ts = bar_ts.replace(tzinfo=timezone.utc)
    if bar_ts < trade_entry:
        continue
```

**Recommendation:** Option B (aware-UTC) — consistent with Rule 4 ("TZ ambiguity is forbidden") and with `_market_now_utc()` convention.

---

## 8 · Regression Coverage Needed

1. **The existing failing test** (`test_bar_level_detector_closes_trades`) becomes the regression — it should PASS after fix.
2. **New test:** Verify that a bar with naive ts (no offset) is also handled correctly (bridge always sends aware, but defensive).
3. **New test:** Verify that a bar with ts BEFORE entry_ts is correctly skipped (the guard's intended behavior).
4. **SHADOW integration:** After fix, verify BarLevelDetector actually detects T1/T2 hits on real bars from the bridge (this can be tested via the existing `test_bar_level_detector_entry_guard.py` tests which already pass in isolation).

---

## Decision Required — Michael

1. **Approve Option A or B** for the TZ normalization.
2. **Acknowledge SHADOW impact:** BarLevelDetector has been a no-op. Once fixed, T1/T2/T3/stop detection activates for all active trades. This is correct behavior (targets should be detected) but changes SHADOW output.
