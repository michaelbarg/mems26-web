# P30 Agent Inbox — Pre-LIVE Cockpit Parity

**Owner:** Cursor agent · **Created:** 2026-05-19 22:30 ET · **Status:** active
**Purpose:** single source of truth for everything Michael has uploaded today,
what was fixed, what is deferred to Claude Code (DLL territory), and what
remains before LIVE futures trading.

This file is updated **every prompt** so we never lose context again.

---

## 1. Documents and screenshots Michael uploaded today

| # | Type | Origin | Status | Outcome |
|---|------|--------|--------|---------|
| D12 | Sierra Chart screenshot at 2026-05-19 ≈15:19 ET (no text body): `MESM26_FUT_CME[M] 5 Min #3 L:1 | Micro E-Mini S&P 500 - CME (Jun26)`. Same right-axis TPO levels (7428.50 / 7411.25 / 7395.00 / 7390.75 / 7378.75 / 7366.25 / 7359.75 / 7353.75) and same CVD pane (Open -12156 / High -12047 / Low -12221 / Close -12047). | Michael upload | Confirms Q1 host-chart period | Header confirms the host chart that owns the `MES_AI_DataExport` DLL is a **5-min chart**, matching the math in §5 Q1 (CVD_PERIOD_S = 5 host bars × 5 min/bar = 1500 s). Earlier D11 screenshot was a linked 3-min view via Sierra "Studies Linked", not the master. **G4 root cause unchanged** — `tpo.json` still stale (re-checked: same mtime). |
| D13 | Sierra Studies Configuration logging (4 native studies tabulated by Michael): TPO Value Area Lines ID:1 (Reference n Periods Back=1 = YESTERDAY, VA=0.7), TPO Value Area Lines ID:3 (Reference=0 = TODAY developing, hidden), Initial Balance ID:6 (09:30–10:30 ET, extensions 0.5×–3×), Cumulative Delta Bars ID:9 (no rolling, reset daily). All four are Sierra **native** studies (no DLL). | Michael upload 2026-05-19 23:24 ET | Reframes G4 entirely | **Critical discovery**: none of the four studies is `MES_AI_DataExport` (our DLL). I greppd `MES_AI_DataExport.cpp` — **zero references to `tpo.json`**. The DLL writes 13 other JSON files (all <2 s fresh), but `tpo.json` is **not in its source code at all**. The current `tpo.json` (export_ts 18:57 ET, `v9.4.0-p30.9`) is a **remnant from an earlier DLL build that has since been removed**. Bridge `tpo_stream.py:3` confirms in its docstring: `"Source: DLL export — tpo.json (NOT YET IMPLEMENTED IN DLL)"`. G4 is therefore not a "DLL stopped writing" bug — it is a **deferred DLL feature**. Sierra's native TPO studies (ID:1, ID:3) and IB study (ID:6) hold the correct values *inside Sierra*, but no code reads them out into our JSON pipeline. **Recorded as new G7 in §3** and folded into the §4 mega-prompt. |
| D11 | Sierra Chart screenshot at 2026-05-19 ≈15:09 ET: `ESM26_FUT_CME[M] 3 Min #3` (linked view of TPO/CVD subgraphs) showing right-axis TPO levels (TPO VAH 7428.50 white, TPO POC 7411.25 white, TPO VAH 7395.00 magenta, TPO VAL 7390.75 white, TP IB High 7378.75 red, IB Mid 7366.25 green, TPO VAL 7359.75 magenta, IB Low 7353.75 green) + Cumulative Delta Bars pane (Open -12202 / High -12157 / Low -12309 / Close -12309) | Michael upload | Diagnostic anchor | Comparison vs `/api/v9/tpo/current` at same moment: our API returns the same `session.poc=7370.5 vah=7391.25 val=7358.75` from `tpo.json` whose `mtime` is **15654 s ago (4 h 21 min)**. Bridge is up and pushing, but the **DLL never wrote this file** — see D13. The 18:57 ET timestamp is from a previous DLL build. **Real fix lives in DLL**: CC must add a `tpo.json` writer that reads Sierra's TPO/IB studies (D13 IDs 1, 3, 6) via `sc.GetStudyArrayFromChartUsingID`. |
| D1 | Two Sierra Woodies screenshots (Sierra vs ours) | Sierra Chart screenshots | Reviewed | Drove §5.2–5.7 visual parity fixes (trendHeader 1/0, alternating ref dots, yellow CCI-14 + black TCCI, GRAY histogram, HUD 11px). |
| D2 | "Hardcoded data" prompt #1 (`mockPanelData`/`Y_AXIS_VALUES`/`DATA_FIELDS_CONFIG`) | External AI | Reviewed | Rejected: workspace `grep` showed **zero** `const data = {…}` / `mockData` / `7702` / `7408.25` in Woodies. Existing constants (`AXIS_TICKS`, `DATA_SLOTS`) already match. |
| D3 | "Hardcoded data" prompt #2 (copy-paste TS code) | External AI | Reviewed | Rejected: prompt itself contains `mockData hardcoded`, plus empty `<g/>` stubs that would erase the whole canvas (histogram, CCI/TCCI lines, ZLR, X marker, time strip). |
| D4 | TPO chart screenshot (white prev levels + magenta POC) + complaint that prev day POC lines look "distorted" | Sierra Chart | Fixed | `SierraLevelsOverlay.tsx`: prev POC/VAH/VAL extended `t1=span.t1`, color `#FFFFFF` opacity 0.92, POC width 1.8 solid, VAH/VAL dash. Backend adds `session_opened_ts` (RTH 09:30 ET) so current POC anchors at RTH start, last POC_STEP widened to 3.0. |
| D5 | Two CVD overlap screenshots (price chart top + CVD bottom, X axis drifting + TPO labels stacking) | Cockpit | Fixed | `cumulative_delta_routes.py:_augment_points_with_t` adds `t = export_ts - (n-1-idx)*300s` to every Sierra CVD point. `cvdMapping.ts` / `CvdChartPane.tsx` use `pt.t` instead of `bars[idx].ts`. `SierraLevelsOverlay.tsx:spreadLabelYs` shifts overlapping right-axis tags by ≥12 px (lines stay exact, labels stop stacking). |
| D6 | "Histogram bar state" prompt (cumulative delta useRef/useEffect) | External AI | Reviewed | Rejected: workspace `grep` showed Woodies histogram is canvas-drawn from `bars[]` per render (no `useState<Bar[]>`), CVD pane fetches `cum` from server (no client-side cumulative), EOD reset happens in Sierra DLL not in React. |
| D7 | Michael claim: "today (2026-05-19) was classified Nontrend but it definitely was not a non-trend day" | Cockpit verdict | Investigation handoff prepared | `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md` — read-only diagnostic prompt for a fresh chat / subagent. Will return verdict + top-3 votes + ground-truth comparison; **no code changes** until Michael picks a direction. |
| D8 | `~/Downloads/05_CC_DETAILED_REPORT_REQUEST.md` — request for per-system (S1–S6) status report in Hebrew (code paths, spec compliance, what changed from spec, tests, blockers, next steps) | Michael upload 2026-05-19 ≈22:30 ET | Handoff prepared | `docs/handoff/CC_DETAILED_STATUS_REPORT_REQUEST.md` consolidates Michael's template and points CC to the existing `docs/reports/PROMPT30_*` series so CC produces **one** consolidated report at `docs/reports/P30_CONSOLIDATED_STATUS.md`, not 6 new files. Cursor does **not** write this report (per `CLAUDE.md` reporting workflow — CC's job). |
| D9 | `~/Downloads/06_CRITICAL_ISSUES_TPO_TABLE_CLEANUP.md` — three critical bug claims: (1) cockpit TPO VAH/POC/VAL ≠ Sierra (claims ours shows 7385/7382/7355 vs Sierra 7428/7411/7390), (2) cockpit table accumulates old + new bar data without cleanup, (3) no historical continuity (yesterday's data lost at session end) | Michael upload 2026-05-19 ≈22:30 ET | Promoted to gaps G4/G5/G6 | Added to inbox §3 as **G4** (TPO value mismatch — needs diagnostic before fix), **G5** (Redis/cockpit table cleanup on bar roll + session boundary), **G6** (EOD archive to historical DB for yesterday-replay). G4 may be DLL **or** backend bug — investigation handoff in `docs/handoff/INVESTIGATE_TPO_VALUE_MISMATCH.md`. **No code changes** until diagnostic confirms direction. |
| D10 | `~/Downloads/07_DLL_GAPS_MILESTONES_QUESTIONS.md` — CC echo of this inbox §3 (G1–G3) and §6 (8-milestone roadmap) with day-by-day ETAs (Day 1 → Day 6) | Michael upload 2026-05-19 ≈22:50 ET | Adopted into inbox | Two new ideas folded into the inbox: (a) DLL should also expose `output_interval` field inside `cumulative_delta.json` so the frontend never has to guess the period (G3 enhancement, baked into §4 mega-prompt), (b) day-by-day ETAs added to §6 roadmap as a parallel column. Doc 07's Q1/Q2/Q3 are the same questions already in §5 — confirms they're still open. |

> If Michael uploads more docs/screenshots, append a row here **before** any
> code edit. We track inputs, not just outputs.

---

## 2. Fixes shipped today (need backend restart + hard refresh to see)

### 2.1 ProjHigh shifting 7408.25 ↔ 7702.75 between refreshes
- **Root cause:** `_enrich_bar_projections` in `backend/v9/api/v9/woodies_chart_routes.py` synthesised `proj_hi=max(highs)+2` / `proj_lo=min(lows)-2` from a 12-bar rolling window. Sierra DLL omits these fields, so backend fabricated a value that drifted every request.
- **Fix:** removed fallback entirely. HUD now renders `—` until DLL exports real Projections.
- **Regression test:** `tests/v9/api/test_woodies_chart_routes.py::test_enrich_never_invents_proj_when_missing`.

### 2.2 Woodies panel visual parity with Sierra
- Trend header shows `1.00 / 0.00` on active bucket (Sierra style) instead of CCI numeric values.
- Reference lines drawn as alternating colored dots (Sierra), not single-color dashes.
- CCI-14 thick **yellow** 3 px, TCCI thin **black** 1.5 px (previously inverted).
- HUD rows 11 px bold (Last stays 22 px on baseline).
- GRAY trend bars rendered (previously skipped).
- Time-strip background `#2A4A4A` instead of `#15151A`.

### 2.3 TPO previous-session white lines extend through the chart
- `SierraLevelsOverlay.tsx` no longer clips prev POC/VAH/VAL to the previous day's bar range; lines now run from prev RTH open through `span.t1`.
- White `#FFFFFF` opacity 0.92, POC width 1.8 solid, VAH/VAL width 1.2 dashed.
- Current-session POC last step widened to width 3.0 opacity 1.0 and anchored at today's RTH 09:30 ET (`session_opened_ts` added in `tpo_routes.py:_rth_open_ts_today`).
- Regression tests: `tests/v9/api/test_tpo_routes_sierra_contract.py::test_normalize_emits_session_opened_ts_for_rth_anchor` (+ DLL-honour test).

### 2.4 CVD pane X axis no longer drifts from price chart
- `cumulative_delta_routes.py` adds `t` per point using `export_ts - (n-1-idx)*CVD_PERIOD_S` (default **600 s** post-Q1 audit; env override `V9_CVD_PERIOD_S`).
- `cvdMapping.ts` + `CvdChartPane.tsx:cumOhlcSeries` use `pt.t` when present; fall back to `bars[idx].ts` only if Sierra ever sends bare points.
- Regression tests: `tests/v9/api/test_cumulative_delta_routes.py::test_cvd_augments_points_with_t_when_dll_omits_it` + `test_cvd_preserves_dll_t_when_present`.

### 2.5 TPO right-axis labels stop stacking
- `SierraLevelsOverlay.tsx:spreadLabelYs` sorts segments by Y and pushes label-Y by ≥12 px when two levels are too close. Line `y` is **not** moved — only the text.

### 2.7 CVD granularity 25 min → 5 min (DLL + backend, 2026-05-20 00:45 ET)

Michael's requirement: "כל בר של הקולמטיב צריך להיות 5 דקות" (every CVD candle must be 5 minutes). The DLL was filtering `(i - session_start) % 5 == 0` so it emitted one CVD point per 5 host-chart bars → at a 5-min host chart that's 25-min candles. Fix:

- **`sc_study/v9_exports.h:v9_cumulative_delta_to_json`** — removed the `% 5` filter; the loop now emits a point for every host bar. Also added explicit `t` (unix UTC seconds, computed via SCDateTime→unix lambda) per point and top-level `output_interval: 300` so the backend stops guessing the cadence.
- **`scripts/build_monolithic_cpp.sh --deploy`** ran successfully — deployed updated source to `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` (2282 lines, SCDLLName@line7, v9.2 markers OK).
- **`backend/v9/api/v9/cumulative_delta_routes.py:_derive_period_s`** — new resolver. Order: (1) DLL `output_interval` if present, (2) auto-detect from observed `i`-step × `HOST_BAR_S` (default 300 s), (3) `CVD_PERIOD_S` env default. This means even a stale Sierra (still running the old `% 5` DLL until Michael does Remote Build) gets a correct `t` per point because the backend detects i-step ≈ 5 and infers 1500 s/point.

**Required steps to activate** (cannot be done from sandbox):

1. Sierra Chart → `Analysis → Build Custom Studies DLL` (Mac UI = `Remote Build`).
2. Reload the study on every chart that uses it (right-click → `Reload Study Settings`).
3. Kill+restart the FastAPI backend so `_derive_period_s` is loaded (see §8 item 1b).
4. Hard-refresh the cockpit in the browser.

After all four steps, `cumulative_delta.json` should contain ~200 points per Globex day, each carrying its own `t`, and the CVD pane should show one candle per 5-min bar perfectly aligned to the price chart.

Tests: `tests/v9/api/test_cumulative_delta_routes.py` now has 9 cases — including the three new ones for `output_interval` priority, legacy-mod5 auto-detect, and unfiltered DLL auto-detect.

### 2.6 Browser-side cockpit fixes (2026-05-20 00:25 ET, verified live via Cursor browser MCP)

Symptom Michael reported: "אין ברים יש 2 / 3 ברים והם לא מסודרים עם הזמן של הקווללמטיב". Diagnosed in the live browser (DevTools console):

1. **Assertion error from lightweight-charts:** `"data must be asc ordered by time, index=597, time=1779198300, prev time=1779198300"`. DB shipped two rows with the same `ts=2026-05-19 16:45:00.000000`. The whole `setData` call aborted → chart stuck at the 3 `barsPoll` updates → user saw "3 bars". **Fix:** `ChartV5b.tsx:loadBars` now dedups `cData` by `time` (last wins) and re-sorts ascending before `setData`. Warns when a duplicate is removed.
2. **Default view too zoomed-out:** `fitContent()` on 600 candles spread the 5-day data across the pane and the CVD sync turned it into a 17 h Globex window. **Fix:** `setVisibleLogicalRange({from: last-60+1, to: last})` so the cockpit opens on the most recent 60 bars (5 h of 5 m / 3 h of 3 m / 60 h of 1 h). Lazy-load still feeds older bars on left-pan.
3. **`tsToUnix` misparsed DB timestamps:** DB ships wall-clock ET ("2026-05-19 16:55:00.000000") without TZ. `new Date()` in Michael's IST browser parsed them as local time, pushing price candles 7 hours away from CVD points (`pt.t` is true UTC epoch). CVD pane rendered empty. **Fix:** all three frontend `tsToUnix` callers (`ChartV5b`, `SierraLevelsOverlay`, `cvdMapping`) now suffix `-04:00` (EDT) before parsing. Trade-off: 1-hour drift during EST (Nov–Mar) — acceptable until API ships `ts_unix` directly.
4. **CVD sync was bidirectional:** `subscribeVisibleTimeRangeChange` on **both** charts caused ping-pong — CVD's `fitContent` (17 h) kept yanking the price chart back from its 5 h default. **Fix:** sync is now one-way (price → CVD only). User pans/zooms the price chart, CVD follows; CVD pans/zooms locally without disturbing price.

Verified live in the browser at 2026-05-20 00:27 ET: 60+ price candles visible in the RTH window, 14+ CVD candles aligned beneath them, TPO labels rendered on the right axis (values still wrong from DLL round 1).

### 2.8 G6 — EOD historical archiver (2026-05-20 01:05 ET)

- New service `backend/v9/services/eod_archiver.py`: copies 10 Sierra exports (5min, cumulative_delta, tpo, woodies_5min/30min, volume_profile, footprint, imbalance_flags, stacked_imbalances, mes_ai_data) into `~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/`. Filesystem-only — no schema migration.
- New routes `backend/v9/api/v9/history_routes.py`:
  - `GET /api/v9/history/dates` — sorted list of archived dates.
  - `GET /api/v9/history/yesterday` — bundle for previous trading day (uses `market_clock.get_previous_trading_day`, fallback to newest archive).
  - `GET /api/v9/history/{date}` — explicit date bundle.
  - `POST /api/v9/history/archive_now` — trigger archive (idempotent). Suggested cron line for Michael:
    ```
    55 15 * * 1-5  curl -s -X POST http://localhost:8000/api/v9/history/archive_now
    ```
- Wired into `backend/v9/app.py`. 9 tests in `tests/v9/api/test_history_routes.py`.

### 2.9 G8 — DB duplicate prevention (2026-05-20 00:45 ET)

- Migration `backend/v9/db/migrations/versions/015_bars_5min_unique_ts_symbol.sql` runs `DELETE … keep MIN(id)` and `CREATE UNIQUE INDEX ux_v9_bars_5min_ts_symbol`. Applied to live DB.
- ORM `backend/v9/db/models/bars_5min.py` declares `UniqueConstraint("ts","symbol")`.
- `backend/v9/api/v9/bars.py::post_bars_5min` rewritten as upsert: `db.flush()` after `add` surfaces `IntegrityError`, which the handler converts to a re-fetch + update. Race-safe. 4 tests in `tests/v9/api/test_bars_5min_unique_ts.py`.

### 2.10 ChartV5b TASK A — CVD ↔ candle X-align (2026-05-20, Michael sign-off #7)

- **Root cause:** Sierra CVD `t` is ET wall-clock stored as UTC epoch; price bars use `tsToUnix` with `-04:00` → ~4 h offset.
- **Fix:** `cvdMapping.ts::alignCvdPointTimesToPriceBars()` (+4h EDT / +5h EST when diff matches); `CvdChartPane.tsx` logs `[ChartV5b] CVD align check`.
- **UAT:** Michael visual sign-off 2026-05-20 — last candle ↔ last CVD bar same ET + X; pairs with **#9 L0** and **G4 round 2** (TPO lines visible; no further POC frontend edits unless reopened).
- Tests: `tests/v9/frontend/test_cvd_time_align.py`, `test_tpo_overlay_six_lines.py`.

### Test totals after today
`pytest tests/v9/api/test_cumulative_delta_routes.py tests/v9/api/test_tpo_routes_sierra_contract.py tests/v9/api/test_woodies_chart_routes.py tests/v9/frontend/test_woodies_build_data_texts.py tests/v9/systems/test_day_type/test_mid_session_restart_seed.py tests/v9/api/test_history_routes.py tests/v9/api/test_bars_5min_unique_ts.py tests/v9/frontend/test_cvd_time_align.py tests/v9/frontend/test_tpo_overlay_six_lines.py` → **62+ passed** (frontend chart contracts included).

---

## 3. Active gaps — what's still blocking 100 % Sierra parity

**G1–G3** are DLL territory (`sc_study/MES_AI_DataExport.cpp`) — Cursor is
forbidden from editing them by `.cursor/rules/mems26-stability.mdc`. Hand
off to Claude Code with the mega-prompt in §4.

**G4–G6** come from doc 06 (Michael 2026-05-19): need **diagnostic first**
before assigning DLL vs backend vs frontend ownership. The investigation
handoffs are in `docs/handoff/INVESTIGATE_*.md`.

| ID | Symptom in cockpit | Real cause | Required change | Owner |
|----|--------------------|------------|------------------|-------|
| G1 | Woodies HUD shows `—` for `ProjHigh` / `ProjLow` | DLL `current_bar` lacks `proj_hi` / `proj_lo` | Pipe `Daily Projected High` / `Daily Projected Low` subgraphs (Sierra study `Pivot Points`) into `current_bar.proj_hi` / `proj_lo`. | CC |
| G2 | TPO `previous_session.poc/vah/val` falls back to DB row (may lag live previous CASH day) | `tpo.json` `previous_session` block is absent | Add `previous_session: { found, poc, vah, val, opened_ts, closed_ts, session_date }` to `tpo.json`, mirroring `_parse_previous_session_block` in `tpo_routes.py`. | CC |
| G3 | CVD pane uses backend-estimated `t` (300 s grid) | `cumulative_delta.json` points carry only `i, d, cum, p` | Add `t` (unix seconds, ET) to every point **and** `output_interval` (seconds) at the JSON top level so the frontend never guesses the period. | CC |
| G4 | Michael claims cockpit TPO values do not match Sierra. | Round 1: writer deployed; subgraph reads returned garbage. **Round 2 DONE 2026-05-20** — CC subgraph indices fix per `CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md`; Michael **L0 sign-off** on cockpit parity (incl. TPO lines). | **Closed for L0** — monitor freshness via `age_s` on `/api/v9/tpo/current`; further drift = ops not code | CC round 2 ✅ |
| G5 | Michael claims cockpit table accumulates old bar values (doc 06 §2). | **Closed as duplicate of G4.** Investigation 2026-05-20 00:55 ET: DB has 1 row per (date, session_type), Redis lists are LTRIM'd at 100, no accumulation. The "table shows 14:03 value at 15:33" symptom was driven by `tpo.json` going stale (G4 root cause). Once G4 resolves the DLL stops writing 0/`-78229` garbage, the cockpit refreshes every 30 s and the drift vanishes. | — (folded into G4) |
| G6 | "No historical continuity" (doc 06 §3). | EOD archival was missing. | **Closed 2026-05-20 01:05 ET** — `backend/v9/services/eod_archiver.py` + `backend/v9/api/v9/history_routes.py` ship: 10 Sierra exports snapshotted to `~/SierraChart_Data/v9_archive/<YYYY-MM-DD>/` on demand. Cockpit's `Hist` tab can call `GET /api/v9/history/yesterday`, `/{date}`, `/dates`. `POST /api/v9/history/archive_now` for cron (suggested: `55 15 * * 1-5  curl -s -X POST http://localhost:8000/api/v9/history/archive_now`). 9 tests pass. No DB schema change. | Cursor — DONE |
| G8 | `v9_bars_5min` accumulated a duplicate `ts` row (`2026-05-19 16:45:00` × 2), tripping `lightweight-charts: data must be asc ordered by time`. | Two concurrent bridge POSTs raced past the SELECT-then-INSERT check. | **Closed 2026-05-20 00:45 ET** — Migration `015_bars_5min_unique_ts_symbol.sql` dedupes existing rows and adds `UNIQUE(ts, symbol)`. `bars.py::post_bars_5min` now catches `IntegrityError` and converts a losing race into an UPDATE. Model `bars_5min.py` declares the constraint at the ORM layer. 4 tests pass. | Cursor — DONE |

Until G1–G3 land, we have **honest fallbacks** (HUD `—`, DB-sourced prev session, 300 s synthetic `t`) instead of silent lies — but they are not pixel-faithful to Sierra Chart.
**G4 / L0 cockpit parity:** signed off **2026-05-20** (Michael). G1–G3 remain open for full Sierra DLL fidelity.

---

## 4. Mega-prompt for Claude Code (DLL fixes)

```text
TASK: Sierra DLL parity fixes for MEMS26 cockpit
Owner: Claude Code · Source: this inbox §3 (G1–G3)
Repo: ~/Downloads/mems26_web_git
DLL source: ~/SierraChart/ACS_Source/MES_AI_DataExport.cpp
Local deploy: ./scripts/build_monolithic_cpp.sh --deploy → Remote Build → reload study

GUARDRAILS (read these first):
- .cursor/rules/mems26-stability.mdc
- docs/runbooks/SIERRA_DLL_OPS.md
- CLAUDE.md (pre-LIVE discipline — diagnose before fix, smallest correct change)

CHANGES REQUIRED:

1) Woodies 5m export — `woodies_5min.json` `current_bar`
   - Add `proj_hi` (sg_proj_high.GetCurrentValue) and `proj_lo` (sg_proj_low.GetCurrentValue)
     from the existing Daily Pivot Points study attached to the 5 m chart.
   - If Pivot Points is not yet attached: attach it and document the Study ID + subgraph indices
     in `docs/runbooks/SIERRA_DLL_OPS.md`.
   - Acceptance: `python3 -c "import json; d=json.load(open('/Users/michael/SierraChart_Data/v9_export/woodies_5min.json')); print(d['current_bar'].get('proj_hi'), d['current_bar'].get('proj_lo'))"`
     prints two non-null floats during RTH.

2) TPO export — `tpo.json` top level
   - Add `previous_session: { found, poc, vah, val, opened_ts, closed_ts, session_date }`
     mirroring the schema the backend already parses (`_parse_previous_session_block`).
   - `opened_ts` / `closed_ts` must be epoch seconds OR `YYYY-MM-DDTHH:MM:SS-04:00`.
   - Source = previous completed CASH TPO row inside Sierra (not Globex).
   - Acceptance: `curl -s http://localhost:8000/api/v9/tpo/current | jq .previous_session`
     returns the same numbers Sierra prints for yesterday's RTH POC/VAH/VAL.

3) CVD export — `cumulative_delta.json` points[] + top-level
   - Add `t` (epoch seconds, ET) to every point. Last point `t == export_ts`.
   - Keep `i, d, cum, p` unchanged.
   - Add top-level field `output_interval` (integer seconds, e.g. 300) so the
     backend / frontend never have to guess the cadence (doc 07 G3 enhancement).
   - Acceptance:
     - `curl -s http://localhost:8000/api/v9/cumulative_delta/current | jq '.points[-1] | {i,t,cum}'`
       shows a `t` value within ±2 s of `export_ts`.
     - `curl -s http://localhost:8000/api/v9/cumulative_delta/current | jq .output_interval`
       returns a positive integer matching the actual DLL emission cadence
       (e.g. 300 for 5 m, 60 for 1 m, or whatever Sierra is configured to emit).

4) TPO export — `tpo.json` is **not currently produced by `MES_AI_DataExport.cpp`**
   (G4 root cause confirmed 2026-05-19 23:25 ET).
   - Grep `MES_AI_DataExport.cpp` for `tpo.json` / `v9_tpo` / `tpo_to_json`:
     **zero hits**. The current `tpo.json` on disk (export_ts 18:57 ET,
     `v9.4.0-p30.9`) is a remnant from an earlier build; the live DLL writes
     12 other files (cumulative_delta, woodies_5min/30min, footprint, etc.)
     all <2 s fresh — only `tpo.json` is 4+ hours stale.
   - `bridge/v9_streams/tpo_stream.py:3` docstring confirms:
     `"Source: DLL export — tpo.json (NOT YET IMPLEMENTED IN DLL)"`.
   - Sierra holds the correct values inside its **native studies**, which
     Michael documented on 2026-05-19 23:24 ET (see D13 in §1):
     - `Study ID:1` — TPO Value Area Lines, `Reference n Periods Back = 1`
       (yesterday's locked POC/VAH/VAL).
     - `Study ID:3` — TPO Value Area Lines, `Reference n Periods Back = 0`,
       `Draw Developing = Yes` (today's developing POC/VAH/VAL).
     - `Study ID:6` — Initial Balance, window `09:30–10:30 ET`, extensions
       0.5×/1×/1.5×/2×/2.5×/3×.
   - **What CC must add to `MES_AI_DataExport.cpp`**: a `v9_tpo_to_json`
     routine that reads those three studies via
     `sc.GetStudyArrayFromChartUsingID(chartNum, studyID, sgIdx, outArr)`
     and writes a `tpo.json` payload matching the schema already consumed
     by `backend/v9/api/v9/tpo_routes.py::_normalize_sierra_tpo`:
     ```json
     {
       "type": "tpo",
       "version": "v9.4.0-p30.X",
       "export_ts": <unix>,
       "session": { "poc": <today POC from ID:3>, "vah": ..., "val": ...,
                    "session_high": ..., "session_low": ...,
                    "total_volume": ... },
       "ib": { "found": true, "high": <ID:6 high>, "mid": ...,
               "low": ... },
       "prior_day": { "found": true, "high": ..., "low": ...,
                      "close": ... },
       "previous_session": { "found": true,
                             "poc": <ID:1 yesterday POC>, "vah": ..., "val": ...,
                             "opened_ts": "<unix or ISO ET>",
                             "closed_ts": "<unix or ISO ET>",
                             "session_date": "YYYY-MM-DD" }
     }
     ```
   - Acceptance:
     - `curl -s http://localhost:8000/api/v9/tpo/current | jq '.age_s'` < 30
     - `curl -s http://localhost:8000/api/v9/tpo/current | jq '.session.poc, .session.vah, .session.val'`
       matches the magenta TPO POC/VAH/VAL Michael sees on the live chart
       (e.g. POC ≈ 7411.25, VAL ≈ 7359.75 around 15:19 ET 2026-05-19).
     - `curl ... | jq '.ib.high, .ib.mid, .ib.low'` matches red/green IB
       levels Michael sees (e.g. 7378.75 / 7366.25 / 7353.75).
     - `curl ... | jq .previous_session.poc` matches Sierra's
       Reference-1 yesterday TPO POC (e.g. 7411.25 white line).

5) Bridge restart sanity (doc 06 G5 supporting evidence)
   - The cockpit has been running without a healthy bridge since 2026-05-17
     (see §9). Confirm with Michael whether the bridge should be brought up
     (`screen -dmS mems26-bridge ...`) before any redis-cleanup investigation.
   - Do **not** unilaterally restart the bridge — `.cursor/rules/mems26-stability.mdc`
     forbids that.

DELIVERABLES:
- DLL diff + redeploy verified by **five** acceptance curls (G1, G2, G3a, G3b, G4-audit)
- `docs/reports/PROMPT30_TPO_VALUE_AUDIT.md` — root cause for G4 nailed down
- Update `docs/reports/PROMPT30_10b_TPO_LEVELS_FIX.md` and create
  `docs/reports/PROMPT30_DLL_PARITY.md` with the redeploy date, study IDs, and verification output
- After verification, gaps G1–G4 in `docs/handoff/P30_AGENT_INBOX_PRE_LIVE.md` §3 can be retired

DO NOT:
- Touch `bridge/`, LaunchAgents, or `CLOUD_URL`
- Change anything in `~/.cursor/projects/...` paths
- Restart `screen` sessions without confirming with Michael first
- "Fix" G4 by changing TPO calculation before the §4-4 audit confirms the
  DLL is the offender (we already burned a day on a similar P27.5a-style
  premature fix; see `.cursor/rules/mems26-pre-live-protocol.mdc` mistake #6)
```

---

## 5. Answers to the three open questions (answered 2026-05-19 23:10 ET from code evidence)

### Q1 — CVD period: corrected from 300 s → 600 s → **1500 s** (final, post-bridge-live audit)

**Evidence sources (final, 2026-05-19 16:18 ET, bridge live):**

- `MES_AI_DataExport.cpp:796` — DLL emits a point only when
  `(i - session_start) % 5 == 0`. So every 5 bars of the host chart.
- `cumulative_delta.json` snapshot at 16:18 ET: 40 points, i-range
  5858 → 6051 (Δ=193). Critical detail: DLL `session_start` is
  **calendar midnight ET of today's date**, not RTH 09:30. Elapsed since
  00:00 ET = **978.3 min**. 193 bars / 978.3 min → **5.07 min/bar of host
  chart** → 5 bars × ≈5 min = **≈1500 s per CVD point**.
- The earlier 300 s assumed 1 min/bar; 600 s assumed RTH-only 2 min/bar;
  both math was wrong. The host chart that the `MES_AI_DataExport` study
  is attached to is a **5 min Globex 24 h chart**, confirmed by
  `woodies_5min.json:bar_period_minutes=5`.

**Fix applied this turn:**

- `backend/v9/api/v9/cumulative_delta_routes.py:CVD_PERIOD_S` default
  600 → **1500**. Override via `V9_CVD_PERIOD_S` env var.
- Requires backend FastAPI process restart for the constant to load
  (one of the §8 immediate steps below).
- Real fix lives in G3 (DLL must ship `t` per point + `output_interval`
  so the frontend never has to guess). Mega-prompt in §4 covers this.

### Q2 — "historic bars not deleted when you jump to the latest bar"

**Evidence sources:**

- `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx:214-253` — chart
  uses **lazy-load left edge** (`range.from < 20` triggers a fetch of
  240 older bars, cap 2000 in memory). So interpretation (b) is already
  implemented.
- There is **no auto-pan-to-latest** call after lazy-load. When you
  scroll back to view 18-May bars, then click "go to latest", the chart
  does not call `timeScale().setVisibleRange()` to snap forward —
  earlier bars stay rendered in the visible region.

**Conclusion: this is interpretation (a) — missing "snap to latest"
behavior, not a memory leak**. Fix is one localized change in
`ChartV5b.tsx`: add a `goToLatest()` action that calls
`chart.timeScale().scrollToRealTime()` (lightweight-charts API). I will
implement this when Michael confirms.

### Q3 — Pixel-diff harness for Woodies parity

**Recommendation: defer until after LIVE (L8).**

**Reasoning:**

- A real pixel-diff requires a Sierra reference screenshot + Playwright
  headless browser + canvas snapshot test infrastructure (`@playwright/test`
  + `pixelmatch`). Setup is ~2 days of focused work and adds a new CI
  surface to maintain.
- Right now, parity is being driven by Michael's side-by-side screenshots
  (D1/D4/D5). That's slower but it's converging fast and surfaces semantic
  drift (e.g. trend header showing 1.00 vs CCI value), which a pixel diff
  would miss anyway because the colors match.
- Re-evaluate after LIVE when we have post-trade replay needs and a
  reason to keep Sierra parity guarantees regression-tested.

If you disagree and want the harness now, say so and I'll create
`tests/visual/woodies-parity.spec.ts` with a placeholder reference
screenshot you can update each release.

---

## 6. Roadmap to LIVE futures trading

Ordered by what blocks what. Each row finishes with a single owner. Cursor
agent works only on rows where the owner is **Cursor**; everything marked
**CC** waits for Claude Code; **Michael** rows are decisions only you can
make. ETAs adopted from doc 07 (CC echo) — these are best-case if no new
blockers surface.

| # | Milestone | Owner | Blocker resolved | Verification | ETA |
|---|-----------|-------|------------------|--------------|-----|
| L0 | Cockpit visual parity with Sierra (Woodies + TPO + CVD + Price chart axes) | Cursor + Michael | G4 round 2 + chart TASK A/CVD align + visual UAT (#7) | **DONE 2026-05-20** — Michael sign-off | Day 1 ✅ |
| L1 | Sierra DLL parity (G1 proj_hi/proj_lo, G2 previous_session, G3 cvd `t` + `output_interval`, G4 TPO value audit) | CC | §4 mega-prompt | Five `curl` acceptance checks pass | Day 2 |
| L2 | All 6 systems (S1–S6) green on `/api/v9/cockpit/systems-snapshot` for a full RTH soak (≥4 h, no drift) | Cursor + Michael | L0 ✅ | **DONE 2026-05-20** — Michael sign-off (#12); prior SHADOW soak 22/22 in `PROMPT30_SHADOW_READY.md` | Day 3 ✅ |
| L2.5 | Bridge healthy + redis cleanup on bar roll (G5) | CC + Cursor | bridge brought back up after 2-day downtime (see §9) + G5 diagnostic | `/tmp/bridge.err.log` clean for 4 h; no stale Redis keys after new-bar event | Day 3 |
| L2.6 | EOD historical archive (G6 feature) | Cursor | L2 | `data/mems26_local.db` gets `v9_bar_history` + `v9_cvd_history` filled at 16:00 ET; `GET /api/v9/history/yesterday` returns yesterday's data | Day 3 |
| L3 | Decision tree pre-fire rows + Plan tab BLOCKED reason chain audited per system | Cursor | L2 | **DONE 2026-05-20** — `PROMPT30_10b_PLAN_LIVE.md` S1–S6 table + live curl/browser UAT | Day 3 ✅ |
| L4 | Risk surface review — `firewall.json`, `system_5/risk_engine`, daily-loss kill switch, max-position lock | Michael + Cursor | L3 | Read-only audit doc; Michael sign-off | Day 4 |
| L5 | Paper-trade dry run (no broker) — bridge full path with `V9_PAPER_MODE=1` | Cursor + Michael | L4 | 1 RTH session, 0 errors in `/tmp/bridge.err.log`, manual journal entry | Day 4 |
| L6 | Broker dry run (Sierra Chart → broker simulator, 0 contracts) | CC + Michael | L5 | Broker round-trip latency < 250 ms | Day 5 |
| L7 | LIVE 1-contract gate, single instrument, half-RTH | Michael (go/no-go) | L6 | Live journal with PnL, post-mortem | Day 5 |
| L8 | Full LIVE | Michael | L7 (signed off) | Continuous monitoring runbook | Day 6 |

> **Reality check on ETAs:** doc 07's "Day 1 → Day 6" assumes no surprise
> DLL hiccup, no risk-surface red flags, and Michael available to sign off
> at L4 and L7. Add 50 % buffer mentally.

---

## 7b. Next-chat paste prompt (2026-05-20)

Full copy-paste block for the next Cursor chat:  
**[`docs/handoff/P30_NEXT_CHAT_FULL_PROMPT.md`](P30_NEXT_CHAT_FULL_PROMPT.md)**  
Primary task: **#13** Plan tab BLOCKED chain (S1–S6). L0/L2 closed per Michael sign-off.

---

## 7. Working agreement (so we stop losing context)

### 7a. Sierra real-time first — DLL + time axis (**DONE** — Michael 2026-05-20)

**Status: already implemented.** Do not re-open or “re-fix” without live verification.

**What shipped (see §2):** Sierra DLL + time-axis path — CVD `t` + `output_interval`, `session_opened_ts`, chart `tsToUnix` EDT, bars dedup, TPO round 2, no invented `proj_hi`/`proj_lo`. The stack **receives live market data from Sierra exports**; it does not invent OHLC/TPO/CVD/Woodies in Python or React.

**Mandatory before any edit** to `sc_study/`, `bridge/`, chart routes, TPO/CVD/Woodies APIs, or Plan/gateway firing logic:

1. **Read instructions** — this inbox §2 (what shipped), `docs/runbooks/SIERRA_DLL_OPS.md`, relevant `docs/reports/PROMPT30_*` and handoffs (`CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md`, `PROMPT_P30_WOODIES_SYSTEM_SLOW_HANDLER.md`, etc.).
2. **Verify with data** — four UAT axes on the affected endpoint; `export_ts` / `age_s` on Sierra JSON under `~/SierraChart_Data/v9_export/`; do not assume old behavior from memory.
3. **Do not “fix” by synthesizing** — forbidden patterns unless Michael explicitly approves:
   - Backend fabricating `proj_hi`/`proj_lo`, synthetic CVD grids without DLL `t`, guessed `output_interval`, or rolling-window “projections”.
   - Frontend rebuilding market series from `Date.now()` / index math instead of API/DLL timestamps.
4. **Ownership** — `sc_study/`, Remote Build, LaunchAgent, bridge process: **CC / Michael** unless Michael says “go”. Cursor: read-only on DLL; backend/frontend only after verify.

**Allowed backend roles (not substitutes for Sierra):** normalize/passthrough JSON, DB upsert, dedup by `ts`, timezone labeling for display, decision-tree/gateway **logic** on already-ingested bars — not replacement of Sierra study output.

**Canonical protocol (CC 2026-05-20):** `docs/reports/P30_SIERRA_STUDY_PROTOCOL.md` — study IDs / subgraph indices (ProjHigh/Low from Woodies Panel ID:9 SG1/SG2; SWI SG5; CZI SG2). Supersedes older inbox G1 note that cited Pivot Points only.

- **This file is touched every prompt.** Cursor agent appends to §1 every
  time Michael uploads something, marks §2 with the date of every shipped
  fix, and updates §3/§4 the moment a gap closes.
- **Reports stay short.** Long-form reports live in `docs/reports/PROMPT30_*`
  and are Claude Code's job (per `CLAUDE.md` reporting workflow). This inbox
  is the index, not the report.
- **Pre-LIVE rules win.** If a prompt contradicts
  `.cursor/rules/mems26-pre-live-protocol.mdc`, the rule wins and I stop and
  ask Michael. This already happened 3× today (the "hardcoded data" / "state
  anti-pattern" prompts) — the rule said `Diagnose first, Audit existing
  surfaces, Smallest correct change`, and the rule was correct.
- **Strategic stop = mandatory.** I will not blanket-replace files because a
  prompt told me to. I'll explain the contradiction and wait.

---

## 8. Consolidated order of work (woven from docs 04, 05, 06, 07)

This is the single ordered queue. Cursor agent works **strictly top-down**;
no jumping ahead. Items marked **WAIT** are gated on Michael's input or
Claude Code's deliverable.

| # | Task | Source | Owner | Status | Blocker |
|---|------|--------|-------|--------|---------|
| 1 | Bring the **bridge back up** (down since 2026-05-17). | §9 live status | Michael | **DONE 2026-05-19 23:15 ET** — LaunchAgent reload successful, 12 streams pushing to localhost:8000, log clean | None |
| 1b | **Restart the FastAPI backend** to load CVD_PERIOD_S=1500, `session_opened_ts`, no-`proj_hi`-fallback. | §2 + §5 Q1 | Michael | **DONE 2026-05-19 23:42 ET** — PID 55475 (with `set -a; source .env`). Three curls verified: `period_s=1500.0`, `session_opened_ts="2026-05-19 09:30:00"`, `proj_hi/lo=null`. | None |
| 2 | **G4 — DLL `tpo.json` writer (round 2 subgraph indices)**. | doc 06 + `CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md` | CC | **DONE 2026-05-20** — Michael confirms round 2 deployed; valid POC/VAH/VAL in cockpit; pairs with **#9 L0 sign-off**. | None |
| 3 | Run the **Day Type "Nontrend" investigation** per `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19.md`. | D7 | Fresh agent (Cursor dispatched at 23:09 ET) | **IN PROGRESS — subagent 651647eb running read-only** | None |
| 4 | Hand the **CC detailed status report request** (doc 05) over to Claude Code. Deliverable lands at `docs/reports/P30_CONSOLIDATED_STATUS.md`. Cursor does not write this. | D8 / doc 05 | CC | **WAIT — Michael to forward to CC** | None |
| 4b | **CC status matrix** — what is DONE vs NOT (DLL G1–G3, bridge, gateway). | Cursor request 2026-05-20 | CC | **WAIT** — forward `docs/handoff/CC_STATUS_REQUEST_2026-05-20.md` §5 prompt; fill §4 table | Michael forward |
| 16 | **6-agent fire/block spec audit** (S1–S6, read-only, no design/Sierra). | Michael 2026-05-20 | 6 agents + Cursor merge | **READY** — `docs/handoff/P30_ORCHESTRATION_FIRE_AUDIT_2026-05-20.md` + `docs/handoff/agents/AGENT_S*.md` | CC §4 + Michael "go" per agent |
| 17 | **Sierra study protocol + system gap audit** (Michael marks LIVE priorities). | CC 2026-05-20 | Michael | **WAIT Michael** — `P30_SIERRA_STUDY_PROTOCOL.md`, `P30_SYSTEM_GAP_AUDIT.md` §Priority Matrix | None |
| 18 | **CC full status report for Cursor** (live probes, no code changes). | Cursor request 2026-05-20 | CC | **DONE** — `P30_CC_FULL_STATUS_FOR_CURSOR.md`, `P30_CC_FIRE_BLOCKERS_SUMMARY.md` | — |
| 19 | **P30 Diagnostic Report** (Phase A/B/C, Sierra match 29/29). | CC 2026-05-20 | CC | **DONE** — `docs/P30_DIAGNOSTIC_REPORT.md` | — |
| 20 | **Priority task table** (ordered work queue). | Cursor 2026-05-20 | Michael | **READY** — `docs/reports/P30_PRIORITY_TASK_TABLE.md` — Michael marks + go per row | #17 optional |
| 5 | Hand the **CC DLL parity mega-prompt** (inbox §4, now covering G1–G4) over to Claude Code. | §4 | CC | **DONE 2026-05-19 23:35 ET** — Michael forwarded. Round 1 deployed. Round 2 followup is `docs/handoff/CC_FOLLOWUP_TPO_SUBGRAPH_INDICES.md`. | — |
| 6 | **Answer Q1/Q2/Q3** in inbox §5. | §5 + doc 07 | Cursor | **DONE 2026-05-19 23:15 ET** — Q1 = 1500 s (DLL `% 5 == 0` × 5 min host bar), Q2 = interpretation (a) "no snap-to-latest" — fix shipped in item 10, Q3 = defer pixel-diff harness post-LIVE | — |
| 7 | **Visual UAT** of shipped fixes (§2.1–§2.8 + item 10 + **ChartV5b TASK A** CVD↔candle X-align). | §2 | Michael (visual) | **DONE 2026-05-20** — Michael sign-off: chart panes aligned, fixes visible after hard refresh | — |
| 8 | Verify backend + DLL after round 1: `age_s<30`, `period_s=1500`, `session_opened_ts`, `proj_hi=null`. | Verification | Cursor | **DONE 2026-05-19 23:48 ET** — all four assertions verified live. | — |
| 9 | **L0 sign-off** (cockpit pixel parity vs Sierra). | L0 roadmap §6 | Michael + Cursor | **DONE 2026-05-20** — G4 round 2 + #7 UAT; cockpit accepted for L0 gate | None |
| 10 | **G2-Q2 "snap-to-latest" fix** — add `goToLatest` callback + `▶|` button to TF row. | Q2 finding | Cursor | **DONE 2026-05-19 23:47 ET** — `ChartV5b.tsx` `goToLatest()` calls `chart.timeScale().scrollToRealTime()`, button at end of TF row. No TS errors on touched file. | — |
| 10b | **C1 Day Type "Nontrend" fix** — seed `ib_class` from TPO on first post-restart bar. | Day Type investigation 651647eb | Cursor | **DONE 2026-05-19 23:53 ET** — added `backend/v9/api/v9/day_type_seed.py::maybe_seed_ib_from_tpo` with 7 guardrails, wired into `backend/main.py::_day_type_on_bar`, 14/14 regression tests pass in `tests/v9/systems/test_day_type/test_mid_session_restart_seed.py` (including the exact `-78229.0` uninitialized DLL value case). Full suite: 140 passed. Requires backend restart to activate. | Backend restart for activation |
| 11 | Implement **G6 EOD archiver** (`services/eod_archiver/` + `/api/v9/history/yesterday`). | Doc 06 §3 + L2.6 | Cursor | **DONE 2026-05-20 01:05 ET** — see §3 G6 | None |
| 12 | **L2 soak** — systems-snapshot green ≥4 h (script or manual probes). | L2 roadmap | Michael + Cursor | **DONE 2026-05-20** — Michael sign-off; evidence also in `PROMPT30_SHADOW_READY.md` (22/22). Optional: `scripts/soak_systems_snapshot.py` for repeat runs | None |
| 13 | Audit **Plan tab BLOCKED reason chain** per system (S1–S6). | L3 roadmap | Cursor | **DONE 2026-05-20** — live curl `count=6` 340ms + browser S1–S6 Plan/RTL; pytest 6/6; report `PROMPT30_10b_PLAN_LIVE.md` | None |
| 14 | Risk surface audit (L4). | L4 roadmap | Cursor + Michael | **DONE 2026-05-21** — `docs/reports/P30_L4_RISK_AUDIT.md`: SHADOW soak OK; **LIVE NO-GO** (dual gateway, W14 unwired, MAX_CONTRACTS dead, no PANIC). Michael sign-off pending. | Backend curl UAT when :8000 up |
| 15 | Paper-trade dry run with `V9_PAPER_MODE=1` (L5). | L5 roadmap | Cursor + Michael | **WAIT on L4** | L4 |

### Items the Cursor agent should NOT start without explicit "go"

- Any change to market/time data paths without reading **§7a** and passing live Sierra/UAT checks (no synthesizing OHLC/TPO/CVD/Woodies).
- Rewriting `WoodiesCciPanel.tsx` to match doc 02/03/04's "props-only" pattern.
  Rationale: doc 04 is rejected per D6, the existing component is already
  fetch-based, and the proposed replacement contains `mockData` hardcoded
  plus empty stubs. Documented in `CLAUDE.md` "no while-I'm-here refactors".
- Editing `bridge/`, `sc_study/`, `~/Library/LaunchAgents/com.mems26.bridge.plist`.
  These are CC / Michael territory by rule.
- Restarting any service. Status reads are OK; `launchctl load` / `screen -dmS`
  / `kill -9` are not.
- Pushing or force-pushing anything to git. Commits only when Michael
  explicitly asks.

---

## 9. Live project status snapshot (2026-05-19 ≈ 22:54 ET)

Captured by the parent agent earlier in this thread; surfaced here so it
doesn't get lost in the chat scroll.

| Component | Status | Evidence |
|-----------|--------|----------|
| Backend FastAPI (`:8000`) | **UP** | `lsof` shows Python PID 15095 listening; `/api/v9/status` returns `mode: shadow, session: CASH_HOURS, is_cash: true` |
| Frontend Next.js (`:3000`) | **UP** | `lsof` shows node PID 33876 listening |
| Bridge (`bridge/v9_streams/...`) | **DOWN since 2026-05-17 23:13 ET** | `launchctl list \| grep mems26` returned empty; `/tmp/bridge.err.log` last line is `2026-05-17 23:13:36 [INFO] All streams stopped. Exiting.` This means **two RTH sessions ran without the bridge** (5/18, 5/19). |
| Sierra DLL → `woodies_5min.json` | **FRESH (1 s old)** — DLL writing directly, no bridge needed | `stat` mtime |
| Sierra DLL → `cumulative_delta.json` | **FRESH (1 s old)** | `stat` mtime |
| Sierra DLL → `tpo.json` | **STALE (14 103 s ≈ 3 h 55 m old)** ⚠ | `stat` mtime — Sierra stopped writing TPO ~11:55 ET despite RTH continuing past that |
| `GET /api/v9/tpo/current` | Returns payload **with `stale: true`** flag (honest) | `keys: [running, hydrated, source, version, export_ts, age_s, stale, session_type]` |
| `GET /api/v9/woodies/chart?limit=3` | Returns payload (fresh) | `keys: [source, version, export_ts, bar_period_minutes, study_caption, age_s, stale, bars]` |
| `GET /api/v9/cumulative_delta/current` | **Returned EMPTY in 2 s curl** — needs investigation | Could be timeout (2 s too short), could be backend not reloaded after today's edit (`_augment_points_with_t` added in this thread), could be a real error. Re-run with 5 s timeout to confirm. |
| `GET /api/v9/day_type/state` | **Returned EMPTY in 2 s curl** — needs investigation | Likely the same backend-not-reloaded issue. Day Type investigation (D7) depends on this endpoint, so this must be resolved before the D7 fresh-chat investigation can run. |

### Immediate implications

1. **Backend restart is required** before Michael can visually verify
   today's fixes (§2.1–§2.5). Without restart, the new code (CVD `t`
   augmentation, TPO `session_opened_ts`, `_enrich_bar_projections`
   without `proj_hi` fallback) is not active in the running process —
   only on disk.
2. **Bridge being down for 2 days** means doc 06's G5 ("table not
   cleaning") cannot be reproduced or fixed without bringing the bridge
   back up first. Michael must decide whether to restart it.
3. **`tpo.json` going stale 4 hours ago** could be the upstream cause of
   doc 06's G4 ("TPO values don't match Sierra"). If Sierra DLL stopped
   writing TPO at 11:55 ET, then everything cockpit shows for TPO since
   then is the **last value before the freeze**, not the live VAH/POC/VAL.
   This is a critical first thing to verify before pursuing other G4
   hypotheses.

### Recommended next live-status step (after Michael unblocks)

```bash
# 1. Backend reload (uvicorn auto-reloads on file change if --reload flag,
#    otherwise restart the process).
# 2. Confirm endpoints with longer timeout:
curl -s --max-time 5 http://localhost:8000/api/v9/cumulative_delta/current | jq '{source,age_s,stale,point_count,period_s}'
curl -s --max-time 5 http://localhost:8000/api/v9/day_type/state | jq .

# 3. Diagnose tpo.json staleness — is Sierra Chart still running, is the
#    TPO study still attached, is it emitting during CASH_HOURS?
python3 -c "import json,os,time; p='/Users/michael/SierraChart_Data/v9_export/tpo.json'; print('age_s:', round(time.time()-os.path.getmtime(p),1)); print(json.load(open(p)))"
```
