# DLL Memory Fix — v9.1.1

## The Problem

Sierra Chart consumed **123 GB of RAM** and had to be force-quit.

## Root Cause: Throttle in Wrong Position

With `sc.AutoLoop = 1`, Sierra calls the study function **once per bar** during chart load. A 3-minute chart with 5000 bars = 5000 function calls in rapid succession.

The time-based throttle (`ExportIntervalSec = 3`) was positioned **after** all heavy computation:

```
BEFORE (broken — 5000 calls each create maps):

  Bar 0:  CVD → VWAP → pvm map (200 nodes) → tpo_map (120 nodes) → vector → ... → THROTTLE → JSON
  Bar 1:  CVD → VWAP → pvm map (200 nodes) → tpo_map (120 nodes) → vector → ... → THROTTLE → return
  Bar 2:  same...
  ...
  Bar 4999: same...

  Total: 5000 × 320 map nodes = 1.6 MILLION heap alloc/dealloc cycles
  MSVC allocator fragmentation → memory never returned to OS
```

## What Was Leaking (Specific Lines)

| Line | Allocation | Per-call | × 5000 bars |
|------|------------|----------|-------------|
| 1152 | `std::map<int,float> pvm` | ~200 nodes × 64B | 64 MB churn |
| 1181 | `std::map<int,int> tpo_map` | ~120 nodes × 48B | 29 MB churn |
| 1218 | `std::vector<ImbLevel>` + sort | ~5 entries | 1.6 MB churn |
| 952  | `cci_slice` vector copy in loop | 50 copies × growing | 0.5 MB churn |

Additionally, each bar triggered O(n) loops for VWAP, Woodi pivots, 72H/weekly — totaling O(n²) CPU during chart load.

## The Fix

### 1. Moved throttle BEFORE heavy computation (BIGGEST impact)

```
AFTER (fixed — 5000 calls only do CVD + VWAP):

  Bar 0:  CVD → VWAP → THROTTLE passes → maps, vectors, JSON, V9 exports
  Bar 1:  CVD → VWAP → THROTTLE → return (< 3 sec)
  Bar 2:  CVD → VWAP → THROTTLE → return
  ...
  Bar 999: CVD → VWAP → THROTTLE passes → maps, vectors, JSON, V9 exports
  ...

  Total map allocs: ~2 (not 5000). 99.96% reduction.
```

CVD and VWAP **must** run every bar (subgraph writes for chart display). Everything else only needed for JSON export → runs every 3 seconds.

### 2. Static vector with clear() for imbalances

```cpp
static std::vector<ImbLevel> imbalances;
imbalances.clear();  // reuses capacity — no heap alloc after first call
```

### 3. Eliminated cci_slice vector copy in woodies loop

```cpp
// BEFORE (50 vector copies per export):
std::vector<float> cci_slice(cci14_hist.begin(), cci14_hist.begin() + bi + 1);
ZLRResult zlr = v9_detect_zlr(cci_slice, 12);

// AFTER (zero copies — pointer + count):
ZLRResult zlr = v9_detect_zlr(cci14_hist.data(), bi + 1, 12);
```

Changed `v9_detect_zlr` signature from `const std::vector<float>&` to `const float*, int n`.

### 4. Added reserve() for all vectors

- `bars.reserve(lookback_bars / 4)` — tick reversal
- `fp_bars.reserve(32)` — footprint bars
- `bars.reserve(max_bars + 1)` — woodies 30min bars
- `cci14_hist.reserve(n)` — CCI history

### 5. Memory safety net

Tracks approximate bytes per export cycle. Logs warning if > 10 MB:
```cpp
if (mem_est > 10 * 1024 * 1024)
    sc.AddMessageToLog("MEMS26 WARNING: export alloc > 10 MB!", 1);
```

## Expected Memory Profile

| State | Before Fix | After Fix |
|-------|-----------|-----------|
| Chart load (5000 bars) | 123 GB (crash) | < 50 MB |
| Real-time idle | Growing | Stable < 50 MB |
| Real-time active | Growing | Stable < 100 MB |
| **Should NEVER exceed** | — | **1 GB** |

## Files Changed

- `MES_AI_DataExport_merged.cpp` — throttle move, static buffers, memory safety
- `MES_AI_DataExport.cpp` — same throttle move and static buffers
- `v9_exports.h` — reserve() for tick reversal vectors
- `v9_woodies_export.h` — reserve(), cci_slice fix, v9_detect_zlr signature

## What Was NOT Changed

- Real-time behavior preserved — no "last bar" guards
- All 8 V9 exports still functional
- CVD + VWAP subgraph accuracy maintained (run every bar)
- Export interval unchanged (3 seconds default)
