# New-chat onboarding — MEMS26 (2026-07-07, REAL MONEY LIVE)

**Priority rule (Michael):** on REAL MONEY. 🔴 LIVE = the only priority; ⚪ SHADOW = nice-to-have.
Be crisp + calm + organized. For live-system questions → read the CODE or ask CC, **not the screen**.

## Where we are (verified today)
- **Order path to Sierra WORKS** — 2-contract SIM order ORDER_SUBMITTED + fills, no GENERAL_ERROR
  (root was `sc.SendOrdersToTradeService` vs Sim-Mode mismatch; fixed DLL 9d314d0).
- **Live is armed + real money ON** (Michael flipped Sim Mode OFF): LIVE_TRADING_V1=1 ·
  LIVE_EXECUTION_V1=1 · FIXED_CONTRACTS_2=1 · RISK_HALT_V1=1/CAP=400 · account 37138283.
- **Safety net built + flag-gated (default OFF until enabled):** P1.2 orphan-fill→CRITICAL ·
  P1.3 reconcile-live · P2.4 System6 per-bar + reconcile-feed · P1.1 EOD-flatten. 18 tests green.
- Capture proven on a demo gateway fire (#297, I-58 fallback). Phantom 297 cleaned.
- Live trades did fire (REACTIVE_SHORT, BEAR_FLAG_SHORT); BE-after-T1 seen working (stop→BE+1T).

## Open 🔴 LIVE issues — the work (source of truth: `docs/plans/LIVE_FIX_JOURNAL.md`)
- **L1 A7** fire_setup routing — verify ZLR/GHOST routes live (no `failed_stages=['A7']`).
- **L2 BE-after-T1** — confirm the stop-move fires on **live/demo** every T1 (not just shadow).
- **L3 monitor** shows SHADOW as "live" + no P&L — display/tracking bug.
- **L4 live fill capture** on a real fill (not just demo).
- **L5 day-type lag** (task #22) · **L6 T1/T2 P&L from Sierra** (task #17).
- **L7 2-contract symmetry** — whole system must read contracts=2 everywhere (bracket still shows
  3 targets for a 2-contract trade); audit bracket/targets/P&L/R/command/display.

## Protocol (permanent)
Every trading day: EOD review of LIVE issues → CC fixes in code (tests + raw verify, Rule 5) →
update `LIVE_FIX_JOURNAL.md` + `STATUS_BOARD.md` → carry open items. **Never restart the backend
or deploy a code change while a live trade is OPEN** — investigate only during live; fix when flat/EOD.

## Rules that bit us (don't repeat)
- Verify in code/DB before asserting (Michael caught many mis-diagnoses). Rule 5: paste raw output.
- Cowork's sandbox can't reach the live Mac (PG/backend/Sierra) — route live checks to CC.
- Sandbox git leaves stale `.git/*.lock` — CC clears + commits.
