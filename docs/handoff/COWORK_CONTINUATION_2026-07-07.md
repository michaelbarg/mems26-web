# Cowork — continuation handoff (2026-07-07, REAL MONEY LIVE)

Read first: `docs/plans/LIVE_FIX_JOURNAL.md` (source of truth) + `STATUS_BOARD.md`.

**Priority:** 🔴 LIVE only · ⚪ shadow = nice-to-have. **Be crisp, calm, organized.**
**Cowork's role:** orchestrate + verify from the repo/DB + build code in the repo (with tests) +
keep the journal/board current + prepare CC handoffs. **Live Mac ops (Sierra, restart, live DB/logs)
→ route to CC** — the sandbox can't reach the live system. **Don't screen-scrape.**

**Hard rules (bit us today):** verify in code/DB before asserting (Rule 5, paste raw). No backend
restart / code deploy while a live trade is OPEN — investigate only during live; fix when flat/EOD.

## State (verified from the repo)
- Order path proven in **SIM** (2-contract fill, no error). Live is armed (Michael flipped Sim OFF):
  LIVE_TRADING_V1=1 · LIVE_EXECUTION_V1=1 · FIXED_CONTRACTS_2=1 · RISK_HALT_V1/CAP=400 · acct 37138283.
- **L2 root FIXED by CC (eb4bc6f, verified in diff):** MODIFY_STOP/TARGET used to emit for DEMO only
  → the stop-move (BE-after-T1) never reached Sierra on LIVE (recorded but not real). Now emits for LIVE.
- CC also fixed a DB crash (ea868cc): ORDER_FAILED reason `...GENERAL_ERROR_OR_NOT_ENABLED` (42 chars)
  overflowed varchar(30) — truncated.
- Safety net built flag-gated (P1.1/P1.2/P1.3/P2.4, 18 tests). Phantom 297 cleaned.

## 🔴 BLOCKER #1 (live) — orders REJECTED by Sierra
The live LONG (trade 303) got `ORDER_FAILED:-1:GENERAL_ERROR_OR_NOT_ENABLED` — **sent and rejected**,
not "not sent." SIM worked; LIVE fails → **Sierra live-trading not armed** (account/order-placement/
broker auth) OR a study/SendOrders regression. **No live order executes until resolved.** Live-side
diagnosis → CC (handoff `CC_CONTINUATION_2026-07-07.md`); Cowork verifies CC's evidence + Sierra root.

## Open work (journal L1–L8, LIVE-first)
- **L8 (URGENT)** — Sierra-sourced LIVE ledger + MANUAL-intervention detect/log. Full spec (tasks
  T1–T6, tests 1–7, verify V1–V5): `docs/handoff/CC_SIERRA_LIVE_LEDGER_2026-07-07.md`. Cowork can
  build the code (reader/ledger/reconcile/manual-tag) with tests; CC provides Sierra data + verifies live.
- L1 A7 route · L2 verify-live (MODIFY reaches Sierra) · L3 monitor shows shadow-as-live/no P&L ·
  L4 live fill capture · L5 day-type lag · L6 T1/T2 P&L · L7 2-contract symmetry.

## Cowork's immediate next steps
1. Verify CC's answer on 303 (mode/state), deploy status (restart done safely?), backend health.
2. Confirm Blocker #1 root (Sierra arming vs regression) from CC's evidence; tell Michael the fix.
3. Build L8 ledger code (flag-gated, tests) while CC handles the live diagnosis.
4. Update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` as items move.
