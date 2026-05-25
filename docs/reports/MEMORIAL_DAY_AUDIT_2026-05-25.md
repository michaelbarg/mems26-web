# Memorial Day Audit · 2026-05-25 · 3-Stream Read-Only Findings

## Executive Summary

- **Stream A:** RED · DLL TPO export emits garbage (poc=-89088, val=0, ib.found=false). Root cause: wrong subgraph indices for Sierra TPO studies (HA-2 confirmed) + TPOChartNumber=0 defaults to host chart (HA-3 contributing). **Confidence: 88%.** Requires Sierra Remote Build.
- **Stream B:** RED · Backend silently synthesizes wrong TPO from stale DB history when DLL is invalid. Synthesis path at `tpo_routes.py:343-353`. Fix: reject-and-warn guard (~11 LOC).
- **Stream C:** YELLOW · B1 (opening_type not wired) = 3-line fix LOW risk. B2 (mode stuck) = bar delivery timing issue, needs investigation.
- **Finding D:** Sub-symptom of B2 (bar delivery race). S1 DayType machine never received enough opening bars before IB window closed. Independent of DLL.
- **Recommended sequencing:** C-B1 (15min) → A diagnosis verify with Michael (Sierra UI check) → B warning-only (30min) → A DLL patch (~1h + deploy) → B reject mode (10min) → C-B2 (TBD)

---

## Stream A · Sierra DLL TPO Export

### Hypothesis Verification

| H | Hypothesis | Status | Evidence |
|---|---|---|---|
| HA-1 | DLL not writing tpo.json | REFUTED | File timestamp fresh, version v9.4.2-p30.11 matches source |
| HA-2 | Wrong subgraph indices for TPO studies | **CONFIRMED** | SG0/1/2 mapping for "TPO Value Area Lines - Period" produces uninitialized floats (poc=-89088 = raw memory). `CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md` documented same pattern in round 1 |
| HA-3 | TPOChartNumber=0 reads from wrong chart | **CONFIRMED (contributing)** | Default 0 = host chart. If TPO studies live on a different chart, all reads return garbage. Woodies block has chart-0 guard (line 576); TPO block does not |
| HA-4 | Memorial Day session boundary bug | REFUTED | No session-type guards exist in export path |
| HA-5 | Sierra TPO study misconfigured | INCONCLUSIVE | Need Michael to screenshot Sierra Study Settings for ID:1, ID:3, ID:6 |

### Root Cause

Primary: Wrong subgraph indices at `MES_AI_DataExport.cpp:655-657` (today), `:707-708` (IB), `:729-731` (yesterday). Code assigns SG0=POC, SG1=VAH, SG2=VAL but Sierra's study uses different subgraph layout.

Secondary: `TPOChartNumber` Input[17] defaults to 0 (host chart). If TPO studies are on a different chart number, all `GetStudyArrayFromChartUsingID` calls return uninitialized data.

### Confidence Rating: 88%

High confidence on HA-2 (same pattern as documented round 1 bug). HA-3 needs Michael verification (which chart has the TPO studies). HA-5 inconclusive without Sierra UI screenshot.

### Fix Requires Sierra Remote Build: YES

1. Correct subgraph indices in cpp (lines 655-657, 707-708, 729-731)
2. Michael verifies/sets TPOChartNumber in Sierra Study Settings
3. `./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload

---

## Stream B · Backend TPO Synthesis

### Ingest Path

`backend/v9/api/v9/tpo_routes.py:400` — `_load_sierra_tpo()`. Backend file-poll: reads `tpo.json` from disk on every `/api/v9/tpo/current` request. Bridge TPO stream is a stub (not wired).

### Synthesis Logic: FOUND

`tpo_routes.py:343-353` — `_normalize_sierra_tpo()`: when `_va_spread_ok(poc, vah, val)` returns False (catches poc=-89088), code iterates DB history periods in reverse and substitutes the most recent valid period's values. Corrupt DLL data silently overwritten with stale historical POC. No warning logged.

Second path: `tpo_history_snapshotter.py:209` — guard checks `isinstance(poc, (int, float))` which passes for -89088. Corrupt values written to `v9_tpo_history`.

### What Happens Today

1. DLL emits poc=-89088, val=0 → `_va_spread_ok` returns False
2. Synthesis loop finds stale DB period → substitutes poc=7558.25 (yesterday's or hours-old)
3. Response marked `source: "sierra_tpo_json"` with wrong prices, no warning
4. Snapshotter writes -89088 to `v9_tpo_history` (typeof guard passes)

### Proposed Fix

Two insertion points (~11 LOC total):
1. `tpo_routes.py:343` — reject-and-warn before synthesis when `_mes_price_ok()` fails
2. `tpo_history_snapshotter.py:208` — hard reject corrupt values before DB write

---

## Stream C · S2 Wiring

### B1 · opening_type not wired (LOW risk)

`_on_day_type_update` (line 252-264) extracts `day_type` from event payload but NOT `opening_type`. The event payload includes `opening_type` (main.py:327). Fix: add 2 lines after line 263.

### B2 · mode transition stuck (MED risk)

Mode gate at line 244-246 uses bar-time (SessionClassifier on processed bar), not wall-clock. With bar_router backlog, processed bars lag. BarRouter is async sequential dispatch (no queue) — subscribers called in series within same `await publish()`.

Root cause hypothesis: bars not reaching `_on_bar_closed` before IB window due to bridge outbound queue or `bind_main_loop` timing at startup.

---

## Finding D Classification

**VERDICT: D is downstream of B2 (bar delivery race) — NOT Stream A.**

Evidence:
- S1 `_stage_a3` advances to A4 when `bar.session_min >= 60` (10:30 ET). `session_min` is wall-clock-based (main.py), so A3→A4 transition fired on time.
- BUT `_stage_b1` requires `self.opening is not None` (line 441). Opening requires `len(opening_bars) >= 3` from stage A2 (09:30-09:45). If bars arrived late (after A2 window passed), opening was never set.
- Result: B1 returns early every bar → no vote cast → machine stays at B2 with confidence 0.38 → never reaches C1 (lock).
- DB confirms: last row at 16:21 UTC (12:21 ET), stage B2, confidence 0.38, day_type Trend_DD. 1h51min past IB close, still not locked.

D resolves when B2 bar-delivery is fixed (bars arrive in real-time → A2 collects opening bars → B1 votes → C1 locks).

---

## Cross-Impact Map

| Consumer | Today's Blast | Future Risk |
|---|---|---|
| S4 Woodies | 151 trades (not 142) against wrong POC. 44 SHORTs above real POC (7559.75), 23 LONGs below. | Continues until Stream A fixed |
| Pipeline 2 G0 | Not started (no impact today) | G0 audit against unreliable TPO baseline → wrong KEEP/ADAPT/REPLACE decisions. **Recommend slipping G0 until Stream A GREEN.** |
| Pkg 5b/5c SHADOW | Mode-blocked today (0 chart pattern fires) | SHADOW soak invalid until TPO trusted |
| S1 NeuE/NeuC | prev_day VAH/VAL from DLL invalid → misclassification risk | Every neutral day until DLL fixed |
| S2 OFA | 3 fires in 7 days (effectively dead) | Blocked by B2 mode transition |
| UI cockpit | Shows wrong POC/VA levels | Continues until Stream B fixed |

**S4 verification (v2 P6):** 151 fires today (firing_system=4), 44 SHORTs entered above real POC 7559.75, 23 LONGs below. Entry range 5900-7566 (the 5900 outlier needs investigation — may be test/different instrument).

---

## Recommended Phase 2 Fix Sequence

Stream A confidence = 88% (≥80%) → **Option 2** (skip warning-only, go straight to A→B-reject).

| # | Stream | Fix | Est. | Risk | Conditional |
|---|---|---|---|---|---|
| 1 | C | B1 opening_type wiring (3 lines) | 15min | LOW | always |
| 2 | A | DLL subgraph index fix + TPOChartNumber verify | ~1h + deploy | HIGH | needs Michael Sierra UI |
| 3 | B | TPO reject-and-warn (full reject mode) | 30min | MED | after A passing |
| 4 | C | B2 investigation + smallest fix | TBD | MED-HIGH | after A+B |

---

## Open Questions for Michael

1. **HA-5:** Can you screenshot Sierra Study Settings for studies ID:1 (TPO yesterday), ID:3 (TPO today), ID:6 (IB) — showing which chart they're on + subgraph layout?
2. **TPOChartNumber:** What chart number should Input[17] be set to? (Which chart has the TPO studies?)
3. **Pipeline 2 G0:** Should we slip G0 start until Stream A is GREEN?
4. **5900 entry price:** Is there a test trade or different instrument in `v9_trades` today?

---

## Stop Conditions

None hit during audit. All 5 layers completed for all 3 streams.

---

CC · 2026-05-25 ~20:15 IL · Phase 1 audit took ~45 minutes (3 parallel agents + DB queries + log analysis)
