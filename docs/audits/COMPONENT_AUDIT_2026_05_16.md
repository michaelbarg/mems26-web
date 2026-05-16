# MEMS26 V9 Component Audit V2 — 16 May 2026

## Summary

- Backend .py files: 286
- Frontend .tsx files: 84
- API endpoints: 90
- Tests: 1371 passed, 39 failed (27 intentional spec-drift + 6 woodies patterns + 6 infra), 3 skipped
- Sierra DLL: 3405 LOC total (5 files), 11 JSON exports, MaintainVAP=OFF

---

## S1 — Day Type (Observer) — 15 files, 2152 LOC

**Tests:** 9 files, 58 tests passing

| Spec Item | Status | Evidence |
|---|---|---|
| 6 Day Types enum | YES | schemas.py:10-17 (Trend_Normal, Trend_DD, Variation, Normal, Neutral, Nontrend + UNKNOWN) |
| Market Clock service | YES | services/market_clock.py (now_et, is_rth_open, 10 holidays 2026, 2 half-days) |
| Previous Day Loader | PARTIAL | BarInput has pd_high/pd_low/pd_close fields (schemas.py:103-105), state_machine uses them (line 283-293), but main.py never populates them |
| Open Type (5 sub-types) | YES | opening_detector.py: OD/OTD/ORR/OA_IN/OA_OUT + open_type.py (4 types) |
| IB Width thresholds | YES | schemas.py:85-86 (narrow_max=15, medium_max=25). Static, NOT 33/67 percentile rolling. |
| IB Width history table | YES | db/models/day_type_history.py has ib_width + ib_width_class columns |
| Distribution shape detection | NO | No distribution_shape/single_dist/double_dist/P/b-shape found |
| State machine V9 | YES | state_machine.py:229 process_bar, :656 on_trigger, :772 to_classification |
| V1 classifier fallback (D-071) | YES | api.py:115 _classify_v1_from_tpo |
| Dead wiring (5 V9 methods) | DEAD | update_cvd_state, update_max_tpo_row_width, on_trigger: defined but 0 production callers |
| /clock/now | YES | clock_routes.py:8 |
| /tpo/previous_day | YES | tpo_routes.py:57 |
| /open_type/current | YES | open_type_routes.py:13 |
| /day_type/current (V1) | YES | api.py:217 |
| /day_type/v9/current (V9) | YES | day_type_v9_routes.py:23 |
| DayTypeClassification | YES | 13-field frozen dataclass in state_machine.py |
| DayTypeConsumer UPSERT | YES | consumer.py, wired in main.py |
| Event schema YAML | YES | event_bus/schemas/day_type_classification.yaml |

**Gaps:**
- P0: Previous Day data never populated in main.py. 5 dead V9 methods not wired.
- P1: IB Width static thresholds (should be 33/67 percentile rolling). Distribution shape detection missing.
- P2: V1 fallback removal (both old + new endpoints coexist).

---

## S2 — 5-Min T1 (Firing) — 2 files, 416 LOC

**Tests:** 3 files found (test_five_min_system.py, test_five_min_sizing.py, test_five_min_patterns.py)

| Spec Item | Status | Evidence |
|---|---|---|
| Reactive LONG/SHORT | YES | five_min_system.py:265-317 _detect_reactive() with COT > AMT check |
| Initiative LONG/SHORT | YES | five_min_system.py:319-373 _detect_initiative() with COT < AMT check |
| COT integration | YES | five_min_system.py:246 _get_cot_from_footprint() |
| AMT integration | YES | five_min_system.py:255 _get_amt_from_footprint() (90-min avg, 1.2x/0.8x thresholds) |
| Per-system sizing | PARTIAL | Sizing logic embedded, not H=3/M=2/L=skip explicit |
| Fire output schema | YES | DB model five_min_setups.py: direction, entry, stop, t1, t2, time_stop, confidence |
| pre_fire_validator | NO | Module doesn't exist (MISSING service) |
| V9 enhancement layer | NO | No triggers/zohar equivalent |
| Bar close trigger | YES | Subscribed to cumulative_delta via wrappers.py:115 |
| Endpoints (4) | YES | /current, /setups, /fire, /stats |

**Gaps:**
- P0: pre_fire_validator missing (blocks validated firing).
- P1: Per-system sizing not H/M/L explicit. V9 enhancement layer.
- P2: reasoning_notes >= 4 enforcement.

---

## S3 — Footprint T3 (Standalone Observer) — 8 files, 823 LOC

**Tests:** 1 file (test_footprint_system.py)

| Spec Item | Status | Evidence |
|---|---|---|
| 7-stage pipeline (A-G) | NO | Signal-based architecture, not staged pipeline |
| 4 signal types | YES | signals/absorption.py, stacked_imbalance.py, sweep_return.py, exhaustion.py |
| 3 classifications | YES | footprint_system.py: NO_SETUP (line 44/248), TACTICAL (line 247), STRATEGIC (line 245) |
| tick_reversal inputs | YES | wrappers.py:184 subscribes tick_reversal_15/12 + footprint |
| Sierra JSON inputs | YES | footprint.json + stacked_imbalances.json + imbalance_flags.json |
| pre_fire_validator | NO | MISSING service |
| Standalone per D-072 | YES | wrappers.py returns None (observer) |
| Endpoints (3) | YES | /current, /fire, /journal |

**Gaps:**
- P0: None (observer, data flows correctly).
- P1: pre_fire_validator. 7-stage pipeline (spec vs signal-based implementation divergence).
- P2: 5 named patterns per spec (currently 4 signal types).

---

## S4 — Woodies CCI T2 (Firing) — 18 files, 1737 LOC

**Tests:** 3 files (6 real failures in patterns, 3 intentional v1 drift)

| Spec Item | Status | Evidence |
|---|---|---|
| 11 CCI Studies | YES (all 11) | cci_calc.py: cci_14, cci_6/tcci, ema_34, lsma, lsma_above, swi, czi, trend_state, predictor, zlr_detected, zlr_direction |
| 8 Pattern files | YES (all 8) | patterns/: zlr.py, tlb.py, tt.py, gb100.py, vegas.py, ghost.py, famir.py, htlb.py |
| HFE pattern (#9) | NO | Not found |
| 21 Decision Tree stages (A1-A7, B1-B14) | NO | Only 4 core stages: STUDY_COMPUTE, PATTERN_DETECT, CLASSIFY, TREND_STATE |
| Priority Hierarchy Dispatcher | NO | Not implemented |
| 18 Terminal States | NO | Not enumerated |
| YAML config loader | NO | Manifest exists but not loaded at runtime |
| woodies_30min Sierra input | YES | v9_woodies_export.h (345 LOC), bridge stream, JSON export |
| Sierra studies wire-up | YES | 11 studies computed in DLL |
| Endpoints (3) | YES | /current, /signals, /patterns |
| ZLR test failures | 6 real | test_woodies_patterns.py (confidence + detection) |

**Gaps:**
- P0: 21-stage Decision Tree (A1-A7, B1-B14) not implemented. Priority Hierarchy Dispatcher missing.
- P1: HFE pattern. 18 Terminal States. YAML config. ZLR test fixes.
- P2: Full Woodies CCI Spec V1 compliance.

---

## S5 — TPO (Observer) — 8 files, 1154 LOC

**Tests:** 2 files + 1 atomic (test_tpo_ufl_ufh.py)

| Spec Item | Status | Evidence |
|---|---|---|
| POC_TPO | YES | levels.py: compute_poc, schemas.py:127 |
| POC_VOL | YES | profile_builder.py:133 |
| VAH / VAL | YES | levels.py:74-89, schemas.py:128-129 |
| Tail Detection | YES | levels.py:145-188 compute_tails, tail_min_letters=2 |
| Single prints | YES | levels.py:134-142 compute_single_prints |
| POC migration tracking | YES | tpo_system.py:230-278 (STUCK/ROTATIONAL/ACCEPTED/FAILED) |
| HVN / LVN | YES | levels.py:104-129, tpo_system.py:193 |
| UFL / UFH | YES | tpo_system.py:292-312 _compute_ufl_ufh, levels.py:191-228 |
| IB extension analysis | YES | Via Day Type extensions.py (cross-system) |
| /tpo/current | YES | tpo_routes.py:8 |
| /tpo/sessions | YES | tpo_routes.py:37 |
| /tpo/previous_day | YES | tpo_routes.py:57 |
| /tpo/journal | YES | tpo_routes.py:16 (bonus endpoint) |

**Gaps:**
- P0: None.
- P1: MIGRATED_UP/MIGRATED_DOWN not explicit enum values (implied via velocity).
- P2: Letters exposed per TPO row.

---

## S6 — Killzone (Observer + Gate) — 9 files, 586 LOC

**Tests:** 2 files + 1 atomic (test_killzone_playbook.py)

| Spec Item | Status | Evidence |
|---|---|---|
| Zone detection (11 zones) | YES | compliance_manifest.yaml:52-62 (PRE_MARKET through AFTER_HOURS, 11 total) |
| D-061 (TRADE ALL THE TIME) | NO | Not explicitly codified |
| News block windows | NO | compliance_manifest.yaml:152-154 "MISSING, deferred to post-demo" |
| Holiday calendar | YES | detector.py:92, api.py:19 |
| Half-day handling | YES | gate.py:17, detector.py:115 (close at 13:00 ET) |
| DST transitions | YES | compliance_manifest.yaml:145-148 |
| /killzone/current | YES | killzone_routes.py:7 |
| Compliance | 24/26 | 3.8% drift (EC4 news, EC5 NTP missing) |

**Gaps:**
- P0: D-061 codification (when trading is allowed).
- P1: News block windows (FOMC/CPI/NFP +/-10min).
- P2: NTP time validation.

---

## Shared Services

| Service | Status | Used By |
|---|---|---|
| market_clock.py | EXISTS | S1 (session_min), open_type, clock_routes |
| pre_fire_validator.py | MISSING | Required by S2, S3, S4 (blocks firing) |
| stream_health/ | EXISTS | Monitoring |
| bar_router.py | EXISTS | All 6 systems |
| event_dispatcher/ | EXISTS | All 6 systems via wrappers |
| historical_replay.py | EXISTS | Startup warm-up |
| clock_routes.py | EXISTS | /api/v9/clock/now |

## Frontend Cockpit V6

| Component | Status |
|---|---|
| ChartV5b | EXISTS |
| ActiveTradeCard | EXISTS |
| SessionTimeStrip | MISSING |
| IBLifecycleOverlay | MISSING |
| RiskWidget | MISSING (LIVE only) |
| EmergencyKill | MISSING (LIVE only) |
| PreFlightModal | MISSING |

## Sierra DLL

| Item | Status |
|---|---|
| MES_AI_DataExport.cpp | 654 LOC |
| MES_AI_DataExport_merged.cpp | 1705 LOC |
| v9_exports.h | 590 LOC |
| v9_types.h | 111 LOC |
| v9_woodies_export.h | 345 LOC |
| MaintainVolumeAtPriceData | OFF (line 98) |
| 11 JSON exports | All present in /v9_export/ |
| Last commit | c2d9429 (2026-05-11) |

---

## Critical Path to SHADOW

| # | P0 Item | System | Est. Commits |
|---|---|---|---|
| 1 | pre_fire_validator.py | Shared (S2/S3/S4) | 2-3 |
| 2 | S1 wire 5 dead V9 methods | S1 | 1-2 |
| 3 | S1 populate pd_high/pd_low in main.py | S1 | 1 |
| 4 | S4 Decision Tree 21 stages (A1-A7, B1-B14) | S4 | 5-8 |
| 5 | S6 D-061 codification | S6 | 1 |
| **Total P0** | | | **10-15 commits** |

## Critical Path to LIVE

| # | P1 Item | System |
|---|---|---|
| 1 | S1 IB Width rolling 33/67 percentiles | S1 |
| 2 | S1 Distribution shape detection | S1 |
| 3 | S2 explicit H/M/L sizing | S2 |
| 4 | S3 7-stage pipeline (spec vs signal divergence) | S3 |
| 5 | S4 HFE pattern + 18 Terminal States + YAML config | S4 |
| 6 | S4 ZLR test fixes (6 failures) | S4 |
| 7 | S5 MIGRATED_UP/DOWN explicit enums | S5 |
| 8 | S6 News block windows (FOMC/CPI/NFP) | S6 |
| 9 | Frontend: SessionTimeStrip + IBLifecycleOverlay | FE |
| 10 | Frontend: RiskWidget + EmergencyKill + PreFlightModal | FE (LIVE) |
