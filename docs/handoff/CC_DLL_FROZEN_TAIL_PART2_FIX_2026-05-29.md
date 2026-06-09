# CC Handoff · DLL Frozen-Tail Bug · Part 2 of 3: Fix
**Date:** 2026-05-29  
**Owner:** Claude Code  
**Pre-condition:** Part 1 diagnosis complete. Michael confirmed `WoodiesChartNumber = 12` (In:19 = 12).  
**Decision:** Michael wants to keep chart 12 as the Woodies data source → **Option A only.**  
**Protocol:** Smallest correct change. Build + deploy + reload Sierra.

---

## Context (confirmed)

- `WoodiesChartNumber` (sc.Input[18], displayed as In:19) = **12** — confirmed by Michael's Sierra UI screenshot.
- `mapIdx` calls `GetContainingIndexForDateTimeIndex(12, dll_bar_idx)` for every history bar.
- For the last ~13 bars of RTH, Sierra returns the **same** chart-12 index → stale non-zero values → frozen tail.
- `current_bar` path uses `arr[sc.Index]` (no mapping call) → always live.
- Chart 12 has the Woodies studies and should stay as the data source.

---

## Option A — DLL patch: clamp detection in `mapIdx`

**File to edit:** `sc_study/v9_woodies_export.h`  
**Lines to change:** 458–463 (the `mapIdx` lambda)

### Current code (lines 458–463)

```cpp
// Map DLL bar index → Woodies chart bar index using Sierra's cross-chart mapping
// GetContainingIndexForDateTimeIndex maps a datetime index from THIS chart to target chart
auto mapIdx = [&](int dll_bar_idx) -> int {
    if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
    return sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
};
```

### Replacement code

```cpp
// Map DLL bar index → Woodies chart bar index using Sierra's cross-chart mapping.
// Clamp-detection: if two consecutive bars map to the same Woodies index, the
// cross-chart mapping has hit its boundary — fall back to direct index for those bars.
auto mapIdx = [&](int dll_bar_idx) -> int {
    if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
    int mi = sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
    // If this bar maps to the same index as the previous bar, the Woodies chart
    // has no newer bar yet — use dll_bar_idx directly (local fallback will apply).
    if (dll_bar_idx > 0) {
        int mi_prev = sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx - 1);
        if (mi == mi_prev) return dll_bar_idx;  // clamped: fall back to local
    }
    return mi;
};
```

### Why this works

When the Woodies chart hasn't computed the current bar yet,  
`GetContainingIndexForDateTimeIndex` returns the same value for bars N and N-1.  
Falling back to `dll_bar_idx` means `S_VAL(arr, dll_bar_idx)` reads from the DLL's own  
chart arrays — which may return 0 for studies that don't live on this chart,  
triggering the existing `sv == 0` fallback to Python-computed values.

This is correct: a Python-computed CCI/SWI is less accurate than Sierra's native study  
but is **never frozen** — it advances every bar and gives A5/sizing real, moving inputs.

### After the code change — build and deploy

```bash
cd /Users/michael/Downloads/mems26_web_git
./scripts/build_monolithic_cpp.sh --deploy
```

Then in Sierra Chart:
- **Analysis → Build Custom Studies DLL → Remote Build** → wait for SUCCESS
- Study will auto-reload; if not: right-click the DLL study → Reload Study

Verify the build succeeded:
```bash
# DLL newer than source
stat -f '%Sm' ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp \
              ~/SierraChart/Data/MES_AI_DataExport_64.dll

# Version in export
python3 -c "import json; d=json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json')); print('version:', d['version'])"
```

---

## Regression test (add to `tests/v9/dll/test_woodies_mapidx_clamp.py`)

```python
"""
Regression: mapIdx clamp detection.
Simulates what the DLL does in Python to verify the clamp-detect logic
produces non-frozen output when cross-chart mapping repeats an index.
"""

def simulate_mapIdx(dll_bar_idx: int, mapping: dict) -> int:
    """Mirrors the Option-A mapIdx lambda logic."""
    mi = mapping.get(dll_bar_idx, dll_bar_idx)
    if dll_bar_idx > 0:
        mi_prev = mapping.get(dll_bar_idx - 1, dll_bar_idx - 1)
        if mi == mi_prev:
            return dll_bar_idx  # clamped: fall back
    return mi

def test_no_clamp_passes_through():
    mapping = {0: 0, 1: 1, 2: 2, 3: 3}
    assert simulate_mapIdx(3, mapping) == 3

def test_clamp_detected_returns_dll_idx():
    # bars 3,4,5 all map to woodies bar 2 (clamped)
    mapping = {1: 1, 2: 2, 3: 2, 4: 2, 5: 2}
    assert simulate_mapIdx(3, mapping) == 3  # clamped → fallback
    assert simulate_mapIdx(4, mapping) == 4  # clamped → fallback
    assert simulate_mapIdx(5, mapping) == 5  # clamped → fallback

def test_first_bar_no_prev_check():
    mapping = {0: 0}
    assert simulate_mapIdx(0, mapping) == 0

def test_non_frozen_tail_stays_mapped():
    mapping = {10: 8, 11: 9, 12: 10, 13: 11}
    assert simulate_mapIdx(13, mapping) == 11
```

Run with:
```bash
python3 -m pytest tests/v9/dll/test_woodies_mapidx_clamp.py -v
```

---

## Commit format

```
fix(dll): clamp-detect in mapIdx — frozen-tail bug

Option A: when GetContainingIndexForDateTimeIndex returns same index
for consecutive bars, fall back to dll_bar_idx so the sv==0 local
fallback produces live (non-frozen) Python-computed values.

Regression: tests/v9/dll/test_woodies_mapidx_clamp.py (4 tests)
```

**Stop here. Do not proceed to Part 3 until Michael confirms the fix is live and the T2 probe shows no frozen runs.**
