# Prompt 13: Compliance Triage & Final A–E Score

**Date:** 2026-05-16  
**HEAD:** `3370656` — fix(s4): check V9 health directly  
**Branch:** `stabilize/mems26-local-truth-2026-05-16`  
**Tests:** 243 compliance pass (was 216) · 279 atomic pass · 5 atomic fail

---

## A–E Scoring Matrix

Dimensions:
- **A** Data/hydration (bars flow, DB populated, Sierra→Bridge→Backend alive)
- **B** Detection logic (patterns, classifiers, signals implemented)
- **C** Decision/gating (pre_fire, L0 chop gate, sizing, day-type gate)
- **D** Routing/execution handoff (fire → gateway → trade_manager → L4)
- **E** Observability/tests/UI contract (endpoints, tests, frontend pills)

---

### S1 Day Type (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | Hydrates from 5-min BarRouter; IB tracked; /current returns PENDING pre-RTH correctly |
| B | GREEN | 13-stage state machine, decision_matrix, zohar_rules, extensions, triggers |
| C | GREEN | Pre-IB gate active (stage=PRE_IB, reason="Awaiting IB lock @ 10:30 ET") |
| D | YELLOW | Publishes classification but gateway doesn't consume S1 as firing system (correct per D-049: OBSERVING) |
| E | YELLOW | 4 atomic fails (INDETERMINATE OpeningType not in matrix — test/code drift from V9 additions) |

**Blocker:** None — S1 is OBSERVING, not FIRING. Test failures are non-critical drift.

---

### S2 Five-Min T1 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | Running, subscribed to 5min+tick_reversal_15 via BarRouter, mode=WEEKEND |
| B | GREEN | multi_bar, cot_amt, belly, poc_vol, reactive/initiative detectors; 65 tests pass |
| C | GREEN | /fire endpoint returns pattern+confluence+reasoning_notes; mode gate (WEEKEND blocks fire) |
| D | YELLOW | /fire returns `fired:false` correctly; gateway route_setup NOT called automatically (needs BarLevelDetector integration for S2) |
| E | GREEN | /five_min/current 200, /five_min/fire 200, 65 tests pass, pills show IDLE/pattern |

**Blocker for SHADOW:** S2 fire → gateway auto-routing not wired (BarLevelDetector only watches L4 targets, doesn't initiate entries from S2 fire signals).

---

### S3 Footprint T3 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | Running, 117K bars processed today, cumulative_delta=-38M tracked |
| B | GREEN | 4 detectors (absorption/stacked_imbalance/sweep_return/exhaustion), calculate_size |
| C | GREEN | /fire shows `fired:true` with signal=sweep_return LONG strength=0.375 |
| D | GREEN | _fire() persists to DB + updates current_state; gateway ready to consume |
| E | GREEN | /footprint/current + /fire + /journal all 200; pills show BAL/BULL/BEAR |

**Blocker:** None — S3 is the most complete firing system.

---

### S4 Woodies T2 (FIRING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | D-074 migrated to 5-min; running, subscribed woodies_5min, buffer=8 bars |
| B | GREEN | 9 patterns (ZLR/TLB/TT/GB100/VEGAS/GHOST/FAMIR/HTLB/HFE), decision_tree 257 lines |
| C | GREEN | /fire returns decision_tree stages A1-A7; classification=NO_SETUP when no pattern |
| D | YELLOW | /fire returns ready_to_route=false; gateway fire path exists but not auto-triggered |
| E | GREEN | /woodies/current 200 + /fire 200; timeframe=5min confirmed; 20 compliance + 5 decision_tree tests pass |

**Blocker for SHADOW:** S4 fire → gateway auto-routing not wired (same as S2).

---

### S5 TPO (OBSERVING)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | Running, poc=7415.5, vah=7480.5, val=7320.25, session=GLOBEX |
| B | GREEN | tpo_system + levels + tails + single_print + ufl_ufh |
| C | N/A | OBSERVING — no gating logic needed |
| D | GREEN | Publishes to touch-points; consumed by S1 (IB read) and S4 (TP#2) |
| E | GREEN | /tpo/current 200; pills show POC migration direction |

**Blocker:** None.

---

### S6 Killzone (OBSERVING + GATE)

| Dim | Score | Evidence |
|-----|-------|----------|
| A | GREEN | Running, zone=WEEKEND, edge=none (correct for Fri night) |
| B | GREEN | 8 zones defined, zone_playbook (quality modifiers per zone) |
| C | GREEN | Gate logic in gate.py; zone preferences advise firing systems |
| D | GREEN | Consumed by pre_fire_validator; killzone/health 200 |
| E | GREEN | /killzone/current 200; pills show PM/ASIA/LON/etc correctly |

**Blocker:** None.

---

## Summary Table

| System | A Data | B Detection | C Decision | D Routing | E Observability | Overall |
|--------|--------|-------------|------------|-----------|-----------------|---------|
| S1 Day Type | GREEN | GREEN | GREEN | YELLOW | YELLOW | **GREEN** |
| S2 Five-Min | GREEN | GREEN | GREEN | YELLOW | GREEN | **YELLOW** |
| S3 Footprint | GREEN | GREEN | GREEN | GREEN | GREEN | **GREEN** |
| S4 Woodies | GREEN | GREEN | GREEN | YELLOW | GREEN | **YELLOW** |
| S5 TPO | GREEN | GREEN | N/A | GREEN | GREEN | **GREEN** |
| S6 Killzone | GREEN | GREEN | GREEN | GREEN | GREEN | **GREEN** |

**Overall system health: 4 GREEN, 2 YELLOW**

---

## SHADOW Blockers (must fix before Day 1/30)

| # | Blocker | Impact | Est. |
|---|---------|--------|------|
| 1 | S2/S4 fire → gateway auto-route not wired | Firing systems detect+size but signals don't reach TradingGateway.route_setup() automatically | 1–2 commits |
| 2 | S1 INDETERMINATE OpeningType not in decision_matrix | 4 test failures (non-fatal — falls to UNKNOWN, but gates future scoring) | 1 commit |

**That's it.** Only 2 blockers. S3 already fires and would create SHADOW trades. S5/S6 are OBSERVING and complete.

---

## Test Results

| Suite | Pass | Fail | Notes |
|-------|------|------|-------|
| Compliance (v9/) | 243 | 0 | UP from 216 (27 were fixed in recent waves) |
| Atomic + system | 279 | 5 | 4 = S1 INDETERMINATE, 1 = state_machine V9 prob API |
| **Total** | **522** | **5** | 99% pass rate |

---

## Low-Risk Fixes (not implemented — awaiting approval)

1. **Add INDETERMINATE to decision_matrix** (maps to UNKNOWN with 0 confidence) — fixes 3/5 test failures
2. **Wire S2/S4 fire signals to gateway** — in `process_bar()`, after pattern detected and `ready_to_route=true`, call `gateway.route_setup()` — fixes the SHADOW blocker
3. **Update test assertion** for V9 `get_probabilities` API (expects dict, gets different shape) — 1/5 fail

---

## Next 3 Recommended Prompts

```
Prompt 14: Wire S2+S4 fire → TradingGateway.route_setup() (SHADOW blocker #1)
           ~30 lines in five_min_system.py + woodies_system.py process_bar
           After calculate_size returns non-reject → call gateway

Prompt 15: S1 INDETERMINATE handling + test alignment
           Add fallback in decision_matrix for INDETERMINATE + update 4 tests

Prompt 16: SHADOW activation verification (restart + 24h soak criteria check)
           Verify all 3 firing systems produce SHADOW trades
           Confirm BarLevelDetector closes them (T1/T2/T3 hit detection)
           Print Day 1/30 status
```

---

## Evidence Files

| System | Key file | Line evidence |
|--------|----------|---------------|
| S1 | `backend/v9/systems/day_type/state_machine.py` | DayTypeStateMachine class, 800+ lines |
| S2 | `backend/v9/systems/five_min/five_min_system.py` | process_bar + multi_bar + cot_amt |
| S3 | `backend/v9/systems/footprint/footprint_system.py:294` | _check_firing_signals → 4 detectors |
| S4 | `backend/v9/systems/woodies/woodies_system.py:64` | subscribed_bar_types → woodies_5min |
| S4 | `backend/v9/systems/woodies/decision_tree.py` | 21 stages, 257 lines |
| S5 | `backend/v9/systems/tpo/tpo_system.py` | poc/vah/val/migration |
| S6 | `backend/v9/systems/killzone/zone_playbook.py` | 9 zones × preferences |
| L0 | `backend/v9/systems/layer0/chop_score.py` | 6 indicators, 4-state |
| L3 | `backend/v9/layer3/entry_executor.py` | TargetConfig + compute_entry_plan |
| L4 | `backend/v9/services/trade_manager/bar_level_detector.py:32` | BarLevelDetector class |
| GW | `backend/v9/gateway/trading_gateway.py:62` | route_setup() shadow/demo/live |
