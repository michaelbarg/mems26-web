# CC Diagnosis — DLL Frozen-Tail Bug · 2026-05-29

**Mode:** Diagnosis only — no code changes

---

## T1 — Code Confirmations

### T1.1 — mapIdx lambda + S_VAL macro (v9_woodies_export.h:455-463)
```cpp
// Helper: read Sierra float at mapped index, 0 if unavailable
#define S_VAL(arr, idx) ((idx) >= 0 && (idx) < (arr).GetArraySize() ? (arr)[(idx)] : 0.0f)

// Map DLL bar index → Woodies chart bar index using Sierra's cross-chart mapping
auto mapIdx = [&](int dll_bar_idx) -> int {
    if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
    return sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
};
```
**CONFIRMED.** When `wc == 0` or `wc == sc.ChartNumber`, returns `dll_bar_idx` directly (no cross-chart mapping).

### T1.2 — History loop uses mapIdx (v9_woodies_export.h:486-527)
```cpp
for (int bi = history_start; bi < n; bi++) {
    int mi = mapIdx(bars[bi].chart_bar_start);  // mapped index in Woodies chart
    // ...
    sv = S_VAL(s_cci14_arr, mi);  cci14  = (sv != 0) ? sv : v9_calc_cci(bars, bi, 14);
    sv = S_VAL(s_cci6_arr, mi);   cci6   = (sv != 0) ? sv : v9_calc_cci(bars, bi, 6);
    // ... (all 6 study fields use the same `mi`)
```
**CONFIRMED.** Every study field in the history loop uses `mi = mapIdx(bars[bi].chart_bar_start)`.

### T1.3 — WoodiesChartNumber = sc.Input[18] (MES_AI_DataExport.cpp:45)
```cpp
SCInputRef WoodiesChartNumber  = sc.Input[18];   // Chart # where Woodies studies live (0 = same chart)
```
**CONFIRMED.**

### T1.4 — current_bar path uses arr[idx] directly (MES_AI_DataExport.cpp:576-621)
```cpp
int w_chart = WoodiesChartNumber.GetInt();
int wc = (w_chart > 0) ? w_chart : sc.ChartNumber;
// ...
if (w_chart > 0) {
    sierra.valid = true;
    SCFloatArray arr;
    sc.GetStudyArrayFromChartUsingID(wc, 4, 0, arr);
    if (arr.GetArraySize() > idx) sierra.cci_14 = arr[idx];
    // ... all fields use arr[idx], NOT mapIdx
```
**CONFIRMED.** `idx = sc.Index` (the current bar index on the host chart). No `GetContainingIndexForDateTimeIndex` call — direct array access.

### T1.5 — Default WoodiesChartNumber = 0 (MES_AI_DataExport.cpp:118)
```cpp
WoodiesChartNumber.Name = "Woodies Chart Number (0=same chart)";
WoodiesChartNumber.SetInt(0);  // Set to the chart # where Woodies studies live
```
**CONFIRMED.** Default = 0 = same chart = no cross-chart mapping.

---

## T2 — Live JSON Probe

```
total history bars: 50
version: v9.4.2-p30.11
export_ts: 1780054610

Runs of identical cci_14 (run >= 3):
  bars[  0..  2]  ts=1780025400→1780026000  cci_14=0.00  run=3

Last 15 bars (ts / close / cci_14 / swi_value):
  ts=1780035900  c=7588.5   cci_14=-38.12   swi=104.39
  ts=1780036200  c=7588.75  cci_14=-27.84   swi=79.1
  ts=1780036500  c=7589.75  cci_14=13.96    swi=72.62
  ts=1780036800  c=7589.5   cci_14=19.0     swi=57.12
  ts=1780037100  c=7590.25  cci_14=64.56    swi=92.4
  ts=1780037400  c=7590.0   cci_14=66.14    swi=52.18
  ts=1780037700  c=7590.25  cci_14=62.63    swi=43.62
  ts=1780038000  c=7592.25  cci_14=136.6    swi=72.04
  ts=1780038300  c=7591.75  cci_14=138.1    swi=71.96
  ts=1780038600  c=7592.5   cci_14=121.11   swi=58.48
  ts=1780038900  c=7593.75  cci_14=147.91   swi=11.31
  ts=1780039200  c=7594.25  cci_14=154.4    swi=16.3
  ts=1780039500  c=7590.0   cci_14=41.88    swi=-79.23
  ts=1780039800  c=7587.0   cci_14=-104.07  swi=-251.98
  ts=1780040100  c=7588.25  cci_14=-122.19  swi=-276.59

current_bar: cci_14=-122.19  swi_value=-276.59  tcci=-108.55
```

**CRITICAL FINDING: No frozen-tail runs detected right now.** Only a trivial 3-bar run of `cci_14=0.00` at the start (bars 0-2), which is the local-fallback zero for the beginning of the buffer where there's not enough history for CCI-14 computation.

All 15 most recent bars have **unique, varying** `cci_14` and `swi_value` values. `current_bar` matches `history[-1]` exactly (`cci_14=-122.19`).

**Possible explanations:**
- (a) `WoodiesChartNumber` is currently 0 (same chart) → `mapIdx` returns `dll_bar_idx` → no cross-chart mapping → no clamping → no freeze
- (b) The freeze only manifests during RTH when the Woodies chart has more active studies competing for computation
- (c) Michael changed Input #18 since the May 28 incident

---

## T3 — WoodiesChartNumber Current Value

```
keys: ['type', 'version', 'export_ts', 'bar_period_minutes', 'total_bars', 'history', 'current_bar']
version: v9.4.2-p30.11
```

**WoodiesChartNumber is NOT embedded in the JSON.** The DLL does not export the Input #18 value. We cannot determine from the JSON alone whether it's 0 or >0.

However, the T2 evidence (no frozen tail right now) is consistent with `WoodiesChartNumber = 0` — because when `wc == 0`, `mapIdx` returns `dll_bar_idx` directly and no cross-chart clamping can occur.

**Michael must verify in Sierra UI.**

---

## T4 — Fix Feasibility

### Q1 — Option B: Set WoodiesChartNumber = 0 (same chart)

If `WoodiesChartNumber = 0`, `mapIdx` bypasses `GetContainingIndexForDateTimeIndex` entirely → no freeze possible.

**Required studies on the host chart:**

| Study ID | Subgraph | Purpose |
|----------|----------|---------|
| ID:4 | SG0 | CCI-14 |
| ID:10 | SG0 | CCI-6 / TCCI |
| ID:3 | SG0 | EMA-34 |
| ID:2 | SG0 | LSMA-25 |
| ID:6 | SG5 | Sidewinder |
| ID:7 | SG2 | ChopZone |
| ID:1 | SG1,SG2,SG3 | TrendUp/Down/Neutral |
| ID:11 | SG0,SG1 | CCI Predictor |
| ID:9 | SG1,SG2 | ProjHigh/ProjLow |

**Feasibility: NEEDS-MICHAEL.** Cannot confirm chart layout from code. Michael must verify: "Does the host chart (where MES AI Data Export DLL is attached) have Study IDs 1, 2, 3, 4, 6, 7, 9, 10, 11 loaded?"

If yes → set Input #18 = 0 → immediate fix, no code change needed.
If no → studies are on a different chart → Option B requires moving studies or adding them to the host chart.

### Q2 — Option A: Detect clamping in mapIdx

`mi` is computed per-bar at line 489: `int mi = mapIdx(bars[bi].chart_bar_start)`. A "previous mi" comparison is straightforward:

```cpp
int prev_mi = -1;
int clamp_count = 0;
for (int bi = history_start; bi < n; bi++) {
    int mi = mapIdx(bars[bi].chart_bar_start);
    if (mi == prev_mi) {
        clamp_count++;
        if (clamp_count >= 2) mi = bars[bi].chart_bar_start;  // fall back to direct index
    } else {
        clamp_count = 0;
    }
    prev_mi = mi;
    // ... use mi for S_VAL reads
```

**Feasibility: YES.** The loop structure supports per-bar tracking of previous `mi`. The fallback to `dll_bar_idx` (= `bars[bi].chart_bar_start`) would use the local compute functions instead of Sierra arrays — safe because the local computes are already the existing fallback for `sv == 0`.

---

## Recommendation

**Option B (set Input #18 = 0) is the preferred fix IF the host chart has all required studies.** Zero code changes, zero DLL rebuild, instant. Option A (code fix) is the backup if the studies can't be on the host chart. Both are low-risk and can coexist. **Start with Michael verifying the chart layout.**

---

## Open Question for Michael

Please confirm in Sierra UI:

1. **What is Input #18 (`Woodies Chart Number`) on the MES AI Data Export study?** (0 = same chart, or a specific chart number?)
2. **Does the host chart (where the DLL is attached) have Study IDs 1, 2, 3, 4, 6, 7, 9, 10, 11 loaded?** If yes, setting Input #18 = 0 immediately fixes the frozen-tail bug without any code change.
