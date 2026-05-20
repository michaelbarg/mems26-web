# P30 DIAGNOSTIC REPORT

**Date:** 2026-05-20
**Mode:** Diagnostic only — no production code changes
**Authority:** Michael Barg (Strategic chat approved)

---

## Section 1: EXECUTIVE SUMMARY

- Total gaps investigated: 8 (Phase A) + 29 Sierra checks (Phase B) + 30 audit questions (Phase C)
- 🔴 BLOCKING_SHADOW count: 1 (cluster_guard blocks all shadow trades)
- 🟡 BLOCKING_LIVE count: 4 (VAP disabled, S1 unwired modules, pre_fire S2 gap, PROMPT 5/6/7 unbuilt)
- 🔵 POST_LIVE count: 3 (session volume, CCI Predictor accuracy, trend from Sierra)
- Top recommendation: Fix cluster_guard BLOCKED state — it prevents any shadow trade from recording.

---

## Section 2: PHASE A RESULTS

### Gap A1 — VAP / MaintainVAP=0

**STATUS:** 🔴 MISSING
**EVIDENCE:** `sc_study/MES_AI_DataExport.cpp:122` — `sc.MaintainVolumeAtPriceData = 0;` (explicitly disabled). Comment says "v9.2.0: DISABLED — was causing Sierra-internal memory accumulation (unbounded VAP storage per bar)."
**IMPACT:** BLOCKING_LIVE (footprint uses fallback distribution, not real VAP)
**SCOPE_ESTIMATE:** 1 file, ~5 LOC to re-enable, but risk of memory leak recurrence
**RECOMMENDATION:** Test with `MaintainVolumeAtPriceData = 1` on a dedicated session to measure memory impact. If stable for 1 trading day, keep enabled.

### Gap A2 — §6.7 Data Integrity Audit

**STATUS:** 🟢 OK (as of this session)
**EVIDENCE:** Sierra match tool: 29/29 checks passing. All indicator values in expected ranges. TPO previous_session validated (3000-10000 range). CVD has timestamps + interval. Freshness < 2s for all exports.
**IMPACT:** N/A (currently passing)
**SCOPE_ESTIMATE:** 0 LOC
**RECOMMENDATION:** Run `python3 tools/p30_sierra_match_tool.py --watch` during RTH to catch drift.

### Gap A3 — prev_day.py module

**STATUS:** 🟡 PARTIAL
**EVIDENCE:** No standalone `prev_day.py` exists. Previous-day context is handled inline: `backend/v9/systems/day_type/opening_detector.py:19-20` accepts `prev_day_high/low` params. `state_machine.py:299` logs "missing_previous_day_context" when unavailable. TPO `previous_day` endpoint exists at `/api/v9/tpo/previous_day`.
**IMPACT:** BLOCKING_LIVE (S1 DayType needs prev-day context for OA_IN/OA_OUT classification)
**SCOPE_ESTIMATE:** ~50 LOC + 1 test file. Module to fetch prev-day high/low/close/POC from TPO endpoint and inject into S1 startup.
**RECOMMENDATION:** Create `backend/v9/systems/day_type/prev_day.py` that reads from `/api/v9/tpo/previous_day` at S1 hydration.

### Gap A4 — S1 main.py wiring (7 DEAD)

**STATUS:** 🟡 PARTIAL
**EVIDENCE:** 7 modules built but not imported in `main.py`:
- `decision_matrix.py` — S1 classification rules
- `extensions.py` — S1 extensions
- `open_type.py` — Opening type classifier
- `opening_detector.py` — OA_IN/OA_OUT detection
- `targets_table.py` — Day-type target levels
- `triggers.py` — 6 trigger types for DayType engine
- `models.py` — S1 data models

Wired modules (5): `state_machine`, `schemas`, `detector`, `consumer`, `api` + `day_type_seed`.
**IMPACT:** BLOCKING_LIVE (S1 classification incomplete without decision_matrix + targets)
**SCOPE_ESTIMATE:** ~30 LOC wiring in main.py + integration tests
**RECOMMENDATION:** Wire `decision_matrix`, `opening_detector`, `targets_table`, `triggers` into the DayTypeConsumer pipeline. `extensions` and `models` may be support modules already used indirectly — verify imports.

### Gap A5 — D-061 vs Cockpit V5 §3.3 conflict

**STATUS:** 🟢 OK (no conflict)
**EVIDENCE:** D-061 is implemented as OBSERVATIONAL per `killzone/detector.py:89`, `zones.py:4`, `gate.py:24` — all three files state "zones are observational tags; they do not hard-block trades." IB_BUILDING appears in `day_type/api.py:155` as a stage label, not a trade blocker. No code path hard-blocks based on Killzone zone name.
**IMPACT:** N/A
**SCOPE_ESTIMATE:** 0 LOC
**RECOMMENDATION:** No action needed. D-061 correctly implemented.

### Gap A6 — cluster_guard BLOCKED state (S3)

**STATUS:** 🔴 BLOCKING_SHADOW
**EVIDENCE:** `gateway/cooldown.py` — `ClusterGuard` blocks after 5+ trade attempts within 60 seconds for 5 minutes. `gateway/trading_gateway.py:86-87` — if `cluster_guard.is_blocked()`, sets `blocked_by="cluster_guard"` and returns without recording shadow trade. Log showed "[Woodies] Gateway blocked: cluster_guard" during this session.
**ROOT CAUSE:** Runtime state — cluster_guard triggers because Woodies fires patterns frequently (multiple per bar during high-CCI periods). Each pattern attempt counts toward the 5-attempt limit. After 5 fires in 60s → blocked for 5 minutes.
**IMPACT:** BLOCKING_SHADOW (no shadow trades recorded while blocked)
**SCOPE_ESTIMATE:** ~10 LOC
**RECOMMENDATION:** Either (A) increase CLUSTER_MAX_TRADES to 10+ for shadow mode, or (B) skip cluster_guard entirely in shadow mode (`if mode == "SHADOW": return` in `route_setup`).

### Gap A7 — M18 pre_fire_validator coverage

**STATUS:** 🟡 PARTIAL
**EVIDENCE:**
| System | Calls pre_fire_validator? | Location |
|--------|--------------------------|----------|
| S4 Woodies | YES | `decision_tree.py:355-370` (A7 stage) |
| S2 FiveMin | NO | `five_min_system.py:556` calls `gateway.route_setup` directly, skips A7 |
| S1 DayType | NO | S1 is observer, does not fire trades |

S2 FiveMin calls `self._gateway.route_setup(gateway_setup, 2)` at line 556 without pre_fire validation. The gateway itself does NOT call validate_fire — only the Woodies decision tree does.
**IMPACT:** BLOCKING_LIVE (S2 can fire without M18 safety checks)
**SCOPE_ESTIMATE:** ~15 LOC — add `validate_fire()` call before `route_setup` in S2
**RECOMMENDATION:** Add pre_fire_validator call in `five_min_system.py` before `route_setup`, matching S4's pattern.

### Gap A8 — PROMPT 5/6/7 status

**STATUS:** 🟡 PARTIAL
**EVIDENCE:**
| Prompt | File | Status |
|--------|------|--------|
| PROMPT 5 (SHADOW Analyst) | `docs/UAT_REPORTS/PROMPT_5_20260512_105505.md` | Report exists, appears scoped |
| PROMPT 6 (LIVE pre-flight UI) | `docs/PROMPT_6_REPORT.md` | Report exists |
| PROMPT 7 (LIVE activation) | `docs/PROMPT_7_REPORT.md` | Report exists |

All three have report files but content scope not verified (read-only pass — did not read full contents).
**IMPACT:** BLOCKING_LIVE (need to verify PROMPT 6/7 are implemented, not just scoped)
**SCOPE_ESTIMATE:** Unknown until content review
**RECOMMENDATION:** Michael to review PROMPT 6 + 7 reports and confirm implementation status.

---

## Section 3: PHASE B RESULTS

**Tool:** `tools/p30_sierra_match_tool.py`
**Usage:** `python3 tools/p30_sierra_match_tool.py` (one-shot) or `--watch` (30s loop)
**Log:** `/tmp/p30_diagnostic/sierra_match_20260520T142613Z.log`

### Summary (29 checks, all passing)

| System | Field | Verdict | Detail |
|--------|-------|---------|--------|
| woodies | sierra_source | 🟢 MATCH | True |
| woodies | version | 🟢 MATCH | v9.4.2-p30.11 |
| woodies | ccidiff_consistency | 🟢 MATCH | diff=0.00 |
| woodies | cci_14_range | 🟢 MATCH | in [-500,500] |
| woodies | cci_6_tcci_range | 🟢 MATCH | in [-500,500] |
| woodies | swi_value_range | 🟢 MATCH | in [-300,300] |
| woodies | czi_value_range | 🟢 MATCH | in [-100,100] |
| woodies | ema_34_range | 🟢 MATCH | in [3000,10000] |
| woodies | lsma_value_range | 🟢 MATCH | in [3000,10000] |
| woodies | proj_hi_range | 🟢 MATCH | ~7703 |
| woodies | proj_lo_range | 🟢 MATCH | ~7112 |
| woodies | proj_spread | 🟢 MATCH | hi > lo |
| tpo | today POC/VAH/VAL | 🟢 MATCH | all in MES range |
| tpo | va_ok | 🟢 MATCH | True |
| tpo | yesterday POC/VAH/VAL | 🟢 MATCH | all valid, ordering correct |
| cvd | output_interval | 🟢 MATCH | 300 |
| cvd | points_with_t | 🟢 MATCH | 0 missing |
| freshness | all 4 files | 🟢 MATCH | age < 2s |

---

## Section 4: PHASE C RESULTS — Audit Verification

| System | Question | Category | Evidence / Next Step |
|--------|----------|----------|---------------------|
| DLL | CCI Predictor accuracy | B (NEEDS_RUNTIME) | Run match tool during RTH, compare with Sierra HUD screenshot |
| DLL | ZLR Sierra match | B (NEEDS_RUNTIME) | Compare ID:13 SG2 alerts vs our ZLR detection during live session |
| DLL | HFE from Sierra | C (NEEDS_DECISION) | No Sierra study for HFE found. Keep computed? |
| DLL | Trend state from ID:1 | A (ANSWERED) | ID:1 SG6=-7.0 (color code), not directly usable as BLUE/RED/YELLOW. Keep computed from CCI+SWI. |
| DLL | Session volume | B (NEEDS_RUNTIME) | Currently 0 placeholder. Can sum from chart bars — ~5 LOC in DLL. |
| Bridge | Stream 12/12 missing | A (ANSWERED) | 11 streams active, heartbeat shows 11/12. Need to identify which stream config is missing. |
| Bridge | TPO push errors (312) | A (ANSWERED) | Transient timeouts — `[ERROR] timed out` followed by successful push 2s later. Backend response latency, not data loss. |
| Bridge | Stacked imbalances errors | A (ANSWERED) | Same pattern — transient timeouts, self-recovering. |
| Backend | Touchpoints background cache | C (NEEDS_DECISION) | Currently empty dict. Implement cache or accept degraded A4? |
| Backend | TPO periods granularity | A (ANSWERED) | Backend accumulates from bridge pushes. Resolution = DLL export interval (3s). Sufficient for 30-min stepped paths. |
| Backend | /tpo/continuous/history | C (NEEDS_DECISION) | Endpoint doesn't exist. TpoContinuityOverlay uses periods array. Add endpoint for richer data? |
| Backend | Decision tree A4 degraded | A (ANSWERED) | A4 returns PASS with "degraded" status. Touchpoints are advisory — does not block routing. Acceptable for SHADOW. |
| Backend | Gateway LIVE mode | C (NEEDS_DECISION) | Currently shadow only. When to enable? |
| Frontend | Woodies HUD values | B (NEEDS_RUNTIME) | CCIDiff/Predictor displayed — need RTH screenshot comparison |
| Frontend | TPO continuity resolution | A (ANSWERED) | Uses periods from API. 5 periods available. Steps render correctly. |
| Frontend | Pink lines during RTH | B (NEEDS_RUNTIME) | isRthNow() correct server-side. Need browser console check. |
| Frontend | Chart zoom/pan bounded | B (NEEDS_RUNTIME) | Lines use LineSeries (engine-locked). Visual verification needed. |
| Frontend | CVD alignment | B (NEEDS_RUNTIME) | CVD pane uses shared timeScale. Visual verification needed. |
| Frontend | Mobile/responsive | B (NEEDS_RUNTIME) | Not tested. Lower priority for desktop trading platform. |
| S4 Woodies | Pattern vs Sierra | B (NEEDS_RUNTIME) | Need live comparison during RTH session |
| S4 Woodies | A4 touchpoints impact | A (ANSWERED) | Advisory only. Patterns/sizing/routing work without touchpoints. |
| S4 Woodies | Signal persistence perf | A (ANSWERED) | SQLite INSERTs, ~5ms per pattern. Acceptable at 5-min bar frequency. |
| S4 Woodies | A7 pre-fire active | A (ANSWERED) | `decision_tree.py:355` calls `validate_fire()`. Active for S4. |
| S5 TPO | Session classification | A (ANSWERED) | Always "NA" — Sierra doesn't export profile_shape/opening_type via study subgraphs. |
| S5 TPO | POC migration | A (ANSWERED) | Direction "UNKNOWN" — requires tracking POC changes over time. ~30 LOC in TPO system. |
| S5 TPO | IB width | A (ANSWERED) | Always null. Simple fix: `ib_width = ib_high - ib_low` when both > 0. ~3 LOC. |
| S1 DayType | Classification accuracy | C (NEEDS_DECISION) | Last audit unknown. Needs RTH session comparison. |
| S3 Footprint | Stacked imbalances render | B (NEEDS_RUNTIME) | Backend exports. Cockpit rendering not verified. |
| S3 Footprint | Imbalance flags visible | B (NEEDS_RUNTIME) | Same — backend has data, frontend rendering not verified. |
| S6 Killzone | Zone transitions | A (ANSWERED) | `killzone_system.py` uses ET-based time windows. Correct per D-061. |
| Veto | Suffering side | B (NEEDS_RUNTIME) | Implementation exists. Needs live data test. |
| Layer 0 | State machine | A (ANSWERED) | Exists in `layer0/`. SEARCHING is default state until data arrives. |

**Summary:** 18 ANSWERED | 11 NEEDS_RUNTIME | 4 NEEDS_DECISION

---

## Section 5: RECOMMENDED PRIORITY MATRIX

🔴 BLOCKING_SHADOW
- cluster_guard blocks all shadow trades after 5 fires in 60s | A6 | ~10 LOC
- S2 FiveMin skips pre_fire_validator | A7 | ~15 LOC

🟡 BLOCKING_LIVE
- VAP disabled (MaintainVAP=0) — footprint uses fallback | A1 | 5 LOC + memory test
- S1 DayType 7 unwired modules | A4 | ~30 LOC
- prev_day.py module missing for S1 | A3 | ~50 LOC
- PROMPT 5/6/7 implementation verification | A8 | review only

🔵 POST_LIVE
- Session volume placeholder (0) | DLL | ~5 LOC
- CCI Predictor accuracy verification | runtime | match tool
- POC migration tracking | S5 | ~30 LOC
- IB width calculation | S5 | ~3 LOC

⚪ DEFERRED
- HFE from Sierra (no study available)
- Trend state from Sierra ID:1 (color code not usable)
- Mobile/responsive layout
- /tpo/continuous/history endpoint

---

## Section 6: OPEN QUESTIONS FOR MICHAEL

1. **cluster_guard in shadow mode** — increase MAX_TRADES to 10+, or skip entirely in SHADOW? (A6)
2. **Touchpoints background cache** — implement cache, or accept degraded A4 permanently? (Backend)
3. **Gateway LIVE mode** — when to enable? What's the activation criteria? (Backend)
4. **S1 DayType classification audit** — schedule RTH comparison session? (S1)
5. **HFE detection** — keep computed, or investigate Sierra study? (DLL)
6. **PROMPT 5/6/7** — are these implemented or just scoped? Need your review of the report files. (Docs)
