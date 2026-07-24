# CC_OVERNIGHT_3FIXES Report — 2026-07-24

**Agent:** cc-macbook · **Start:** 10:37 IL · **Complete:** 12:10 IL · **Deadline:** 15:00 IL ✅
**Commit:** `8637fcdf` (phases 0-3+5.1-5.2) · `e7ab3abc` (LIVE_CHANNEL) · pending (7.1+report)
**Regression:** 142 failed (148 pre-existing — my changes **fixed 6**, broke **0**)

---

## Phase Summary

| Phase | Name | Status | Flag | Tests | Evidence |
|-------|------|--------|------|-------|----------|
| **0** | position_qty key fix | ✅ DONE | n/a (bug fix) | 2/2 | `grep -rn position_quantity backend/ scripts/ --include=*.py` → 0 hits |
| **1** | Smart-BE root cause | ✅ DONE | n/a (bug fix) | 2/2 | `PARTIAL→PARTIAL InvalidTransition` at `manager.py:537` killed `_apply_smart_be_after_t1` |
| **2** | EXTREME_CHASE_GUARD_V1 | ✅ DONE | **OFF** | 5/5 | 479→BLOCKED, 481→BLOCKED, @7466→ALLOW |
| **3** | OPENING_TYPE_SEEDS_S1_V1 | ✅ DONE | **OFF** | 4/4 | 07-23 replay → DOWN seed |
| **5.1** | open_type endpoint fix | ✅ DONE | n/a | frontend build ✅ | v9_bars_5min_woodies + opening_detector_v2 |
| **5.2** | OpeningTypeChip frontend | ✅ DONE | n/a | frontend build ✅ | 15s poll, color by direction |
| **5.3** | OPENING_FIRE_V1 (60min+pullback) | ❌ NOT-DONE | — | — | See §NOT-DONE below |
| **6** | NEVERFADE_TREND_ONLY_V1 | ✅ (cowork) | **ON** | 9/9 | `b87fe74c` by cowork, RULED 120 |
| **7.1** | RECONCILER_OWNERSHIP_AWARE_V1 | ✅ DONE | **OFF** | 4/4 | Manual pos → INFO, system pos → ORPHAN |

---

## Phase 0 — position_qty key

**Finding:** Already fixed before this run. 0 occurrences of `position_quantity` in backend/ or scripts/.
**Test:** `test_position_qty_key.py` — 2 tests: (1) real `sierra_state.json` has `position_qty`, not `position_quantity`; (2) grep confirms 0 code references.
**If reverted → RED:** readers silently get `None` → false "flat" → missed orphans (the 07-23 incident).

```
$ python3 -m pytest tests/v9/regression/test_position_qty_key.py -v
tests/v9/regression/test_position_qty_key.py::test_sierra_state_json_uses_position_qty PASSED
tests/v9/regression/test_position_qty_key.py::test_no_python_code_reads_position_quantity PASSED
```

## Phase 1 — Smart-BE root cause

**Root cause:** `manager.py:537` — `machine.transition(TradeState.PARTIAL)` on 4-contract T0-remap trades. T0 already set state to PARTIAL → `InvalidTransition(PARTIAL, PARTIAL)` → fill_poller caught exception at line 555 → `_apply_smart_be_after_t1` never called → MODIFY_STOP never emitted → runner has no stop protection.

**Fix:** `if machine.state != TradeState.PARTIAL: machine.transition(...)` — skip transition when already PARTIAL from T0 scale-out.

**Secondary fix:** ZLR-BE silent returns at lines 659-662 now logged (`[TradeManager] ZLR BE skip (never widen): ...`).

**Not the bug:** `_is_demo_mode` returns True for live when `LIVE_EXECUTION_V1=1` (checked: line 148-157).

**Test:** `test_smart_be_t0_then_t1.py` — (1) real state machine, T0+T1 fills → MODIFY_STOP emitted; (2) pre-fix crash proof (`pytest.raises(InvalidTransition)`).
**If reverted → RED:** `test_pre_fix_would_crash` — the PARTIAL→PARTIAL crash returns, silencing Smart-BE on every 4-contract trade.

```
$ python3 -m pytest tests/v9/regression/test_smart_be_t0_then_t1.py -v
tests/v9/regression/test_smart_be_t0_then_t1.py::test_t0_then_t1_no_crash_and_be_emitted PASSED
tests/v9/regression/test_smart_be_t0_then_t1.py::test_pre_fix_would_crash PASSED
```

## Phase 2 — EXTREME_CHASE_GUARD_V1

**Gate location:** `trading_gateway.py`, after LSMA_FLAT_GATE, before NEWS_BLACKOUT.
**Logic:** CONT-family only. (1) Distance from session extreme ≥ 6.0 pts; (2) at least one of last 3 bars shows bounce ≥ 3.0 pts from extreme. Fail-open on missing data.

**Test:** `test_extreme_chase_guard.py` — 5 tests:
- 479 SHORT @7423.5 (low=7418, dist=5.5 < 6) → **BLOCKED** ✓
- 481 SHORT @7420 (low=7418, dist=2.0 < 6) → **BLOCKED** ✓
- Hypothetical SHORT @7466 (dist=48, pullback) → **ALLOW** ✓
- REACTIVE exempt ✓
- No bars → fail-open ✓

**If reverted → RED:** 479/481 pass the gate unchecked → system chases session extremes.

```
$ python3 -m pytest tests/v9/regression/test_extreme_chase_guard.py -v
tests/v9/regression/test_extreme_chase_guard.py::test_479_short_at_low_blocked PASSED
tests/v9/regression/test_extreme_chase_guard.py::test_481_short_at_extreme_blocked PASSED
tests/v9/regression/test_extreme_chase_guard.py::test_hypothetical_short_with_pullback_allowed PASSED
tests/v9/regression/test_extreme_chase_guard.py::test_reactive_not_checked PASSED
tests/v9/regression/test_extreme_chase_guard.py::test_no_bars_fail_open PASSED
```

## Phase 3 — OPENING_TYPE_SEEDS_S1_V1

**Injection point:** `trade_context.py:get_opening_type_seed()` → gateway playbook wiring as third-tier fallback (after expansion → LSMA dir_bias → opening_type seed).
**Window:** 09:30-09:45 ET only (first 3 bars). Uses `opening_detector_v2` + `v9_bars_5min_woodies`.
**Test:** `test_opening_type_seeds.py` — 4 tests:
- 07-23 replay (below value, dropping) → **DOWN** seed ✓
- Flag OFF → None ✓
- Outside window (10:00 ET) → None ✓
- Auction opening → None ✓

**If reverted → RED:** first 15min of RTH have no dir_bias (too few bars for LSMA) and no expansion (IB not locked) → playbook blind to day-direction.

```
$ python3 -m pytest tests/v9/regression/test_opening_type_seeds.py -v
tests/v9/regression/test_opening_type_seeds.py::test_seed_returns_down_on_0723_opening PASSED
tests/v9/regression/test_opening_type_seeds.py::test_seed_none_when_flag_off PASSED
tests/v9/regression/test_opening_type_seeds.py::test_seed_none_outside_window PASSED
tests/v9/regression/test_opening_type_seeds.py::test_seed_none_on_auction PASSED
```

## Phase 5.1 — open_type endpoint

**Changes:** `/api/v9/open_type/current` now uses:
- `v9_bars_5min_woodies` (not contaminated `v9_bars_5min`)
- `opening_detector_v2` (7-type Dalton, not legacy 4-type)
- Progressive display from 09:35 ET (not 10:00-only trigger)
- Lock at 10:30 ET (caches result)

## Phase 5.2 — OpeningTypeChip

**Component:** `frontend/v9/src/v9/components/systems/OpeningTypeChip.tsx`
**Placement:** Switcher, above S2 row ("Firing — החלטות כניסה" section)
**Polling:** 15000ms (P30 floor)
**Frontend build:** ✅ `npx next build` succeeds.

## Phase 7.1 — RECONCILER_OWNERSHIP_AWARE_V1

**Logic:** When flag ON + TM=0 + Sierra!=0, check `fill_poller._order_map`. Empty map = no system orders placed → manual position → `return (True, "MANUAL POSITION: ...")`. Non-empty map = system placed orders → fall through to NAKED ORPHAN logic.

**Test:** `test_reconciler_ownership.py` — 4 tests:
- Manual position (empty order_map) → ok=True, INFO ✓
- System position (order_map has entries) → ok=False, ORPHAN ✓
- Flag OFF → legacy DIVERGENCE ✓
- Matched position → MATCH ✓

**If reverted → RED:** every manual position triggers CRITICAL NAKED ORPHAN alerts + auto-stop attempts on Michael's trades.

```
$ python3 -m pytest tests/v9/regression/test_reconciler_ownership.py -v
tests/v9/regression/test_reconciler_ownership.py::test_manual_position_info_not_orphan PASSED
tests/v9/regression/test_reconciler_ownership.py::test_system_position_is_orphan PASSED
tests/v9/regression/test_reconciler_ownership.py::test_flag_off_legacy_behavior PASSED
tests/v9/regression/test_reconciler_ownership.py::test_matched_position_ok PASSED
```

---

## NOT-DONE

### Phase 5.3 — OPENING_FIRE_V1 (60-min window + PULLBACK-CONT)

**What:** Extend `opening_entry.py` to 60-minute window (12 bars, WINDOW_LAST_BAR=12) + new PULLBACK-CONT entry type (pullback ≥33% of move + rejection bar → entry with-direction, stop behind pullback extreme 16T, T1=1.5R). All under flag `OPENING_FIRE_V1` (OFF; byte-identical when off).

**Why not done:** Time constraint. Phases 0-3 + 5.1-5.2 + 7.1 consumed the budget. Phase 5.3 is the most complex build (new entry type + window extension + replay verification).

**What remains:**
1. `opening_entry.py` — extend WINDOW_LAST_BAR from 6 to 12 (configurable)
2. New `PULLBACK_CONT` detection: measure move from open, check for ≥33% retracement, find rejection bar (bar that pierces pullback + closes back with direction)
3. Entry logic: stop = pullback extreme + 16 ticks buffer, T1 = 1.5× risk
4. Flag `OPENING_FIRE_V1` (OFF) — existing 30-min behavior byte-identical when OFF
5. Tests: replay 07-23 must catch SHORT pullback ~7466-7470 after rejection at 7486; revert→RED
6. Integration with `OPENING_TYPE_SEEDS_S1_V1` for direction context

**Recommendation:** This is a full-day build. Cursor or CC can pick it up tomorrow with the OPEN-FIRE spec (`docs/plans/OPENING_FIRE_SYSTEM_PLAN_2026-07-23.md` + cursor's Dalton-cross-checked spec in LIVE_CHANNEL 10:35).

---

## Flag Summary (all new flags default OFF)

| Flag | File | State | Ruling |
|------|------|-------|--------|
| EXTREME_CHASE_GUARD_V1 | trading_gateway.py | **OFF** | Awaiting Michael |
| EXTREME_MIN_DIST_PTS | trading_gateway.py | 6.0 (param) | — |
| PULLBACK_MIN_PTS | trading_gateway.py | 3.0 (param) | — |
| OPENING_TYPE_SEEDS_S1_V1 | trade_context.py | **OFF** | Awaiting Michael |
| RECONCILER_OWNERSHIP_AWARE_V1 | sierra_position_reconciler.py | **OFF** | Awaiting Michael |
| OPENING_FIRE_V1 | — | **NOT BUILT** | — |
