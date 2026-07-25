# CC-MACBOOK Weekend Report 2026-07-26 (Part C)

**Agent:** cc-macbook | **Deadline:** Sunday 20:00 IL | **Contract:** CC_HANDOFF_CONTRACT.md

## Phase Summary

| # | Phase | Status | Tests | revert→RED | Flag |
|---|---|---|---|---|---|
| W2 | exit-tracking (trade 513) | DONE | 5/5 | 5 fail without fix | EXIT_TRACK_ACTIVITY_V1=OFF |
| W3 | NAKED_STOP_SUSPECT fix | DONE | 5/5 | 2 fail without fix | STOP_RETRY_ON_NONE_V1=OFF |
| W4 | Variation with-trend cont | DONE | 10/10 | 4 fail without fix | VARIATION_WITH_TREND_CONT_V1=OFF |
| W1 | DLL Trade Positions fields | DONE (code) | N/A (DLL) | N/A | Needs Remote Build Monday |
| W1b | Account truth page | DONE | 6/6 | N/A (new endpoint) | Always-on (read-only) |
| W6 | HIGHER_LOW_SECOND_TEST_V1 | DONE | 6/6 | import error without file | HIGHER_LOW_SECOND_TEST_V1=OFF |
| W5 | S6/EXIT-v2 | **NOT-DONE** | — | — | Stretch; continuation map below |

**All new behavior flags = OFF.** No live trading behavior changed.

## W2 — exit-tracking (trade 513)

**Root cause:** Deployed DLL (v8.2.0→merged v9.4.2) lacks Pipeline 5 fill monitor — exit fills (T1/T2/T3/STOP) never written to `trade_fills.json`. fill_poller reads only that file → bracket exits invisible → trade stays FILLED, slot blocked.

**Fix:** `fill_poller._check_activity_exits()` — watches `CLOSED_TRADE_PNL` events from `trade_activity_events.jsonl`. When detected + `sierra_state.json` position_qty=0 + FILLED trade exists → closes with Sierra PnL, back-computes exit_price, frees slot. Flag `EXIT_TRACK_ACTIVITY_V1` (OFF).

**Files:** `backend/v9/services/fill_poller.py` (new method + poll loop wiring) · `backend/v9/tests/test_w2_exit_tracking.py` (5 tests)

**Tests:**
```
$ python3 -m pytest backend/v9/tests/test_w2_exit_tracking.py -v
5 passed in 0.41s
```

**revert→RED:** `git stash` → 5 failed (AttributeError: no ACTIVITY_EVENTS_PATH) → `git stash pop` → 5 passed

## W3 — NAKED_STOP_SUSPECT

**Root cause:** `MODIFY_STOP_NONE` from DLL (stop_ids stale or bracket not settled) overwrites `ORDER_SUBMITTED` in `trade_result.json` → reconcile reads `MODIFY_STOP_NONE` ∉ `_STOP_OK_STATUSES` → `NAKED_STOP_SUSPECT` for 837s (entire trade life). No escalation beyond log.

**Fix (two parts):**
1. `fill_poller._handle_modify_stop_none()`: CRITICAL log + phone push (ALWAYS, not flag-gated). Retry MODIFY_STOP with fresh stop value when `STOP_RETRY_ON_NONE_V1=1` (throttled 1/10s/trade).
2. `bar_level_detector._reconcile_live()`: phone push on NAKED_STOP_SUSPECT verdict.

**Files:** `backend/v9/services/fill_poller.py` · `backend/v9/services/trade_manager/bar_level_detector.py` · `backend/v9/tests/test_w3_naked_stop.py` (5 tests)

**Tests:**
```
$ python3 -m pytest backend/v9/tests/test_w3_naked_stop.py -v
5 passed in 0.12s
```

## W4 — Variation with-trend continuation

**Root cause:** `NEVERFADE_TREND_ONLY_V1` kills all with-trend semantics on Variation days → responsive LONG requires VAL (value-location) → 07-24 REACTIVE LONG @7478 blocked "not at VAL (above_value)" on Variation-UP while counter-trend SHORT went live.

**Fix:** `VARIATION_WITH_TREND_CONT_V1` (OFF):
- On directional Variation (UP/DOWN), allow with-trend continuation using session-extreme chase detection (IB-scaled: `max(6, 0.25*IB_width)`).
- Counter-trend falls to location-fade (ruling #3 preserved).
- Gateway plumbs `day_high`/`day_low` into playbook levels.

**Files:** `backend/v9/systems/daytype_playbook.py` · `backend/v9/gateway/trading_gateway.py` · `tests/v9/regression/test_variation_with_trend_cont.py` (10 tests)

**Tests:**
```
$ BRIDGE_TOKEN=test python3 -m pytest tests/v9/regression/test_variation_with_trend_cont.py -v
10 passed in 0.42s
```

## W1 — DLL Trade Positions fields

**Change:** `sc_study/MES_AI_DataExport_merged.cpp` — expanded `sierra_state.json` with 7 new fields from `s_SCPositionData`:
- `open_pnl` (OpenProfitLoss)
- `daily_pnl` (DailyProfitLoss)
- `high_during_pos` (PriceHighDuringPosition)
- `low_during_pos` (PriceLowDuringPosition)
- `trade_account` (GetTradeAccount)
- `symbol` (GetChartSymbol)
- `daily_total_qty_filled` (DailyTotalQuantityFilled)
- `last_price` (LastTradePrice)

Buffer enlarged 1024→2048. Existing `position_qty`+`avg_price` unchanged.

**READY FOR BUILD:** Michael → Remote Build Monday. Deploy: copy `sc_study/MES_AI_DataExport_merged.cpp` directly (NOT `build_monolithic_cpp.sh` — the monolith generator doesn't include FIX-13 sierra_state section which was added post-generation). Until built, new fields = None (readers handle gracefully).

## W1b — Account truth page

**Backend:** `GET /api/v9/account/state` → reads `sierra_state.json` (not DB synthesis). Returns all fields + open system trade from TM + verdict (flat/system/manual/divergence/unknown). Missing fields = None.

**Frontend:** `AccountStatePanel.tsx` on `/board` page. Position, avg, Open P/L, Daily P/L, High/Low During, working orders, SIM/LIVE badge, ARMED badge, verdict badge. Polling 15000ms.

**Files:** `backend/v9/api/v9/account_state_routes.py` · `backend/v9/app.py` · `frontend/v9/src/v9/components/board/AccountStatePanel.tsx` · `frontend/v9/src/app/board/page.tsx` · `backend/v9/tests/test_w1b_account_state.py` (6 tests)

## W6 — HIGHER_LOW_SECOND_TEST_V1

**Detector:** `backend/v9/systems/five_min/patterns/higher_low_second_test.py`
- Detects 5-phase higher-low structure: push → L1 → recovery ≥33% → L2 > L1+margin → rejection bar
- LONG and symmetric SHORT
- Flag `HIGHER_LOW_SECOND_TEST_V1` (OFF). **Definition awaiting Michael approval.**

**Files:** detector + `tests/v9/regression/test_higher_low_second_test.py` (6 tests)

**NOTE:** Detector is standalone (not yet wired into `five_min_system.py` `process_bar`). Integration points documented in the code. Full wiring deferred to after Michael approves the definition.

## W5 — S6/EXIT-v2 (NOT-DONE)

**Status:** NOT-DONE (stretch). The core blocker remains: per-contract attached OCO means no free contract for individual exit.

**Continuation map:**
1. `docs/handoff/CC_PROMPT_2026-07-14_EXIT_OP_REBUILD.md` — existing spec still valid
2. C++ bracket dispatch must support per-contract exit via CancelOrder + BuyExit/SellExit
3. Backend `write_exit` must target a specific contract's stop_id
4. Requires DLL change + Remote Build + sim verify
5. STALL_EXIT / OPPOSITE_EXIT_V1 remain OFF until EXIT-v2 ships (per CLAUDE.md)

## Flag Guard

All new flags registered in `docs/FLAG_REGISTRY.yaml`:
- `EXIT_TRACK_ACTIVITY_V1` (execution, OFF)
- `STOP_RETRY_ON_NONE_V1` (execution, OFF)
- `VARIATION_WITH_TREND_CONT_V1` (s2, OFF)
- `HIGHER_LOW_SECOND_TEST_V1` (s2, OFF)

## Test Results

```
$ python3 -m pytest [all W2+W3+W1b+W4+W6 test files] -v -q
38 passed in 0.62s
```

No new regressions introduced. Pre-existing test failures (BRIDGE_TOKEN, A1Output import) unchanged.

## What's on Michael (Monday)

1. **Remote Build** — `sc_study/MES_AI_DataExport_merged.cpp` → direct copy to Sierra ACS_Source → Remote Build → reload study
2. **Approve W6 definition** — higher-low second test pattern definition (in WORKPLAN §מה-על-מייקל)
3. **Enable flags** — after sim-verify, per ruling protocol: W2 (EXIT_TRACK_ACTIVITY_V1), W3 (STOP_RETRY_ON_NONE_V1), W4 (VARIATION_WITH_TREND_CONT_V1)
