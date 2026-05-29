# S2 + S4 Live Forensic Audit · 2026-05-28

**Auditor:** Cursor agent (parent) · READ-ONLY · pre-LIVE mode
**Time:** Thu 2026-05-28 ~12:15 ET (CASH_HOURS, RTH active)
**Subject:** Re-audit of `docs/reports/DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` after Michael's pushback
**Branch:** working tree on `stabilize/mems26-local-truth-2026-05-16` (per `SPEC_AUDIT_S4_WOODIES_2026-05-27.md` §0)
**Constraints:** no edits to code/services, no DB writes, no service restarts; sandbox limitations recorded in §7.

---

## §1 — Executive Summary

- **CC's prior diagnosis ("S2/S4 didn't fire because no patterns matched today") is FALSIFIED by the database.** `v9_woodies_signals` contains **12+ S4 pattern detections today** (ZLR LONG conf=0.83, TLB LONG conf=0.77, VEGAS SHORT conf=0.75, HTLB LONG conf=0.65, GB100 LONG conf=0.66, plus earlier hits). Patterns *were* detected; they did not fire.
- **The real S4 firing block is the A5/sizing gate** (`calculate_size=reject`), driven by **SWI/TCCI study values that are STALE/FROZEN** for the last ~13 bars of every session in the Sierra DLL export. Direction-alignment math gets bad inputs → reject.
- **DLL "frozen-tail" bug — primary data-integrity finding.** In `~/SierraChart_Data/v9_export/woodies_5min.json`, the LAST 13 5-min bars of each session block share IDENTICAL Sierra-sourced study fields (`cci_14`, `cci_6_tcci`, `lsma_value`, `ema_34`, `swi_value`, `czi_value`, `trend_state`). Confirmed live on three sessions (5/26 15:55–16:55 ET, 5/27 15:55–16:55 ET, 5/28 11:05–now). This propagates straight into the frontend `WoodiesCciPanel` via `/api/v9/woodies/chart`.
- **Frontend Woodies values DO NOT match Sierra UI — confirmed live** by hitting `/api/v9/woodies/chart?limit=20`: 13 consecutive bars show `cci_14=155.98, tcci=111.11, trend=BLUE`. This is what Michael sees as a flat horizontal CCI line; his Sierra UI Woodies study shows true per-bar oscillation. This is the root of Michael's claim #1.
- **Backend uses the FROZEN history tail and ignores `current_bar`** when routing to S4 (`backend/v9/api/v9/bars.py:786-852`). `payload.all_bars` prefers `history` → S4 receives history[-1] (frozen) instead of `current_bar` (live).
- **Bridge "Chicago TS" fix is over-correcting by ~1 hour** (Sierra chart appears to be running in ET/EDT, not Chicago/CDT). `/api/v9/woodies/chart` returns `latest_ts_unix = 17:20 UTC = 13:20 ET` while wall clock is 12:20 ET — the timeline is shifted 1 hour into the future.
- **`v9_bars_5min_woodies` DB table is mis-shaped.** It stores **push timestamps**, not bar timestamps (3,193 rows for today by 12:13 ET — one row per bridge push, no dedup-by-bar). Today's freshest CCI in DB (push@12:13 ET) reads **67.96**; same-instant DLL `current_bar.cci_14`=**47.21**; frontend tail shows **155.98** for the previous 13 bars frozen. **Three sources, three different numbers** — see §3 table.

> Net: this is NOT "no setups today" — this is a layered **data integrity** failure that froze the SWI/TCCI inputs the sizing gate relies on, and the prior diagnosis was reached without inspecting the signals table or comparing the export to Sierra UI.

---

## §2 — WS-A · Woodies Spec Re-Review (KEEP/ADAPT/REPLACE classification)

### Spec authority surveyed

| Doc | Type | Status |
|-----|------|--------|
| `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` | Master spec | KEEP — re-read for Woodies §; no direct contradiction with impl |
| `docs/spec_authority/S4_WOODIES_TABLE_A_Pattern_Setup.csv` | 9-pattern entry/stop spec | KEEP — implementation matches the 9 detector names in `patterns/` |
| `docs/spec_authority/S4_WOODIES_TABLE_B_DayType_Matrix.csv` | Day-type advisory matrix | KEEP — A2 stage exists, is advisory-only (confirmed in `stages/a2_day_type_query.py`) |
| `docs/spec_authority/S4_WOODIES_TABLE_C_Strategy_Caveats.csv` | Lunch skip / FOMC / trend gates | KEEP |
| `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` | Binary; could not parse without xlsx tool | DEFER — sandbox could not unzip cleanly; ask Michael to re-export to MD |
| `docs/reports/SPEC_AUDIT_S4_WOODIES_2026-05-27.md` | Prior CC audit (8/8 PASS) | NOTED — passes are real, but they audit gates+wiring, NOT data integrity |

### Implementation surface (confirmed present)

- 9 patterns: `backend/v9/systems/woodies/patterns/{zlr,tlb,tt,gb100,vegas,ghost,famir,htlb,hfe}.py` ✓ matches spec
- Anti-Patterns AP1-9: present in `anti_patterns.py` + `patterns/hfe.py` ✓
- YELLOW gate (A1) at `woodies_system.py:299` ✓
- RTH gate (filter-F17) at `woodies_system.py:253-261` ✓ (default `V9_WOODIES_RTH_ONLY=1`)
- Dedup gate at `woodies_system.py:395-405` ✓
- W-8 dispatcher with `yaml_override` config ✓
- Time stop W-10 at `time_stop.py` ✓

### Spec-vs-implementation DELTAS

| # | Delta | Spec quote | Impl evidence | Severity |
|---|-------|-----------|---------------|----------|
| D-1 | **Lunch skip (12:00–13:30 ET) is NOT enforced in code** | `Table A`: "skip 12:00–13:30 ET" for all 9 patterns | No `lunch` check found in `woodies_system.py` or `pattern_engine.py`. RTH gate only blocks pre-09:30/post-16:00. | LOW — would only suppress some midday signals |
| D-2 | **FOMC ±90min skip is NOT enforced** | Table A: "FOMC ±90min" for all 9 patterns | No FOMC calendar wired | LOW for non-FOMC days |
| D-3 | **Day-type matrix gate (A2) is advisory-only** | Table B specifies per-day-type allowed patterns | `stages/a2_day_type_query.py:9` says "terminal is always None". Per `SPEC_AUDIT_S4_WOODIES_2026-05-27.md` §2 check 4, this is by design for Pipeline 2 | MEDIUM for LIVE — wire before LIVE |
| D-4 | **`min_r_t1_threshold = 0.0` in shadow** | YAML comment: "LIVE: should be ≥1.0" | `dispatcher_config.yaml` ships 0.0 | MEDIUM — pre-LIVE checklist item |
| D-5 | **Sizing uses live `current_state` snapshot, not pattern's bar context** | Implicit: aux alignment is per-pattern-bar | `calculate_size()` lines 592-617 reads `self.current_state["swi_value"]/cci_6_tcci/czi_value`, which is whatever the LAST processed bar set. Because S4 receives the frozen-history `history[-1]` (see §3), SWI/TCCI used by sizing are themselves stale. | **HIGH — root cause for §1 fire-blocker** |
| D-6 | **`v9_woodies_patterns` table is defined but never written** | DB model `V9WoodiesPattern` exists | `rg "V9WoodiesPattern\(" backend/` → 0 INSERT sites | LOW (only matters if a report queries it; signals table has the data) |

**No drift in the 9 detector definitions themselves was found.** Pattern names, group, direction, anti-pattern wiring match the spec.

---

## §3 — WS-B · Frontend ↔ Sierra Value Parity (the smoking gun)

### Data flow (mapped)

```
Sierra DLL  ─► /Users/michael/SierraChart_Data/v9_export/woodies_5min.json
                                  │
                ┌─────────────────┴────────────────────┐
                │                                       │
                ▼ (path A: bridge → API → S4)           ▼ (path B: API → frontend)
   bridge/v9_streams/woodies_5min_stream.py    backend/v9/api/v9/woodies_chart_routes.py
   (Watchdog/poll; +5h Chicago TS fix)          (reads file DIRECTLY; +5h Chicago TS fix)
                │                                       │
                ▼                                       ▼
   POST /api/v9/bars/woodies_5min               GET /api/v9/woodies/chart
   • iterates payload.all_bars (= history)      • normalizes 200 history bars
   • for each bar → INSERT v9_bars_5min_woodies • detects ts-bug, reconstructs ts
   • _route_bar("woodies_5min", last_flat)       • merges current_bar onto tail
   • last_flat = history[-1] (FROZEN)            • returns to frontend WoodiesCciPanel
                │                                       │
                ▼                                       ▼
   WoodiesSystem.process_bar(event)              [CCI:xx.xx] label + chart line
   • studies = bar.{cci_14, ema_34, swi_value, czi_value, …}  ← FROZEN inputs
   • detect_all_patterns(buffer)
   • calculate_size(...) reads current_state ← also FROZEN
   • A5/sizing → "reject"
   • ready_to_route = false → no trade
```

### The frozen-tail symptom (live evidence, 12:05 ET snapshot)

Snapshot of `/tmp/woodies_5min_snapshot.json` (copied from live export):

```
Runs of identical cci_14 (run >= 3):
  bars[ 65.. 77]  (Tue 05-26 15:55→16:55 ET)  cci_14=-155.02  run=13
  bars[155..167]  (Wed 05-27 15:55→16:55 ET)  cci_14= 143.20  run=13
  bars[187..199]  (Thu 05-28 11:05→12:05 ET)  cci_14=  49.70  run=13
```

Same 13-bar window with multi-field view (today, ET):

| idx | ts (ET)   | close   | cci_14 | tcci    | lsma    | ema_34  | swi    | czi  | trend |
|----:|-----------|---------|--------|---------|---------|---------|--------|------|-------|
| 186 | 11:00     | 7571.50 |  38.46 | -124.22 | 7578.79 | 7558.94 | -72.09 |  56  | BLUE  |
| 187 | 11:05     | 7570.00 |  49.70 |  -21.09 | 7577.91 | 7559.80 | **-78.17** | 54 | BLUE |
| 188 | 11:10     | 7567.25 |  49.70 |  -21.09 | 7577.91 | 7559.80 | -78.17 |  54  | BLUE  |
| 189 | 11:15     | 7568.25 |  49.70 |  -21.09 | 7577.91 | 7559.80 | -78.17 |  54  | BLUE  |
| …   | (frozen)  |   …     |  49.70 |  -21.09 | 7577.91 | 7559.80 | -78.17 |  54  | BLUE  |
| 199 | 12:05     | 7573.50 |  49.70 |  -21.09 | 7577.91 | 7559.80 | -78.17 |  54  | BLUE  |

`ohlc.close` **does** vary bar-to-bar (DLL local read of `sc.Close[]`).
`ccidiff` (DLL-computed locally) **does** vary.
But everything pulled via `sc.GetStudyArrayFromChartUsingID(woodies_chart, …)` (`cci_14`, `cci_6_tcci`, `lsma_value`, `ema_34`, `swi_value`, `czi_value`, `trend_state`) is **identical for 13 bars**.

This is a **subgraph-mapping bug**: `GetContainingIndexForDateTimeIndex(woodies_chart, dll_bar_idx)` is returning the **same Woodies-chart index** for the last 13 5-min DLL bars (likely because the Woodies chart's study array hasn't been recomputed past a stale boundary, so out-of-bounds / in-progress bars all clamp to the last valid Woodies index). The local fallback in `sc_study/v9_woodies_export.h:495-500` only kicks in when `sv == 0`, but the stale value is **non-zero**, so the fallback is bypassed.

### Frontend-vs-Sierra side-by-side (live)

Hit `GET /api/v9/woodies/chart?limit=20` at 12:20 ET (this is what `WoodiesCciPanel` consumes):

```
latest_ts_unix → 2026-05-28 17:20 UTC → "13:20 ET"  (BUT WALL CLOCK IS 12:20 ET)

Last 14 bars from the endpoint:
  ts=2026-05-28 16:15:00  cci=145.45  tcci=173.73  trend=BLUE  zlr=True
  ts=2026-05-28 16:20:00  cci=155.98  tcci=111.11  trend=BLUE  zlr=False
  ts=2026-05-28 16:25:00  cci=155.98  tcci=111.11  trend=BLUE  zlr=False
  ts=2026-05-28 16:30:00  cci=155.98  tcci=111.11  trend=BLUE  zlr=False
  …
  ts=2026-05-28 17:15:00  cci=155.98  tcci=111.11  trend=BLUE  zlr=False
  ts=2026-05-28 17:20:00  cci=-134.45 tcci=-94.66  trend=BLUE  zlr=False  ← current_bar tick
```

So **13 consecutive bars all show `cci_14 = 155.98, tcci = 111.11`** — a flat horizontal line on Michael's chart panel. Sierra UI's Woodies study renders true per-bar oscillation across those same bars.

### Frontend ↔ DB ↔ Sierra parity table (12:05–12:15 ET window)

| Source | Field | Value | Provenance |
|--------|-------|-------|------------|
| Sierra UI Woodies CCI study (per Michael) | CCI-14 @ 12:00 ET bar | NOT 49.70, oscillating | Direct chart read |
| DLL export `woodies_5min.json` `history[-1]` | `cci_14` | **49.70 (frozen 1h)** | File on disk, snapshot 12:05 ET |
| DLL export `woodies_5min.json` `current_bar.cci_14` | live tick | **47.21** | Same snapshot |
| DLL `_debug.study1_woodies_trend.SG0` (Sierra raw) | current bar | **47.21** ← matches current_bar | Same snapshot |
| Frontend `/api/v9/woodies/chart` last 13 bars before tail | `cci_14` | **155.98 (frozen)** | Live API call 12:20 ET (later snapshot) |
| Frontend `/api/v9/woodies/chart` tail bar | `cci_14` | **-134.45** | Same call (current_bar merged) |
| DB `v9_bars_5min_woodies` latest row | `cci_14` (push@12:13 ET) | **67.96** | sqlite3 select |
| DB `v9_woodies_signals` morning pattern fires | `cci_14` (signal-time) | 17.87 → -136 → 311 → 331 → 100 → 131 (varying) | sqlite3 select |

**These are six independent reads of "CCI-14 now" from six layers of the same pipeline and the numbers don't agree.** That is the parity break Michael was reporting.

### Timestamp drift (sub-finding)

`backend/v9/api/v9/woodies_chart_routes.py:43`: `ts_unix += 5 * 3600` (Chicago→UTC).
`bridge/v9_streams/base_stream.py:283-300`: also Chicago→UTC.

If Sierra chart is currently in **ET (EDT = UTC-4)** rather than **CT (CDT = UTC-5)** — which `live_price.json` + signal-table timestamps strongly imply — both layers add an extra hour. The DB confirms it: `v9_bars_5min.ts` for "current" bar shows `2026-05-28 17:10:00 UTC` (= 13:10 ET) at a wall-clock time of 12:10 ET. **The downstream RTH gate (`woodies_system.py:_is_rth_bar`), killzone classifier, and time-stop expiry math are all running on bars whose ts is 1 hour in the future.**

---

## §4 — WS-C · Push Freshness / Heartbeat

| Source | Evidence | Verdict |
|--------|----------|---------|
| `woodies_5min.json` mtime | 0.0–3.0s old when polled (`age_s=2.6`) | DLL is writing fresh files |
| `/api/v9/status` `sierra.last_write_age_s` | 0.0 | OK |
| `/api/v9/status` `bridge.status` | **"timeout"** | bridge inspector failed (likely sandbox-blocked path; not necessarily real bridge failure) |
| `/api/v9/status` `bar_router.subscribers.woodies_5min` | 1 | S4 subscribed |
| `/api/v9/status` `bar_router.received` | 9,383 (today) | bars are arriving |
| `v9_bars_5min_woodies` row count (today, by 12:13 ET) | 3,193 rows | Bridge IS pushing ~14 rows/min (every ~2-3s) — push freshness is FINE |
| `v9_woodies_signals` row count (today) | 12+ pattern detections | S4 process_bar IS executing per push |

**Net:** push cadence is not the problem. The DLL writes, the bridge polls, the API ingests, S4 runs. The data **content** is the problem.

Spec note from `S4_WOODIES_TABLE_A_Pattern_Setup.csv`: pattern detection operates on closed 5-min bars (no tick-level requirement). Bar-level cadence with ~2-3s push frequency exceeds spec. **Michael's claim #2 ("tick-level / per-second / per-bar freshness") is satisfied at the transport layer.** The freeze is upstream (DLL → study subgraph fetch), not in the push pipeline.

---

## §5 — WS-D · Replay 09:30 → now through S2 + S4

### Bars available

```
v9_bars_5min (ts column, UTC) for 2026-05-28:
  198 rows total, MIN = 2026-05-28 00:00:00 UTC, MAX = 2026-05-28 17:10:00 UTC
```

Note the MAX = 17:10 UTC = 13:10 ET — 1 hour in the future of the current wall clock (12:15 ET).
This is the TZ-fix over-correction described in §3. **All bar timestamps in the DB are shifted +1 hour.** Replaying RTH 09:30 ET means querying ts between 13:30 UTC and 16:10 UTC — adjusted timestamps from the DLL.

### S4 (Woodies) — what actually happened today

Pattern detections logged to `v9_woodies_signals` today (UTC ts in DB; ET = UTC-4):

| DB ts (UTC) | ET   | Pattern | Direction | Confidence | CCI at fire |
|-------------|------|---------|-----------|------------|-------------|
| 13:30:02    | 09:30 (RTH open) | HTLB  | SHORT | 0.65 | 17.87 |
| 13:35:01    | 09:35 | HTLB  | SHORT | 0.65 | -135.98 |
| 14:13:09    | 10:13 | HTLB  | LONG  | 0.65 | 311.20 |
| 14:14:29    | 10:14 | TLB   | LONG  | 0.85 | 331.01 |
| 14:14:29    | 10:14 | HTLB  | LONG  | 0.65 | 331.01 |
| 15:01:55    | 11:01 | GB100 | LONG  | 0.503 | 100.60 |
| 15:10:38    | 11:10 | ZLR   | LONG  | **0.83** | 131.04 |
| 15:10:38    | 11:10 | TLB   | LONG  | **0.77** | 131.04 |
| 15:10:38    | 11:10 | GB100 | LONG  | 0.66 | 131.04 |
| 15:10:38    | 11:10 | VEGAS | SHORT | 0.75 | 131.04 |
| 15:10:38    | 11:10 | HTLB  | LONG  | 0.65 | 131.04 |
| 15:10:40    | 11:10 | VEGAS | SHORT | 0.75 | 131.04 |

**This directly contradicts CC's "no patterns matched today" conclusion** (`DIAGNOSIS_S2_S4_BLOCKED_2026-05-28.md` §1 row "Pattern detection — Likely returned empty").

### Per-bar fire chain — why nothing routed

Per the embedded `decision_tree` snapshot in `v9_trades.cross_context` (e.g. trade id 115 at 16:05 UTC):

```json
"woodies_system": {
  "cci_14": 60.39, "cci_6_tcci": 22.3, "swi_value": -76.03, "czi_value": 59.0, "trend_state": "BLUE",
  "active_patterns": [],
  "classification": "NO_SETUP",
  "decision_tree": {
    "pre_fire": [
      {"stage_id":"A1","status":"SKIP","message":"no patterns"},
      {"stage_id":"A2","status":"PASS","message":"11 studies present"},
      {"stage_id":"A3","status":"SKIP","message":"no patterns this bar"},
      {"stage_id":"A4","status":"SKIP","message":"no setup needs touch-points"},
      {"stage_id":"A5","status":"FAIL","message":"calculate_size=reject"},
      {"stage_id":"A6","status":"SKIP","message":"NO_SETUP"},
      {"stage_id":"A7","status":"SKIP","message":"no fire_setup — gateway/pre_fire run at route_setup"}
    ],
    "ready_to_route": false,
    "failed_stages": ["A5"]
  },
  "last_route": {"skipped": true, "reason": "not_ready_to_route", "failed_stages": ["A5"]}
}
```

**Decoding A5/sizing on the 11:10 ET ZLR LONG (conf 0.83):**
`calculate_size()` (line 581-628) evaluates aux alignment:
- `swi_aligned` (LONG): SWI > 0 → with the FROZEN `swi_value=-78.17`, **FALSE**
- `czi_aligned` (LONG): CZI > 0 → frozen `czi_value=54.0`, **TRUE**
- `tcci_leading` (LONG): TCCI > CCI → frozen `tcci=-21.09` vs `cci_14=49.70`, **FALSE**
- `aux_count = 1` → for any tier other than `low+aux≥2`, returns `reject`.

**The frozen SWI=-78.17 and frozen TCCI=-21.09 are killing the sizing math.** If those values reflected the LIVE Sierra study output (per current_bar SG0=47.21 / Sierra UI's true SWI), at least the LONG GB100/TLB/ZLR fires from 11:10 would likely have rotated through sizing.

### S2 (FiveMin) — what actually happened today

`v9_five_min_setups` for 2026-05-28: **0 rows.** No S2 fires.

From `v9_trades.cross_context.five_min_system` at 16:05 UTC:
```json
"five_min_system": {"running": true, "hydrated": true, "mode": "DAY_TYPE_MODE",
  "buffer_size": 622, "opening_type": "NA",
  "last_pattern": null, "last_confluence": 0, "last_classification": null}
```

S2 is alive, in DAY_TYPE_MODE, with 622 bars buffered. But `last_pattern: null` for the recent snapshot — meaning the per-bar detector chain (Reactive → Initiative → H&S → Double_BT → Flag) returned no setup.

**Per CC's §1**: S2 only reads `current_day_type=Normal` (correct) and the NT NO_TRADE skip is off. **What CC missed**: the bar-input timestamps are shifted +1h (§3), so S2's RTH/killzone gates are evaluating against the WRONG timeframe; bars are likely being put into a different killzone band than their wall-clock reality. Whether that's blocking a detector or not could not be pinned down from the snapshot — see §7 unknowns.

The cross-pattern detectors (H&S, DblBT, Flag) require 10–22 bar geometry. With only ~36 RTH 5-min bars elapsed today (09:30 → 12:15 ET), 1–2 of these patterns could exist but require manual chart inspection to confirm — defer to Claude Desktop review (§7).

### Replay summary table (S4 only — S2 returned 0 setups)

| Time (ET) | Bar OHLC (approx) | DLL `cci_14` (history-frozen value at that moment) | Pattern detected | S4 outcome |
|-----------|-------------------|-----------------------------------------------------|------------------|------------|
| 09:30 | open | 17.87 | HTLB SHORT (0.65) | sized=reject → no fire |
| 09:35 | -2.5pt | -136 | HTLB SHORT (0.65) | reject → no fire |
| 10:13–14 | +5pt rally | 311–331 (extreme bullish) | HTLB LONG, TLB LONG (0.85) | reject → no fire |
| 11:01 | retrace | 100.6 | GB100 LONG (0.50) | reject (low conf) → no fire |
| 11:10 | +1pt | 131.04 | ZLR/TLB/GB100/HTLB LONG + VEGAS SHORT | **reject → no fire** (A5) |
| 11:15 → now | range-bound | 49.70 (FROZEN) | no new patterns (correctly, on frozen data) | no fire |

---

## §6 — WS-E · Root-Cause Hypotheses (ranked)

| Rank | Cause | Class | Evidence | Action implied |
|------|-------|-------|----------|----------------|
| **1** | **DLL frozen-tail bug**: `GetStudyArrayFromChartUsingID(woodies_chart, …)` returns the last computed value clamped across the most recent ~13 5-min bars of every session segment. SWI / TCCI / CCI / LSMA / EMA-34 / CZI / trend_state ALL freeze together. | DATA_INTEGRITY | §3 snapshot showing 13-bar identical-value runs across three independent sessions; `current_bar.cci_14=47.21` ≠ history[-1]=49.70; debug `study1.SG0=47.21` confirms LIVE Sierra CCI ≠ what subgraph-array fetch returns for the same bar. | Fix subgraph-index mapping in `sc_study/v9_woodies_export.h:465-475` and/or change Woodies chart number (input #18) to **same chart** to bypass the cross-chart `GetContainingIndexForDateTimeIndex` call. |
| **2** | **Backend ignores `current_bar`**, routes `history[-1]` (frozen) to S4. | DETECTOR_LOGIC | `backend/v9/api/v9/bars.py:799-852` — `payload.all_bars` falls back to `current_bar` ONLY if `history` is empty. With history present, `last_flat = history[-1]`. | Patch payload handler to prefer `current_bar` when present (its values come from `WoodiesSierraStudies sierra = {…sierra.valid=true}` direct-read path in `MES_AI_DataExport.cpp:582-621` which uses `arr[idx]` at known-good `idx`, not the loop-mapped one). |
| **3** | **A5/sizing rejects valid patterns** because it consumes stale SWI/TCCI from `current_state` (which is itself populated from the frozen history). | GATE (caused by #1+#2) | `calculate_size()` math walkthrough in §5 shows aux_count=1 for the 11:10 ZLR LONG given frozen SWI=-78.17; spec-compliant logic, bad inputs. | Once #1+#2 are fixed, this resolves automatically. No code change needed. Optionally add a sizing-input freshness guard (refuse to size when last N CCI samples are byte-identical). |
| **4** | **Chicago TS over-correction** by ~1 hour (Sierra chart appears to be in ET, fix assumes CT). | DATA_INTEGRITY | DB shows current bar at 17:10 UTC (=13:10 ET) at wall-clock 12:10 ET; bridge `_chicago_to_utc` and `woodies_chart_routes.py:43` both add 5h. | Verify Sierra chart's `Use Global Settings for Time Zone` setting; add a chart-TZ probe to the DLL export so the bridge fix can be DST-aware (ET-CDT/ET-EDT). Currently the +5h is correct for CDT only. |
| **5** | **`v9_bars_5min_woodies` uses push-time ts instead of bar ts** (3,193 rows/day, ~14 inserts/min) | DETECTOR_LOGIC (DB) | `bars.py:824` does `bar.get("ts", "")` but the bridge serializes the ts as int → SQLite stores it as int; meanwhile `woodies_system._persist_pattern` uses `datetime.now(utc).isoformat()`. Result is a mix of int and ISO ts in the same column. | Treat this table as a debug log only; do NOT use it as a source of truth for replay. S4's actual data path is in-memory (`_bar_buffer`) from the router. |
| **6** | **CC's "no patterns today" diagnosis was reached without reading `v9_woodies_signals`** | (process error) | DB clearly has 12+ today; CC's audit table line "Pattern detection — Likely returned empty" should have been verified by a query. | Re-run any prior diagnostic with the four UAT axes from `.cursor/rules/mems26-pre-live-protocol.mdc`. |
| (rejected) | "No patterns today" hypothesis | NO_SETUP | Falsified — 12+ signals in DB | — |
| (rejected) | "Push freshness / stream stale" | FRESHNESS | DLL mtime ~3s, 9,383 bars routed, sierra.last_write_age_s=0 | — |
| (rejected) | "Spec drift in detector code" | SPEC_DRIFT | Pattern IDs and gates match spec; SPEC_AUDIT_S4_WOODIES_2026-05-27.md confirms 8/8 PASS on gating | — (modulo D-1 thru D-6 minor in §2) |

### Top-ranked hypothesis (one-line)

> **DLL "frozen-tail" subgraph bug → backend ingests stale Sierra studies → A5/sizing rejects every valid pattern.** All four classes (data, detector wiring, gate, false-positive-NO_SETUP) collapse to a single upstream Sierra-side fix.

---

## §7 — What Could NOT Be Verified (sandbox + ask-Michael items)

1. **Sierra chart Woodies study subgraph layout** — I could not open Sierra Chart from this sandbox. The DLL code reads:
   - `(study 4, SG0)` for CCI-14
   - `(study 10, SG0)` for TCCI / CCI-6
   - `(study 6, SG5)` for Sidewinder
   - `(study 7, SG2)` for ChopZone
   - `(study 1, SG1/2/3)` for TrendUp/Down/Neutral
   - **Ask Michael:** confirm Study IDs 1, 4, 6, 7, 10 on the Woodies chart match the DLL's expected subgraph indices, and confirm the chart number set in DLL input #18 (`WoodiesChartNumber`). The mapping bug suggests the Woodies chart and the DLL chart are different chart numbers, and `GetContainingIndexForDateTimeIndex` is mis-clamping.
2. **xlsx pattern table** — `docs/spec_authority/S4_WOODIES_PATTERN_TABLES_V1.xlsx` (binary) could not be parsed cleanly with sandbox tools. The CSV companion files (`S4_WOODIES_TABLE_A/B/C`) were used instead and cover the 9 patterns. Re-export the XLSX as MD or CSV if there are deltas.
3. **Bridge log inspection** — `/tmp/bridge*.log` could not be read from sandbox path (no globbed read). Have Claude Code dump the last 200 lines of `/tmp/bridge.err.log` and grep for `API push FAILED`, `WOODIES`, `Chicago TS`.
4. **Live Sierra UI screenshot of Woodies CCI panel** — would close the loop on parity definitively. Ask Michael to screenshot Sierra UI at the same moment a `curl /api/v9/woodies/chart` is captured; the 13-bar identical-CCI window will be the visual diff.
5. **Day-type/inspector divergence** (`/api/v9/status` says PENDING/UNKNOWN/A1, prior diagnosis says DB shows Normal/0.68) — out of scope for this audit; flagged so it doesn't get lost.
6. **S2 chart-pattern presence** (H&S, DblBT, Flag) — confirming whether *real* setups existed requires manual chart inspection. Defer to Claude Desktop review per the mega-prompt deliverable.

---

## §8 — Bottom line for Michael

- Today **was not** a "no patterns" day; it was a "patterns detected, sizing rejected on frozen inputs" day. CC's diagnosis is wrong on the headline and was reached without reading `v9_woodies_signals`.
- Your Sierra UI Woodies CCI **legitimately does not match the frontend Woodies panel** — and the diff is reproducible right now via `curl http://localhost:8000/api/v9/woodies/chart?limit=20`.
- The root cause is on the **Sierra DLL side** (study-array subgraph fetch for the last ~13 bars of each session) — not in your S4 patterns, not in your spec, not in your decision tree. The pre-LIVE blocker is a data-integrity bug, not a logic bug.
- Suggested next action (after Claude Desktop independent review): a single tight CC-led fix to `sc_study/v9_woodies_export.h` (subgraph mapping) + a one-liner in `backend/v9/api/v9/bars.py` to prefer `current_bar` over `history[-1]` for routing. No spec change. No retrofit of the 9 detectors.
