# CC — Demo slot stuck: runner never closes → slot held forever (fill-feedback broken)

**Date:** 2026-07-01 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — command + raw output (Rule 5), anti-tautological tests, NOT-DONE.
**Priority:** HIGH — after the FIRST demo trade of the session, the **single demo slot is held forever** → no further demo trade can reach Sierra. Michael caught it live 2026-07-01.

## Symptom (raw)
- `v9_trades` id **261** (demo, S4 ZLR LONG, 09:03 CT): T1 hit 17:05, T2 hit 17:12, **C3 runner never closes** → `state=PARTIAL`, `t3_hit_ts/stop_hit_ts/exit_ts = NULL`, pnl_r=1.5.
- `/api/v9/gateway/status` → `demo_slot=261` **stuck occupied** hours later, while **Sierra has no active position** (Michael confirmed).
- Subsequent signals (S2 INITIATIVE 262/263, more ZLR) → **shadow-only** ("DEMO slot occupied, skipping" `trading_gateway.py:439`) → never reach Sierra.

## Root cause (pinned)
1. The **runner (C3) is trailed but never CLOSED** in the backend: `[Woodies] RUNNER_T2` logs recompute the runner target each bar (t2=7550→7554→7555…) but **no exit fires** → `on_trade_close` (`trading_gateway.py:528→542 demo_slot=None`) is never called → slot held.
2. The **fill-feedback loop is starved:** `FillPoller` (`backend/v9/services/fill_poller.py`, runs when `MEMS26_MODE=demo` ✓) reads `~/SierraChart_Data/v9_export/trade_fills.json` — but that file is **empty (0 bytes)**. Sierra/DLL writes `trade_result.json` (MODIFY_STOP_OK) but **not fills** → the poller has nothing to reconcile → the backend never learns the trade closed.
- Net: **one demo trade per session, then the slot is dead.** Critical single-slot bug.

## Do (backend-first — don't depend on the DLL)
**A · Backend runner-close (PRIMARY, backend-only):** the runner MUST close on a real exit and call `on_trade_close(trade)`. Wire the runner's exit — trailing-stop hit, structural/LSMA exit (Michael's rule: runners exit at LSMA), time-stop (W-10), or EOD/session-close — so a PARTIAL demo trade reaches a terminal state → `demo_slot=None` freed. Today's 261 should have closed (LSMA/trail/EOD) hours ago.
**B · Startup + periodic reconcile:** on boot and every N sec, if a demo trade is PARTIAL/open in the backend but **Sierra is flat** (no active position / trade_result shows closed), close it + free the slot. (Prevents an orphaned PARTIAL from wedging the slot across restarts.)
**C · Fix the fill-feedback (with the DLL owner):** make Sierra/DLL write fill events to `trade_fills.json` so `FillPoller._process_fill` (`fill_poller.py:135`) drives the TradeManager to close contracts as they fill — the proper closed-loop. Investigate why `trade_fills.json` stays 0 bytes while `trade_result.json` is written.

## Immediate release (Cowork verified)
A **restart frees the stuck slot** — the gateway inits `demo_slot=None` (`trading_gateway.py:57`) and main.py does NOT re-hydrate open demo trades into the slot. So a restart clears it (261 orphaned as PARTIAL, harmless). **But it re-sticks on the next trade's runner until A/B ship.**

## Tests (anti-tautological)
- A demo trade whose runner hits its exit (trail/LSMA/time-stop/EOD) → `state=CLOSED`, `on_trade_close` called, `demo_slot=None` — then a new signal fills the slot.
- Boot with a PARTIAL demo trade + Sierra flat → reconcile closes it + frees the slot.
- A fill event written to `trade_fills.json` → FillPoller closes the corresponding contract.

## NOT-DONE
- ❌ Do NOT widen to multiple demo slots to "fix" this — the bug is the runner never closing, not the slot count. (Michael's rule is one-at-a-time; a per-system slot is a separate product decision.)
- ❌ Do NOT fake a close without a real exit/fill — reconcile against Sierra truth (flat/closed), not a guess.
- ❌ Do NOT change the entry gates.

## Context
Same session: `DAYTYPE_POSITION_GATE=0` (validation override, revert to =1 after) · `d4363a1` fix(s2) 'c'-crash · first demo trade 261 reached Sierra (T1→BE MODIFY_STOP_OK) — the FIRE + MANAGEMENT work; only the **close/slot-release** is broken.
