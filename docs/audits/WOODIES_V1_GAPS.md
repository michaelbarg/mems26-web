# Woodies V1 Gaps Report

Date: 2026-05-15
57 items MISSING across 10 categories.

## P0 — Blocks LIVE (3 items)

### GAP-W-001: HFE Pattern (T4 #9)
- **Spec**: Pattern 9 "Hook From Extreme" — REACTIVE classification in A6 depends on it
- **Grep 1**: `grep -rn "HFE" backend/v9/` → 0 results
- **Grep 2**: `grep -rn "hook_from_extreme" backend/v9/` → 0 results
- **Grep 3**: `grep -rn "Hook.*Extreme" sc_study/` → 0 results
- **Approach**: New pattern file `patterns/hfe.py`. CCI approaches ±200, hooks back. Similar to FAMIR but from deeper extreme.

### GAP-W-002: Priority Hierarchy Dispatcher (T7)
- **Spec**: 9-class priority (ABSOLUTE → NO_ACTION) determines which B-stage wins on conflict
- **Grep 1**: `grep -rn "ABSOLUTE_EXIT\|priority.*class" backend/v9/systems/woodies/` → 0
- **Grep 2**: `grep -rn "dispatch.*priority\|priority_order" backend/v9/systems/woodies/` → 0
- **Grep 3**: `grep -rn "if.*stop.*elif.*eod" backend/v9/systems/woodies/` → 0
- **Approach**: Add `evaluate_active_trade(bar, trade_state)` to woodies_system.py with if-elif chain matching spec priority order.

### GAP-W-003: Active Phase B1-B14 (T3 — all 14 stages)
- **Spec**: Woodies V1 defines 14 active-trade management stages within the system
- **Reality**: All trade management is in `services/trade_manager/` and `services/layer4/`, external to Woodies
- **Architectural note**: Current architecture splits trade management OUT of individual systems. Spec expects it INSIDE Woodies. This is a fundamental design question for SA.
- **Approach**: Either (A) move relevant L4 rules into Woodies per spec, or (B) document the architectural divergence and accept trade_manager as the canonical implementation.

## P1 — Blocks SHADOW (7 items)

### GAP-W-004: Touch-Points #1-#6 (T5 — 7 endpoints)
All 6 advisory touch-points are unimplemented in Woodies. Endpoints exist in other systems but Woodies doesn't consume them.
- `/day_type/current` (TP#1), `/tpo/current` (TP#2a, TP#4), `/veto/state` (TP#2b), `/layer0/state` (TP#6)
- Missing entirely: `/otf-clarity/state` (TP#3, TP#5)
- **Approach**: Add `_query_touch_point(endpoint, fallback)` helper in woodies_system.py. Read each TP, use fallback if timeout/error (per spec degraded mode).

### GAP-W-005: Entry Classification A6 (REACTIVE vs INITIATIVE)
- Spec: A6 classifies as REACTIVE (2ct tight) or INITIATIVE (3ct wide)
- Code: Uses TACTICAL/STRATEGIC (different semantics)
- **Approach**: Map spec terms to code or add explicit REACTIVE/INITIATIVE enum.

### GAP-W-006: Universal Checks A7
- News ±5min, cool-down, $200 cap, stop 3-8pt, bridge health, EOD >60min
- None implemented in Woodies (some exist in gateway/trade_manager)
- **Approach**: Pre-fire validation function reading from risk endpoints.

### GAP-W-007: 18 Terminal States (T6)
- 17 of 18 terminal state string literals not emitted by Woodies
- Only "STRATEGIC" classification exists (not a terminal state per spec)
- **Approach**: Add terminal state emission to each decision point.

## P2 — Polish (3 items)

### GAP-W-008: YAML Runtime Config (T1)
- Config-driven stage ordering/enabling not implemented
- Engine uses hardcoded `detect_all_patterns()` call
- **Approach**: Optional — current hardcoded approach works for V1.

### GAP-W-009: D-Series Rules in Woodies (T8)
- D-001/D-002/D-055/cool-down/cap/time-stop/trail exist in trade_manager/layer4
- Not duplicated inside Woodies
- Same architectural question as GAP-W-003.

### GAP-W-010: UFL/UFH Consumption by Woodies (T10)
- UFL/UFH computed in TPO system (tpo/levels.py:191)
- Woodies A4/B4 don't consume it
- **Approach**: Read from /api/v9/tpo/current ufl_ufh field in TP#2.

---

## Open Query for Strategic Chat

The fundamental question: **Is the Woodies V1 Decision Tree meant to be a self-contained system with all 21 stages internally, or is it an orchestration spec where stages map to different backend services?**

Current architecture: Woodies handles A1 (trend gate) + A3 (pattern detection) + A6 (classification). Everything else (trade management, universal checks, touch-points) lives in separate services.

Spec expects: All 21 stages inside the Woodies decision tree.

This determines whether GAP-W-003 (14 missing B-stages) is a real gap or an accepted architectural divergence.
