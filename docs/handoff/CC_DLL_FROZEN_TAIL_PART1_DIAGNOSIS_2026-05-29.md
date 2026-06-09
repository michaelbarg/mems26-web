# CC Handoff · DLL Frozen-Tail Bug · Part 1 of 3: Diagnosis Only
**Date:** 2026-05-29  
**Owner:** Claude Code  
**Protocol:** CLAUDE.md § "Diagnose first, fix second" — **NO code changes in this part.**  
**Source reports:** `docs/reports/AUDIT_S2_S4_LIVE_FORENSICS_2026-05-28.md` §3 + §6 (rank-1)

---

## What you are diagnosing

The DLL exports `woodies_5min.json` for all S4 Woodies patterns.  
For the last **~13 bars of every session**, the Sierra-sourced study fields  
(`cci_14`, `cci_6_tcci`, `lsma_value`, `ema_34`, `swi_value`, `czi_value`, `trend_state`)  
are **identical** — frozen at the value of bar N-13.  
`ohlc.close` and `ccidiff_*` still change — only the cross-chart-fetched fields freeze.

**Impact:** S4's A5 sizing gate uses `swi_value` and `cci_6_tcci` from `current_state`.  
With frozen inputs, `aux_count ≤ 1` → every pattern in the tail is rejected (`calculate_size=reject`).  
This is the primary reason S4 has not fired in the last hours of any session.

---

## Root cause hypothesis (from forensic audit)

File: `sc_study/v9_woodies_export.h`  
Lines 458–462 (the `mapIdx` lambda):

```cpp
auto mapIdx = [&](int dll_bar_idx) -> int {
    if (!have_sierra || wc == 0 || wc == sc.ChartNumber) return dll_bar_idx;
    return sc.GetContainingIndexForDateTimeIndex(wc, dll_bar_idx);
};
```

When `WoodiesChartNumber` (Input #18) is set to a **different chart** than the host chart,  
`GetContainingIndexForDateTimeIndex(wc, dll_bar_idx)` is called.  
For in-progress / near-end-of-session bars, Sierra's cross-chart time mapping  
**clamps** to the last fully-computed bar on the Woodies chart → returns `same_mi` for 13 bars.  
Since `S_VAL(arr, mi)` returns a **non-zero** stale value, the local fallback (`sv == 0`) never fires.

The `current_bar` path in `MES_AI_DataExport.cpp:582–621` uses `arr[idx]` directly  
(no cross-chart mapping) → returns live values. That is why `current_bar.cci_14` is correct  
while `history[-1].cci_14` is frozen.

---

## Your tasks (diagnosis only — no code changes)

### T1 — Read and confirm code locations

Read the following file sections and confirm each fact:

1. `sc_study/v9_woodies_export.h` lines 458–475 — confirm `mapIdx` lambda and `S_VAL` macro.
2. `sc_study/v9_woodies_export.h` lines 486–530 — confirm the history loop uses `mapIdx(bars[bi].chart_bar_start)` (cross-chart path).
3. `sc_study/MES_AI_DataExport.cpp` lines 44–46 — confirm `WoodiesChartNumber = sc.Input[18]` with `SetInt(0)` default.
4. `sc_study/MES_AI_DataExport.cpp` lines 575–621 — confirm `current_bar` path reads `arr[idx]` (NOT mapped), where `idx = sc.Index`.
5. `sc_study/MES_AI_DataExport.cpp` line 118 — confirm `WoodiesChartNumber.SetInt(0)` (default = same chart).

For each: paste the actual lines you read (no paraphrasing).

### T2 — Probe the live JSON

Run this and paste the raw output:

```bash
python3 - << 'PY'
import json, collections

path = "/Users/michael/SierraChart_Data/v9_export/woodies_5min.json"
d = json.load(open(path))
hist = d.get("history", [])
print(f"total history bars: {len(hist)}")
print(f"version: {d.get('version')}")
print(f"export_ts: {d.get('export_ts')}")

# detect runs of identical cci_14
runs = []
if hist:
    cur_val, run_start = hist[0].get("cci_14"), 0
    for i, bar in enumerate(hist[1:], 1):
        v = bar.get("cci_14")
        if v != cur_val:
            if i - run_start >= 3:
                runs.append((run_start, i-1, cur_val, i - run_start))
            cur_val, run_start = v, i
    if len(hist) - run_start >= 3:
        runs.append((run_start, len(hist)-1, cur_val, len(hist) - run_start))

print(f"\nRuns of identical cci_14 (run >= 3):")
for s, e, v, l in runs:
    ts_s = hist[s].get("ts", "?")
    ts_e = hist[e].get("ts", "?")
    print(f"  bars[{s:3d}..{e:3d}]  ts={ts_s}→{ts_e}  cci_14={v:.2f}  run={l}")

# last 15 bars
print("\nLast 15 bars (ts / close / cci_14 / swi_value):")
for bar in hist[-15:]:
    print(f"  ts={bar.get('ts')}  c={bar.get('ohlc',{}).get('c')}  cci_14={bar.get('cci_14')}  swi={bar.get('swi_value')}")

# current_bar
cb = d.get("current_bar", {})
print(f"\ncurrent_bar: cci_14={cb.get('cci_14')}  swi_value={cb.get('swi_value')}  tcci={cb.get('cci_6_tcci')}")
PY
```

### T3 — Check WoodiesChartNumber current value

The DLL default is `SetInt(0)` but Michael may have changed it in Sierra UI.  
The running export embeds this in JSON. Run:

```bash
python3 -c "
import json
d = json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json'))
# look for chart number in metadata
for k in ['woodies_chart_number','chart_number','input_18','wc']:
    if k in d: print(k, '=', d[k])
# also check version + any 'inputs' block
print('keys:', list(d.keys()))
print('version:', d.get('version'))
"
```

If the JSON does not contain the chart number, note that — it means we need Michael  
to open Sierra and check Input #18 of the `MES AI Data Export` study manually.

### T4 — Determine fix feasibility

Without changing any code, answer these questions by reading source:

**Q1 (Option B feasibility):**  
If `WoodiesChartNumber` is set to 0 (same chart), `mapIdx` returns `dll_bar_idx` directly  
and the cross-chart `GetContainingIndexForDateTimeIndex` call is bypassed entirely.  
**Do the studies the DLL needs (CCI-14, TCCI/CCI-6, EMA-34, LSMA-25, Sidewinder, ChopZone,  
TrendUp/Down/Neutral, CCI Predictor) exist as studies ON THE HOST CHART (the chart the DLL  
is attached to)?**  
Read `sc_study/MES_AI_DataExport.cpp` lines 582–621 (`WoodiesSierraStudies` block) and list  
the Study IDs and subgraphs expected: `(ID:4,SG0)`, `(ID:10,SG0)`, `(ID:3,SG0)`, `(ID:2,SG0)`,  
`(ID:6,SG5)`, `(ID:7,SG2)`, `(ID:1,SG1/2/3)`.  
We cannot confirm the Sierra chart layout from code alone — flag this as "Michael must verify  
in Sierra UI: does chart N have Study IDs 1,2,3,4,6,7,10 loaded?"

**Q2 (Option A feasibility):**  
A code fix to `mapIdx` in `v9_woodies_export.h:460–462` could detect clamping:  
detect when `mi == prev_mi` for ≥2 consecutive bars and fall back to `dll_bar_idx`.  
Read lines 486–510 (the history loop) and confirm that `mi` is computed per-bar  
(`mapIdx(bars[bi].chart_bar_start)`) — so a "previous mi" comparison is straightforward.

---

## Deliverable: diagnosis report

Write `docs/reports/CC_DIAG_DLL_FROZEN_TAIL_2026-05-29.md` with:

1. **T1 confirmations** — paste the actual code lines for each of the 5 read tasks.
2. **T2 output** — paste the raw probe output verbatim.
3. **T3 output** — paste raw + interpret (is WoodiesChartNumber 0 or >0?).
4. **T4 answers** — Q1 + Q2 feasibility summary.
5. **Recommendation** — based on findings, which option (A / B / both) do you recommend and why? Max 5 lines.
6. **Open question for Michael** — "Please confirm in Sierra UI: what is Input #18 (`Woodies Chart Number`) on the MES AI Data Export study? And does that chart have Study IDs 1, 2, 3, 4, 6, 7, 10 loaded?"

**Do not make any code changes. Do not run `build_monolithic_cpp.sh`. Do not restart Sierra.**  
This part ends when the diagnosis report is written and committed.

---

## Commit format

```
diag(dll): frozen-tail T1-T4 diagnosis report

T1: confirmed mapIdx lambda + current_bar direct-read at cpp:582
T2: frozen-tail probe — runs=[paste summary]
T3: WoodiesChartNumber=[value or "not in JSON"]
T4: Option B feasible=[yes/no/needs-Michael], Option A feasible=yes
```
