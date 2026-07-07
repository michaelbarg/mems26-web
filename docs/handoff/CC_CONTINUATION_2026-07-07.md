# CC — continuation work order (2026-07-07, live). You already read CC_SIERRA_LIVE_LEDGER + fixed L2 (eb4bc6f) + the DB-crash (ea868cc).

**Guardrails:** read-only during an open live trade; restart only when FLAT. Rule 5: raw Sierra
evidence, not backend claims. Update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` at the end.

## 🔴 BLOCKER #1 — live orders fail `GENERAL_ERROR_OR_NOT_ENABLED` (the LONG, trade 303)
`exit_reason='ORDER_FAILED:-1:GENERAL_ERROR_OR_NOT_ENABLED'`. The live LONG was **sent and REJECTED
by Sierra** (not "not sent"). SIM worked earlier; LIVE fails. **Diagnose the root, distinguish:**
- **(a) Sierra live-arming (most likely):** is Sim Mode OFF · account **37138283** selected · **Order
  Placement / Auto-Trading armed** · the broker (Teton/IronBeam) connected + **authorized for live
  orders** on that account? Paste the exact Sierra Trade-window state / Message-Log line.
- **(b) our regression:** did the study reload to an OLD binary, or is the SendOrders auto-match
  inactive? Check `sc.SendOrdersToTradeService` value vs Sim-Mode + the deployed DLL mtime (> 06:42).
Tell Michael the EXACT setting to flip if it's (a); fix if it's (b). **Until armed, no live order
executes — flag this to Michael immediately.**

## Confirm state (paste — Rule 5)
1. **303:** `SELECT id,mode,state,direction,pnl_usd FROM v9_trades WHERE id=303;` — was it live?
2. **Deploy:** are `eb4bc6f` + `ea868cc` live? Did you restart? Was a position OPEN when you did
   (guardrail: no restart with an open live trade)? Paste the `[env_loader]` boot line.
3. **Health after the DB crash:** `/api/v9/health` ok · no stuck slot (demo/live_slot=null) ·
   reconcile AGREED_FLAT · no other varchar/DB errors in the log.

## Verify L2 fix on the live path (eb4bc6f)
On the next live stop-move (BE-after-T1): confirm `_emit_modify_stop → sc.ModifyOrder` actually
reaches Sierra — paste the Sierra modify line + the stop value IN Sierra (not just the DB). This is
what proves the "stop recorded-moved but Sierra didn't" bug is really closed.

## Continue L8 — Sierra ledger + manual-intervention (per CC_SIERRA_LIVE_LEDGER_2026-07-07.md)
Tasks T1–T6, tests 1–7, verification V1–V5 (all in that file). Priority after Blocker #1 is
resolved. Reminder: LIVE account only; detect + log MANUAL stop-move / close as distinct events.

## Also open (from the journal, LIVE-first)
L1 A7 route · L3 monitor shows shadow as live + no P&L · L4 live fill capture · L7 2-contract
symmetry (bracket shows 3 targets for 2 contracts). Shadow = nice-to-have, do not block on it.

**Done = Blocker #1 root identified (paste) + state confirmed + L2 live-verified + journal/board updated + NOT-DONE.**
