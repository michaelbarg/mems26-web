# System Completion Control Board

**Date:** 2026-05-16  
**Authority:** Master Index V2  
**Purpose:** Score whether each system produces reliable information  
**Scope:** System correctness only — NOT SHADOW/DEMO/LIVE activation

---

## Summary

| System | Readiness | Tests | Key Issue |
|--------|-----------|-------|-----------|
| S1 Day Type | **PARTIAL** | 37/37 | V1 and V9 classifiers disagree; pd_* not wired |
| S2 Five-Min | **READY** | 65/65 | — |
| S3 Footprint | **READY** | 22/22 | — |
| S4 Woodies | **PARTIAL** | 32/32 | decision_tree never returns ready_to_route=true (A4 touch-points PENDING) |
| S5 TPO | **READY** | 9/9 | — |
| S6 Killzone | **READY** | 24/24 | — |

---

## S1 Day Type (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | Subscribes 5min via BarRouter; IB tracked from TPO; /current returns classified state |
| B Detection | YELLOW | V1 classifier + V9 state machine both active — **they disagree** (V1=Nontrend, V9=Variation on same session) |
| C Decision | GREEN | Pre-IB gate works (PENDING until 10:30 ET); decision_matrix covers all OpeningType×IBWidth |
| D Output | GREEN | V9 endpoint returns 13-field DayTypeClassification with reasoning_notes |
| E Tests | GREEN | 37/37 pass (classifier + targets + e2e + state_machine) |

**Status: PARTIAL**

**Missing/Issues:**
- V1 (`/day_type/current`) and V9 (`/day_type/v9/current`) produce different classifications
- `pd_high`/`pd_low`/`pd_close` not populated from bridge (A1 pre-open context incomplete)
- V1 path shows `ib_range=300` which is unrealistic for MES (suggests stale/wrong data source)

**Files:**
- `backend/v9/systems/day_type/state_machine.py` (825 lines)
- `backend/v9/systems/day_type/decision_matrix.py` (134 lines)
- `backend/v9/systems/day_type/detector.py` (277 lines)
- `backend/v9/systems/day_type/targets_table.py` (128 lines)

**Next prompt:** Reconcile V1/V9 classifiers — single source of truth. Wire pd_* from bridge.

---

## S2 Five-Min T1 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | Subscribes 5min + tick_reversal_15; buffer populated during RTH |
| B Detection | GREEN | multi_bar_pattern (Reactive/Initiative), belly, COT/AMT, POC_VOL |
| C Decision | GREEN | pre_fire_validator runs; quality tier from TPO; mode gate (WEEKEND blocks) |
| D Output | GREEN | /fire returns pattern+confluence+mode+reasoning_notes; auto-routes to gateway |
| E Tests | GREEN | 65/65 pass |

**Status: READY**

**Files:**
- `backend/v9/systems/five_min/five_min_system.py` (574 lines)
- `backend/v9/systems/five_min/setup_emitter.py` (92 lines — pre_fire + gateway compose)
- `backend/v9/systems/five_min/multi_bar_pattern.py`
- `backend/v9/systems/five_min/cot_amt.py`
- `backend/v9/systems/five_min/belly.py`

**Proof:** `python3 -m pytest backend/v9/systems/five_min/ -q` → 65 passed

---

## S3 Footprint/Reversal T3 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | Subscribes tick_reversal_15 + tick_reversal_12; 166+ bars processed today |
| B Detection | GREEN | 4 detectors: absorption, stacked_imbalance, sweep_return, exhaustion |
| C Decision | GREEN | calculate_size (delta+dominance+initiative alignment); _fire persists |
| D Output | GREEN | /fire returns signal+direction+strength+evidence; /journal for history |
| E Tests | GREEN | 22/22 compliance pass |

**Status: READY**

**Files:**
- `backend/v9/systems/footprint/footprint_system.py` (419 lines)
- `backend/v9/systems/footprint/signals/absorption.py` (97 lines)
- `backend/v9/systems/footprint/signals/stacked_imbalance.py` (121 lines)
- `backend/v9/systems/footprint/signals/sweep_return.py` (91 lines)
- `backend/v9/systems/footprint/signals/exhaustion.py` (105 lines)

**Proof:** `python3 -m pytest tests/v9/compliance/test_tick_reversal_compliance.py -q` → 22 passed

---

## S4 Woodies T2 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | D-074 migrated to 5-min; subscribes woodies_5min; buffer=9 bars |
| B Detection | GREEN | 9 patterns via pattern_engine; calculate_size per V2 PART 6 tier map |
| C Decision | YELLOW | decision_tree evaluates A1-A7 stages but **never reaches ready_to_route=true** (A4 touch-points PENDING, causes early SKIP) |
| D Output | GREEN | /fire returns decision_tree stages + classification + ready_to_route |
| E Tests | GREEN | 32/32 pass (20 compliance + 5 decision_tree + 7 system) |

**Status: PARTIAL**

**Missing/Issues:**
- `ready_to_route` is always `false` because A4 (Touch-Points) stage returns PENDING
- A4 queries 6 external endpoints; returns SKIP when they're unavailable
- Until A4 is satisfied (or bypassed for SHADOW), S4 cannot auto-route to gateway
- Patterns ARE detected and calculate_size DOES run — but the decision_tree gate blocks routing

**Files:**
- `backend/v9/systems/woodies/woodies_system.py` (427 lines)
- `backend/v9/systems/woodies/decision_tree.py` (257 lines)
- `backend/v9/systems/woodies/pattern_engine.py` (59 lines)
- `backend/v9/systems/woodies/patterns/*.py` (9 detectors, ~800 lines total)

**Next prompt:** Either (A) make A4 PENDING → PASS in SHADOW mode, or (B) bypass decision_tree gate for initial shadow accumulation, or (C) implement the 6 touch-point HTTP queries.

---

## S5 TPO (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | Running; poc=7478.25, vah=7480.25, val=7478.25, session=GLOBEX |
| B Detection | GREEN | POC migration (direction=STUCK), tails, single_print, UFL/UFH |
| C Decision | N/A | OBSERVING — provides context, no firing |
| D Output | GREEN | /tpo/current returns all fields + poc_migration + ib_locked status |
| E Tests | GREEN | 9/9 pass |

**Status: READY**

**Files:**
- `backend/v9/systems/tpo/tpo_system.py` (554 lines)

**Proof:** `python3 -m pytest tests/v9/compliance/v1_generated/test_system5_v1.py -q` → 9 passed

---

## S6 Killzone (OBSERVING + GATE)

| Dim | Score | Evidence |
|-----|-------|----------|
| A Data | GREEN | Time-based; zone=WEEKEND detected correctly |
| B Detection | GREEN | 8 zones defined with edge_class; zone_playbook per-zone preferences |
| C Decision | GREEN | Gate blocks firing when CLOSED/WEEKEND; quality_modifier per zone |
| D Output | GREEN | /killzone/current returns zone+edge+remaining+next |
| E Tests | GREEN | 24/24 pass (11 playbook + 13 compliance) |

**Status: READY**

**Files:**
- `backend/v9/systems/killzone/killzone_system.py` (88 lines)
- `backend/v9/systems/killzone/definitions.py` (99 lines)
- `backend/v9/systems/killzone/zone_playbook.py` (140 lines)

**Proof:** `python3 -m pytest tests/v9/compliance/v1_generated/test_system6_v1.py tests/atomic/test_killzone_playbook.py -q` → 24 passed

---

## Cross-System Infrastructure

| Component | Status | Evidence |
|-----------|--------|----------|
| pre_fire_validator | GREEN | 63 lines, consumed by S2 setup_emitter |
| TradingGateway | GREEN | shadow/demo/live slots; route_setup wired from S2+S4 (Prompt 14) |
| BarLevelDetector | GREEN | Closes trades on T1/T2/T3 hit; time-stop per Day Type |
| L0 Chop Score | GREEN | /chop_score/current returns 4-state + 6 indicators |
| Layer 3 handoff | GREEN | cluster + empty_zone + entry_executor |
| Bridge | GREEN | Running, 11 streams configured, pushing bars |

---

## Aggregate Readiness

| Category | Count |
|----------|-------|
| READY | **4** (S2, S3, S5, S6) |
| PARTIAL | **2** (S1, S4) |
| NOT READY | **0** |

---

## Remaining Issues (do NOT block initial SHADOW)

| # | System | Issue | Severity | Blocks SHADOW? |
|---|--------|-------|----------|----------------|
| 1 | S1 | V1/V9 classifier disagreement | MEDIUM | NO — V9 is canonical, V1 is legacy |
| 2 | S1 | pd_* not wired | LOW | NO — affects pre-open context only |
| 3 | S4 | decision_tree A4 blocks ready_to_route | HIGH | **YES for S4 auto-routing** |
| 4 | S4 | CCI=0 (no DLL data flowing on weekend) | LOW | NO — will resolve Mon 9:30 |

**Issue #3 is the only functional gap:** S4 Woodies detects patterns but cannot auto-route because the decision_tree requires A4 touch-points to pass. S2 and S3 fire correctly.

---

## Recommended Next Prompts

```
Prompt 18: S4 decision_tree A4 — bypass PENDING in SHADOW mode
           OR implement the 6 HTTP touch-point queries
           (unblocks S4 auto-routing → completes 3/3 firing systems)

Prompt 19: S1 V1/V9 reconciliation — deprecate V1 classifier
           (single source of truth for downstream consumers)

Prompt 20: pd_* wiring from Bridge → S1
           (completes A1 pre-open context for full classification accuracy)
```

---

*Generated: Prompt 17 — System Completion Control Board. No code changes. No push.*
