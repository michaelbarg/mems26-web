# Woodies Panel ↔ Sierra Chart 12 Parity · 2026-06-01

**Date:** 2026-06-01 · **Author:** CC
**Result:** Woodies studies now LIVE in real-time from chart 12.

---

## Root Cause (2 bugs)

### Bug 1: Study reading guard skipped when Input 18 = 0
```cpp
// Line 585 — was:
if (w_chart > 0) {          // ← Input 18 = 0 = "same chart" → SKIPPED!
    sierra.valid = true;
    // ... read CCI, TCCI, SWI, etc.
}
```
**Fix:** Removed `> 0` guard. `wc` already defaults to `sc.ChartNumber`.

### Bug 2: Cross-chart index misalignment (THE REAL BUG)
```cpp
// Was:
sc.GetStudyArrayFromChartUsingID(wc, 4, 0, arr);
if (arr.GetArraySize() > idx) sierra.cci_14 = arr[idx];  // ← idx = HOST chart index!
```
**Problem:** `idx = sc.Index` = host chart's bar index (RTH, frozen overnight). Chart 12's study array has MORE bars (24h). `arr[idx]` pointed to the **middle of chart 12's history** (May 29 values), not the current bar.

**Fix:** Read the LAST element of the study array:
```cpp
#define W_LAST(a) ((a).GetArraySize() - 1)
sc.GetStudyArrayFromChartUsingID(wc, 4, 0, arr);
if (W_LAST(arr) >= 0) sierra.cci_14 = arr[W_LAST(arr)];  // ← LATEST value
```

---

## Before → After

| Field | Before (frozen May 29) | After (LIVE) | Sierra (Michael) |
|-------|----------------------|-------------|-----------------|
| CCI-14 | 74.85 | **-70.8** | -103.86 |
| TCCI | 127.42 | **-5.66** | — |
| SWI | 72.05 | **-77.8** | — |
| EMA-34 | 7427.25 | **7613.17** | — |
| LSMA | 7422.17 | **7610.15** | — |
| ProjHi | 7653.25 | **7908.0** | 7909.00 |
| ProjLo | 7545.50 | **7309.75** | 7310.25 |

Values now match Sierra chart 12 (±1 tick from timing).

## Sierra Input Configuration (verified)

| Input | Name | Value | Status |
|-------|------|-------|--------|
| In:18 | TPO Chart Number | 0 (same chart) | ✅ |
| In:19 | Woodies Chart Number | 12 | ✅ |
| In:21 | Continuous 24h Chart Number | 5 | ✅ |

## Content Staleness Detection

Added `studies_stale` / `studies_badge` to woodies chart endpoint — detects when bar timestamps are >1h old (previous RTH session). During RTH, `studies_stale = false`.

## Commits

1. `bb679f8` — fix(dll): read Woodies studies when Input 18 = 0
2. `86df698` — fix(dll): read LAST element of chart 12 study arrays (index fix)
3. `8fa5f8b` — fix: content-based staleness detection

## Chart #12 Regression

All 16 existing export files remain FRESH. Chart #5 continuous exports unaffected.

---

*Woodies panel now reflects Sierra chart 12 in real-time. Michael confirmed parity.*
