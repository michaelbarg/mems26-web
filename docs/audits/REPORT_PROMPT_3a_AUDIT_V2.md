# Day Type System — Spec vs Code Audit (Prompt 3a V2)

Date: 2026-05-15
Specs: Day Type Tree V2 + Constitution V3 Layer 2 + SPEC_System_A_DayType_V1
Code: backend/v9/systems/day_type/ (1,742 lines across 9 files)

---

## BLOCK 1: File Structure

| File | Lines | Purpose |
|---|---|---|
| api.py | 356 | 5 endpoints + V1 classifier + state machine bridge |
| state_machine.py | 577 | 13-stage A1→B6 + Decision Matrix + Playbook Templates |
| detector.py | 272 | classify_ib_width + detect_opening_type + detect_behavior |
| schemas.py | 201 | DayType enum (6 types) + OpeningType + IBWidth + Stage + configs |
| open_type.py | 123 | Opening type classification (separate module) |
| targets_table.py | 128 | Per-day-type T1/T2/T3 + time stops (V3 Layer 4) |
| models.py | 24 | SQLAlchemy V9DayTypeState model |
| hydration.py | 52 | Hydration helper |
| __init__.py | 9 | Exports |

---

## BLOCK 2: API Surface

| Endpoint | SPEC says | CODE has | GAP |
|---|---|---|---|
| GET /current | Day type + confidence + stage + IB data | ✅ Returns day_type, confidence, stage, reason, classified flag | 🟡 Two classifiers: V1 simple rules (api.py) + state machine (state_machine.py). V1 fires from TPO data, state machine from process_bar. Can conflict. |
| GET /state | Full state machine state | ✅ Returns DayTypeStateResponse | ✅ COMPLIANT |
| GET /history | Historical classifications | ✅ From v9_day_type_history | ✅ COMPLIANT |
| POST /process | Bar-by-bar processing | ✅ Feeds state machine | ✅ COMPLIANT |
| GET /stats | Distribution over N days | ✅ Aggregates from DB | ✅ COMPLIANT |

---

## BLOCK 3: IB Calculator

| Item | SPEC says (Day Type Tree V2) | CODE has | GAP |
|---|---|---|---|
| IB Width thresholds | < 15 pts = NARROW, 15-25 pts = MEDIUM, > 25 pts = WIDE | ✅ `classify_ib_width(narrow_max=15.0, medium_max=25.0)` in detector.py:14-28 | ✅ FULLY COMPLIANT |
| IB Lock time | 10:30:00 ET | ✅ State machine stage A4 triggers on `session_min >= ib_period_min` | ✅ COMPLIANT (config-driven) |
| IB tracking | Continuous H/L during 09:30-10:30 | ✅ `_update_ib()` in tpo_system.py tracks ib_high/ib_low | ✅ COMPLIANT |

---

## BLOCK 4: Opening Type Detector

| Item | SPEC says (5 sub-types per V2) | CODE has | GAP |
|---|---|---|---|
| OPEN_DRIVE (OD) | One-way move, 95% cert | ✅ detector.py:75 — directional_ratio check | 🟡 Confidence 0.9 (not 0.95) |
| OPEN_TEST_DRIVE (OTD) | Test + drive opposite, 85% cert | ✅ detector.py:90 — pullback + continuation | 🟡 Confidence 0.7 (not 0.85) |
| OPEN_REJECTION_REVERSE (ORR) | Rejection + reversal, 50% cert | ✅ detector.py:101 — reversal detection | 🟡 Confidence 0.65 (not 0.50) |
| OPEN_AUCTION_IN (OA in PD VA) | Rotational, 40% cert | ✅ detector.py:108 — no clear direction in VA | ✅ Confidence 0.4 |
| OPEN_AUCTION_OUT (OA out PD VA) | Gap > 5pt, very high conviction | ✅ detector.py:106 — outside VA detection | 🟡 Confidence 0.5 (spec says "very high") |
| INDETERMINATE | Wait until 10:30 | ✅ Falls through to OPEN_AUCTION_IN as default | 🟡 No explicit INDETERMINATE state in enum |
| Lock @ 09:40 (10 min observation) | V2 spec says lock opening type at 09:40 | ❌ No explicit 09:40 lock — detector runs on each bar | ❌ MISSING — opening type should lock after 10 min |

---

## BLOCK 5: Decision Matrix

| Opening × IB Width | SPEC V2 (highest prob) | CODE has | GAP |
|---|---|---|---|
| OD × NARROW | Trend_N 60% | ✅ Trend_Normal | ✅ |
| OD × MEDIUM | Trend_N 70% | ✅ Trend_Normal | ✅ |
| OD × WIDE | Trend_N 50% | ✅ Trend_Normal | ✅ |
| OTD × NARROW | Trend_DD 40% | ✅ Trend_DD | ✅ |
| OTD × MEDIUM | Trend_N 50% | ✅ Trend_Normal | ✅ |
| OTD × WIDE | Variation 50% | ✅ Variation | ✅ |
| ORR × NARROW | Variation 40% | ✅ Variation | ✅ |
| ORR × MEDIUM | Variation 50% | ✅ Variation | ✅ |
| ORR × WIDE | Normal 50% | ✅ Normal | ✅ |
| OA_IN × NARROW | Nontrend 50% | ✅ Nontrend | ✅ |
| OA_IN × MEDIUM | Normal 40% | ✅ Normal | ✅ |
| OA_IN × WIDE | Normal 50% | ✅ Normal | ✅ |
| OA_OUT × NARROW | Trend_DD 50% | ✅ Trend_DD | ✅ |
| OA_OUT × MEDIUM | Trend_DD 40% | ✅ Trend_DD | ✅ |
| OA_OUT × WIDE | Trend_N 40% | ✅ Trend_Normal | ✅ |
| **Probability data** | Full prob distribution per cell | ❌ Only highest-prob stored | 🟡 Matrix uses argmax only, doesn't store full distribution |

---

## BLOCK 6: Day Type Enum + Tests + Targets

| Item | SPEC says | CODE has | GAP |
|---|---|---|---|
| 6 Day Types | Trend_Normal, Trend_DD, Variation, Normal, Neutral, Nontrend | ✅ schemas.py:11-16 (all 6 + UNKNOWN) | ✅ COMPLIANT |
| Targets per Day Type | V3 Layer 4 table | ✅ targets_table.py with exact R-multiples + time stops | ✅ COMPLIANT |
| Tests | Coverage for all paths | ✅ 5 test files (compliance, atomic, L4 verify) | ✅ COMPLIANT |
| Re-eval triggers (Q14) | V2 says re-evaluate on significant events | ❌ No re-evaluation logic in state machine | ❌ MISSING |
| Pre-open context (Q3-Q4) | Load PD POC/VAH/VAL, ON activity bias | ❌ No pre-open context loading | ❌ MISSING |
| V1 vs State Machine conflict | Should be single classifier | 🔴 Two parallel classifiers (V1 in api.py + state machine) | 🔴 CONFLICT |

---

## SUMMARY TABLE

| Component | Status | Notes |
|---|---|---|
| IB Width thresholds (<15/15-25/>25) | ✅ FULLY COMPLIANT | Exact match with V2 spec |
| 6 Day Type enum | ✅ FULLY COMPLIANT | All 6 + UNKNOWN |
| Decision Matrix (15 cells) | ✅ FULLY COMPLIANT | All 15 cells match V2 highest-prob |
| Targets per Day Type | ✅ FULLY COMPLIANT | R-multiples + time stops per V3 L4 |
| 5 Opening Types | 🟡 PARTIAL | All 5 detected but confidence values don't match V2, no INDETERMINATE |
| Opening Type 09:40 lock | ❌ MISSING | No explicit lock — re-classifies on every bar |
| Pre-open context (Q3-Q4) | ❌ MISSING | No PD POC/VAH/VAL, no ON bias loading |
| Re-eval triggers (Q14) | ❌ MISSING | No re-evaluation after significant events |
| Decision Matrix probability distribution | 🟡 PARTIAL | Only argmax stored, not full distribution |
| Dual classifier conflict | 🔴 CONFLICT | V1 simple rules (api.py) + state machine (state_machine.py) can give different answers |
| Tests | ✅ FULLY COMPLIANT | 5 test files covering compliance + atomic + L4 |
| DB schema | ✅ FULLY COMPLIANT | v9_day_type_history with all required fields |
