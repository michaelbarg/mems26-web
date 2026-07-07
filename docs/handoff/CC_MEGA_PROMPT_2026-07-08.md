# CC Mega-Prompt — LIVE-ready by RTH open 2026-07-08 (16:30 IL)

**Context:** First LIVE day (07-07): 2 real trades executed successfully (#299 SHORT $70 WIN,
#305 LONG $65 WIN). Multiple bugs surfaced — all documented in `LIVE_FIX_JOURNAL.md`.
Sierra is OFF (Michael closed it). Backend running. Goal: fix everything overnight,
system LIVE-ready tomorrow with 2 contracts.

**Priority:** 🔴 LIVE = real money = the ONLY thing that matters. ⚪ shadow = nice.

**Protocol:** Rule 5 (paste raw, never "done"). Test on SIM before LIVE. Snapshot before
any .env/DLL change. Update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` after each fix.

---

## TASK LIST — ordered by priority (do in this order)

### 🔴 PHASE 1: CRITICAL BUGS (broke today, fix FIRST)

**T1. L2 — MODIFY_STOP reaches Sierra on LIVE** (eb4bc6f landed but VERIFY)
- `_is_demo_mode` fixed to include `mode="live"`. BUT residual: `_get_sierra_order_id`
  returns None for I-58 fallback-captured trades → MODIFY silently dropped.
- **Fix:** in `fill_poller.py` I-58 fallback path, after `on_fill`, call
  `set_sierra_order_ids` with the fill's order IDs (they're in the fill dict).
- **Fix:** convert both silent `return`s in `_emit_modify_stop` (manager.py:118,120)
  to `logger.warning` so we're never blind.
- **Verify:** fire SIM → T1 hit → `trade_result.json` = `MODIFY_STOP_OK` (not
  `MODIFY_STOP_NONE`). Paste raw.
- **Test:** anti-tautological — live trade with T1 hit → MODIFY_STOP emitted (fails
  on old code).

**T2. L4 — Live fill order-id mapping** (shared root with T1)
- Currently: FillPoller uses I-58 fallback (unmapped order_id → most recent active
  trade). This works but `sierra_order_id` is not stored → MODIFY drops.
- **Fix:** in `_execute_live` (gateway), after `accept_setup` + `command_from_setup`,
  register ALL order IDs in `fill_poller._order_map` (same as demo does implicitly
  through the ENTRY fill's `set_sierra_order_ids`). OR: in the I-58 fallback, after
  adopting the trade, store the order IDs.
- **Verify:** fire SIM → FillPoller log shows `registered order X → trade Y` (not
  `unmapped order_id`). Paste raw.

**T3. exit_reason overflow guard** (ea868cc was a hotfix, need a proper guard)
- `exit_reason` column = varchar(30). `ORDER_FAILED:-1:GENERAL_ERROR...` = 42 chars
  → DB crash → session dead → all subsequent ops fail.
- **Fix:** in the V9Trade model or `close_trade`, truncate `exit_reason` to 30 chars.
  Already truncated in fill_poller; add the guard in `close_trade` itself as belt.
- **Test:** close_trade with 50-char reason → stored truncated, no crash.

### 🔴 PHASE 2: LIVE PATH GAPS

**T4. L7 — 2-contract symmetry audit**
- `FIXED_CONTRACTS_2=1` makes sizing return 2. But:
  - `command_from_setup` sends 2 contracts ✓ (verified in SIM)
  - The bracket shows C1/C2/C3 (3 targets) for a 2-contract trade
  - Display shows "0/3 hit" instead of "0/2 hit"
  - Per-contract P&L assumes 3 contracts
- **Fix:** audit every consumer of contract count:
  - `_calculate_pnl` (manager.py:982) — hardcoded `3 * risk_per_contract`
  - Frontend `ActiveTradeCard` — reads contracts from metadata or hardcoded 3
  - `fire_setup` target generation — C3 target unnecessary for 2c
- **Verify:** fire 2c SIM → display shows "0/2 hit", P&L math uses 2, no C3.

**T5. L3 — Monitor shows shadow as "live"**
- `/api/v9/trades/active` returns the most recent non-closed trade — even shadow.
- **Fix:** filter by `mode IN ('demo','live')` in the active-trade query. Shadow
  trades should never appear in the live monitor.
- **Verify:** with a shadow trade open, the monitor shows no active trade.

**T6. L8 — Sierra Ledger deploy + verify**
- Cowork built `sierra_ledger.py` + `live_ledger_routes.py` + `/board` UI.
  Flag `LIVE_LEDGER_V1` OFF.
- **Deploy:** enable `LIVE_LEDGER_V1=1` in .env → restart when FLAT.
- **Verify:** `GET /api/v9/live_ledger` returns the 2 real trades from 07-07
  (#299, #305) with correct Sierra fill prices + P&L. Paste raw.

### 🔴 PHASE 3: VERIFY EXISTING FIXES

**T7. L1 / A7 — ZLR/GHOST routes**
- V2SizingResult.stop_price added (90567fb). Risk_points fallback added.
- Today's A7 failures were `risk < 2pt` (MEMS_MIN_RISK_POINTS), not fire_setup=None.
- **Verify:** wait for a ZLR/GHOST with risk ≥ 2pt → routes (no A7 drop). OR
  temporarily lower MEMS_MIN_RISK_POINTS=1 in .env for one test → restore.
- **Evidence:** paste the routing log showing the fire reached the gateway.

**T8. Pre-open health check**
- `scripts/mems26_verify.sh` → services, DLL, feed, DB.
- Frontend :3000 UP.
- 0 open trades, slots null, reconcile AGREED_FLAT.
- Snapshot `pre-0708`.
- Paste all.

### ⚪ PHASE 4: SECONDARY (after LIVE is solid)

**T9. L5 — Day-type lag** (Normal→Variation/Trend too slow)
- Today: day_type=UNKNOWN for 10 hours after restart → blocked all S2 fires.
- Hydration from DB should happen at startup, not wait for a bar event.
- Flag-OFF, backtest before enable.

**T10. L2b — Stop trails to STRUCTURE after T1** (design change, not a bug)
- Michael wants: after T1, stop trails to nearest structural level (not BE).
- Flag-OFF + backtest. Separate from the L2 bug fix.

**T11. S1 — Clickable trade rows** (UI, nice-to-have)

---

## VERIFICATION OUTPUT (paste at end of work)

```
=== T1: MODIFY_STOP on LIVE ===
<trade_result.json showing MODIFY_STOP_OK>

=== T2: order-id mapping ===
<FillPoller log showing "registered order X → trade Y">

=== T3: exit_reason guard ===
<test output>

=== T4: 2-contract symmetry ===
<display showing "0/2 hit", P&L with 2 contracts>

=== T7: A7 routing ===
<log showing ZLR/GHOST routed, no A7 drop>

=== T8: pre-open health ===
<mems26_verify.sh output>
```

Update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` with each completed item.
Commit hash at end. NOT-DONE section mandatory.
