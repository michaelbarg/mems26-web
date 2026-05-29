# Fix Report — S2 Volume Key Mismatch + Inspector Gates · 2026-05-28

**Author:** Claude Code
**Priority:** CRITICAL — S2 pattern detection was silently broken since initial wiring
**Scope:** 3 fixes, 3 files, 3 lines changed

---

## Root Cause

S2 (FiveMin) pattern detectors have **never seen volume data** in production.

The bridge sends bars with field name `"vol"`. The `process_bar()` method stores it
as `"vol"` (line 697). But all 10 pattern detectors read `b.get("v", 0)` — looking
for key `"v"` which doesn't exist in the buffer. Result: **volume is always 0**.

This silently blocks:
- **Reactive LONG/SHORT** — requires `b1.volume > 0` AND 90% volume drop on Bar 2
- **Initiative LONG/SHORT** — requires volume > 0 for COT/AMT calculations
- **All lookback volume checks** — `max(b.get("v", 0) for b in lookback)` always returns 0

**Every S2 pattern that depends on volume has been impossible to fire.**

---

## Fixes Applied

### Fix 1 — Volume key alias (CRITICAL)

**File:** `backend/v9/systems/five_min/five_min_system.py:698`
**Change:** Added `bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))` after existing `"vol"` setdefault

```python
# Before (line 697 only):
bar.setdefault("vol", bar.get("volume", 0))

# After (line 697-698):
bar.setdefault("vol", bar.get("volume", 0))
bar.setdefault("v", bar.get("vol", bar.get("volume", 0)))
```

**Why this approach:** The detectors use `"v"`, the bridge sends `"vol"`, the DB column is `"volume"`. Rather than changing all detector code (10+ call sites across 3 files), we add the alias at the single ingestion point. Both `"vol"` and `"v"` now resolve to the same value.

**Impact:** All 10 S2 pattern detectors can now see volume. Reactive/Initiative patterns become possible to fire.

### Fix 2 — Inspector mode gate (DISPLAY)

**File:** `backend/v9/systems/build_status/s2_inspector.py:114`
**Change:** Added `DAY_TYPE_MODE` to accepted trading modes

```python
# Before:
mode_trading = mode_str in ("FIRST_HOUR_TACTICAL", "INTRADAY")

# After:
mode_trading = mode_str in ("FIRST_HOUR_TACTICAL", "DAY_TYPE_MODE", "INTRADAY")
```

**Why:** `DAY_TYPE_MODE` is the standard post-first-hour mode. The inspector was reporting patterns as "blocked" when they were actually running normally.

### Fix 3 — Inspector FHB gate after first hour (DISPLAY)

**File:** `backend/v9/systems/build_status/s2_inspector.py:101-103`
**Change:** FHB check bypassed when mode is past first hour

```python
# Before:
fhb_eligible = fhb_state_val not in ("ACCUMULATING", "UNKNOWN")

# After:
fhb_eligible = mode_str in ("DAY_TYPE_MODE", "INTRADAY") or fhb_state_val not in ("ACCUMULATING", "UNKNOWN")
```

**Why:** After the first hour, FHB is irrelevant — its bar counter stays at 0 if backend restarted mid-session, causing a false "blocked" in the inspector.

---

## Regression

- 962 passed, 1 skipped — my fixes introduce 0 new failures
- 11 pre-existing failures from other uncommitted work (day_type state machine + IB changes)

## Verification

```
# DB confirms volume exists in all 198 bars today:
sqlite3 data/mems26_local.db \
  "SELECT COUNT(*), SUM(CASE WHEN volume=0 THEN 1 ELSE 0 END) FROM v9_bars_5min WHERE date(ts)='2026-05-28'"
→ 198 total, 0 zero-volume

# DLL export confirms field name is "vol":
python3 -c "import json; d=json.load(open('~/SierraChart_Data/v9_export/5min.json')); print(list(d['bars'][-1].keys()))"
→ ['ts', 'o', 'h', 'l', 'c', 'vol', ...]

# Detectors read "v" (not "vol"):
rg '\.get\("v"' backend/v9/systems/five_min/five_min_system.py
→ lines 446, 447, 465, 466, 522, 543, 544 — all use "v"
```

---

## Summary

**באג קריטי: S2 מעולם לא ראה volume.** הבריידג' שולח `"vol"`, הדיטקטורים קוראים `"v"` — כל בדיקת volume החזירה 0. תוקן בשורה אחת: `bar.setdefault("v", ...)`. שני תיקוני תצוגה נוספים ב-inspector (mode gate + FHB gate). אפס רגרסיות חדשות.
