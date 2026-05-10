# DLL Real-Time Fix — v9.1.0

## What W4 got wrong

W4's "merged" DLL (`MES_AI_DataExport_merged.cpp`) added two wrong changes:

### 1. "Last bar only" guard (WRONG)
```cpp
// W4 ADDED THIS — KILLS REAL-TIME:
if (sc.Index != sc.ArraySize - 1)
    return;  // Skip V9 exports for historical bars — only compute on latest
```

**Why this is wrong:** The original V8 design exports V9 data every `ExportIntervalSec` seconds (default 3s) via a time-based throttle. This works perfectly — Sierra calls the study on the current bar, the throttle prevents excessive writes, and V9 JSONs update in real-time. The "last bar only" guard was an unnecessary workaround for a crash that had a different root cause.

### 2. Cumulative delta truncated to 200 bars (WRONG)
```cpp
// W4 CHANGED THIS:
int cd_start = v9_max_i(0, sc.Index - v9_lookback);  // only last 200 bars
```

**Why this is wrong:** Cumulative delta must be anchored to session open to be meaningful for intraday trading. A 200-bar window is arbitrary and loses the session context.

### 3. VAP API wrong function signature (ROOT CAUSE OF CRASH)
```cpp
// v9_exports.h BEFORE fix — used wrong API:
vap_array = sc.VolumeAtPriceForBars->GetVAPArrayAtBarIndex(bar_idx, &num_vap);
// This function may not exist in all ACSIL versions → crash/undefined behavior
```

The correct ACSIL API is `GetVAPElementAtIndex` (element-by-element iteration):
```cpp
// CORRECT — iterate elements one by one:
const s_VolumeAtPriceV2* p_vap = nullptr;
int has_vap = sc.VolumeAtPriceForBars->GetVAPElementAtIndex(bar_idx, 0, &p_vap);
while (has_vap != 0 && p_vap != nullptr) {
    // ... use p_vap ...
    vi++;
    has_vap = sc.VolumeAtPriceForBars->GetVAPElementAtIndex(bar_idx, vi, &p_vap);
}
```

## What the real crash was

The crash was from `GetVAPArrayAtBarIndex` — a function that may not exist in Sierra's ACSIL vtable. W4 "fixed" it by adding "if last bar" guard to reduce how often the crash path was hit. The real fix is using the correct `GetVAPElementAtIndex` API.

Additional protections already in place:
- `v9_max`/`v9_min` instead of `std::max`/`std::min` (ACSIL macro conflict)
- `v9_abs` instead of `std::abs`

## What v9.1.0 fixes

1. **Removed "last bar only" guard** — V9 exports fire on every throttle cycle (every 3s), exactly like V8
2. **Session-anchored cumulative delta** — loops from session open, not from bar 0 or last-200
3. **Separate header files preserved** — `v9_types.h`, `v9_exports.h`, `v9_woodies_export.h` with `#pragma once`
4. **VolumeAtPrice null check** — kept from original headers

## Architecture (unchanged from V8)

```
AutoLoop bar iteration
  ├─ Compute indicators (CVD, VWAP, profile, etc.) — every bar
  ├─ Throttle check: if < ExportIntervalSec since last write → return
  ├─ Write mes_ai_data.json (main export)
  └─ Write V9 exports (tick_reversal, footprint, volume_profile, etc.)
      └─ These fire every ~3 seconds = REAL-TIME
```

## Deployed files

```
~/SierraChart/ACS_Source/
├── MES_AI_DataExport.cpp    (main study, v9.1.0)
├── v9_types.h               (types + helpers)
├── v9_exports.h             (tick rev, footprint, delta, imbalance)
└── v9_woodies_export.h      (woodies CCI 30-min)
```

## After deploy

1. Sierra Chart: Build Custom Studies DLL
2. Sierra Chart: Re-add study to chart
3. Verify: `v9_export/` files update every ~3 seconds during market hours
