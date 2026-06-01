# Calibration Flags ON + Chart #5 Discovery · 2026-06-01

**Date:** 2026-06-01 13:25 IL (06:25 ET) · **Author:** CC

---

## Part 1 — Calibration Flags Enabled

### Before → After

| Flag | Before (runtime) | After (runtime) | Behavior Test |
|------|-----------------|-----------------|---------------|
| S2_ATR_RELATIVE | not set → False | **True** | expansion = ATR-relative |
| S3_RELATIVE | not set → False | **True** | `get_min_level_vol(100)` → 30.0 (was 10) |
| S1_IB_WIDTH_ATR | not set → False | **True** | `classify(30, atr=20)` → EXTREME (was WIDE) |
| S1_CVD_OPENING | not set → False | **True** | CVD-enhanced opening type |
| S1_DAYTYPE_STAGING | not set → False | **True** | `cap(0.85, 30min)` → 0.60 (was 0.85) |

### How enabled
Added to `~/Library/LaunchAgents/com.mems26.backend.plist` as export statements.
`.env` already had them. Plist is the runtime source-of-truth (LaunchAgent sandbox blocks .env loading).

### Rollback
Set any flag to `false` in plist → `launchctl unload/load`.

---

## Part 2 — Chart #5 Discovery (Phase A)

### Key finding: Chart #5 does NOT currently export

The DLL (`MES_AI_DataExport`, v9.4.2-p30.11) runs on **chart #12** (3-min, RTH session).
All 14 export files in `v9_export/` come from chart #12.
Chart #5 (5-min, 24h Globex, with Cumulative Delta) is a separate Sierra chart with no DLL instance.

**Evidence:**
```
5min.json: 601 bars, hours 08-15 UTC ONLY → RTH-only (chart #12 session)
cumulative_delta.json: 90 points, 08:29-15:55 UTC → RTH-only
```

### Why bars are RTH-only (root cause confirmed)
`v9_build_5min_ohlcv_bars()` reads `sc.Open/High/Low/Close[i]` from the host chart's bar array.
Chart #12 is set to RTH session → its bar array only contains RTH bars → no overnight data possible.

### Options for chart #5 integration

| Option | Change | Effort | Risk |
|--------|--------|--------|------|
| A: Cross-chart input (recommended) | Add `ContinuousChartNumber` Input, read OHLCV+CVD from chart #5 | ~50 LOC in DLL | Low (same pattern as Woodies/TPO) |
| B: Second DLL instance | Put DLL on chart #5 | Config only | Medium (duplicates all exports) |
| C: Sierra native export | Spreadsheet Study on chart #5 | No DLL change | High (limited format, separate tooling) |

### Strategic stop — DLL change requires Michael approval

Per CLAUDE.md §7a: no sc_study changes without verification.
DLL monolith build + deploy to both Sierra installations + Remote Build required.

**NOT blocking SHADOW** — current mitigation (bid/ask midpoint + merged DB tables) works.

---

*Ready for Michael's decisions on chart #5 approach and timing.*
