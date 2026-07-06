# Road to clean LIVE — for tomorrow (2026-07-07)

Goal (Michael): tomorrow the system executes real trades **properly, end-to-end**,
with the BUGS removed — while KEEPING the safety that correctly blocks bad trades.

## What we located today (2026-07-06 live session) — the real causes
1. **LIVE ORDER_FAILED (-1)** = the DLL ignores our `account` field + no error capture.
   `.env SIERRA_LIVE_ACCOUNT` is unused; the order uses the Sierra CHART's selected
   account. (OPEN_ITEMS A7 · handoff `CC_DLL_LIVE_ORDER_FAILED_2026-07-06.md`.)
2. **ZLR never routes** = A7 `fire_setup=None` drops the fire before the gateway
   (OPEN_ITEMS A6 · `CC_WOODIES_ROUTE_A7_FIRE_SETUP_2026-06-30`).
3. **Phantom live trades** = the system doesn't handle ORDER_FAILED → PENDING trade +
   stuck slot (cleared 293/296 by hand today).
4. **Day-type lag** cost 3 conf-0.80 longs (OPEN_ITEMS B1/B2, task #22) — secondary.

## The distinction — fix BUGS, keep SAFETY (do NOT run "without limits")
- **Remove (bugs that BLOCK valid trades):** DLL account, A7 fire_setup, ORDER_FAILED
  handling, cont_trend mis-tuning (C1), day-type lag (B).
- **KEEP (safety that BLOCKED bad trades correctly today):** −$400 halt · R:R gate
  (rejected 0.11/0.22/0.43) · entry-confirm (no red-bar longs) · risk caps · 2 contracts.
  These are not "limits to remove" — they saved us from ~10 marginal entries today.

## Execution sequence (ordered — each unblocks the next)
**Step 1 — Sierra config (Michael, on the Sierra machine):**
- On the trade DOM, **select account 37138283** + **arm Order Placement / Auto Trading**.
- Do the first validation in **Trade Simulation Mode ON** (Sierra simulates — zero real money).

**Step 2 — DLL fix (CC, rebuild+deploy on the Sierra machine, `SIERRA_DLL_OPS.md`):**
- Capture `sc.GetTradingErrorText(r)` into `trade_result.json` (stop being blind).
- Parse + apply `account`; set `sc.SendOrdersToTradeService` (gated so DEMO still sims).

**Step 3 — A7 / fire_setup (CC):** build fire_setup for every routable pattern using the
V2 stop → ZLR (long+short) route instead of dying at A7.

**Step 4 — Backend ORDER_FAILED handling (CC):** on result=ORDER_FAILED → mark trade
CANCELLED + release live_slot (no more phantoms).

**Step 5 — SIM proof (Michael + CC, before real money):** one `mode:live` order in Sierra
Sim Mode → prove order→fill→P&L==Sierra to the cent. Paste evidence. THIS is OPEN_ITEMS A1.

**Step 6 — go real:** Sim Mode OFF · account selected · all gates + −$400 + 22:15 on ·
supervised first trade (verify the round-trip). Only after Step 5 is green.

## Secondary (after live works — don't block on these)
Day-type lag/volume methodology (task #22) · cont_trend window (C1) · reconcile wired
(A2) · System 6 timer-button (task #20) · SQLite hydration noise (F1).

## Verification discipline (Rule 5, for every step)
Paste the raw command + output. Declare a step done only on evidence, not "should work" —
today proved why (multiple mis-diagnoses corrected only by reading code/logs).
