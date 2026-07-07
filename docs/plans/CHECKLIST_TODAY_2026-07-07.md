# Work plan — TODAY before RTH 16:30 IL (2026-07-07)

Ground rules (Michael): follow conversation guidance (Rule 2 verify-before-trust,
Rule 5 paste raw, snapshot before any out-of-git change). **NO scheduled tasks.**
Goal: a working 2-contract live order proven OUTSIDE hours, then update + test the system.

Status legend: ✅ done · 🔲 to do · ⏳ needs Sierra machine (CC/Michael)

---
## P1 — LIVE ORDER WORKS: 2 contracts, proven outside hours  [Michael point 2 — CRITICAL]
The regression you felt ("worked days ago, then broke") = `sc.SendOrdersToTradeService=1`
(added in 90567fb) is INCONSISTENT with Trade Simulation Mode ON → Sierra ignored ALL orders
(incl. DEMO that worked 07-01). Root proven from Sierra docs (handoff 42c7f34).

- ✅ **P1.1 Fix in source** — CC `a072097` reverted the break + `9d314d0` auto-matches:
  `sc.SendOrdersToTradeService = !GlobalTradeSimulationModeIsOn`.
- 🔲 ⏳ **P1.2 REBUILD the DLL** — the binary is from 06:34 (commit 64ab228); `9d314d0` is
  NOT in it yet. Remote Build + reload study on the Sierra machine.
- 🔲 **P1.3 SIM proof (1 contract):** Sim Mode ON → fire test BUY → expect `trade_fills.json`
  ENTRY fill + ORDER_SUBMITTED (NOT GENERAL_ERROR_OR_NOT_ENABLED). Paste raw. (= OPEN_ITEMS A1)
- 🔲 **P1.4 2-contract proof:** fire a 2-contract order → both contracts submit + fill in Sim.
- 🔲 **P1.5 Prove outside hours:** Globex is open now (pre-RTH) — do the Sim proof now; a
  real 1-contract check only on Michael's go (Sim OFF → SendOrders auto-flips to 1).
- 🔲 **P1.6 ORDER_FAILED handling:** confirm the backend releases the gateway live_slot on
  fail/close (no stuck slot / phantom — happened yesterday; CC added the handler, verify live).

## P2 — DAY-TYPE DIAGNOSIS: breakout to one direction  [Michael point 1]
- 🔲 **P2.1 Close-confirmed IB-break reclass** (task #22, B1/B3): the moment price CLOSES beyond
  the IB, upgrade Normal→Variation/Trend without the bar-close lag. CC build + SHADOW-validate.
- 🔲 **P2.2 Volume-acceptance methodology** (B2): fix typical-price all-or-nothing under-count
  (ignored 12,262 vol yesterday) + full-session denominator. Backtest before enable.
- Note: keep the SAFETY (R:R, entry-confirm, −$400) — fix the recognition, not the guards.

## P3 — REVIEW OPEN ITEMS + INDEX  [Michael points 3, 4]
- 🔲 **P3.1 Open items:** walk `docs/plans/OPEN_ITEMS_2026-07-06.md` (A2 reconcile-wiring, A3
  T1/T2 fill, A4 22:15 flatten, A5 feed-watchdog, A6 fire_setup ✅CC, C1 cont_trend, D System6).
- 🔲 **P3.2 Refresh index:** `python3 scripts/gen_index.py` + `gen_flag_index.py` — SYSTEM_INDEX
  is 2 days stale (07-05). Commit the refreshed index.
- 🔲 **P3.3 A7 fire_setup:** confirm ZLR now ROUTES (CC fixed the code 90567fb; verify live —
  no "FIRE DROPPED failed_stages=['A7']").

## P4 — CLEAN-STATE REVIEW (restore a clean start)  [conversation guidance]
- 🔲 **P4.1 Config drift from yesterday** — Michael ruling on each:
  - `CONT_TREND_FILTER=0` — I turned it off on a MIS-diagnosis (the real blocker was A7).
    Recommend RESTORE to `=1` (its standing state) for a clean start.
  - `MEMS26_MODE=live` · `LIVE_TRADING_V1=1` · `LIVE_EXECUTION_V1=1` — keep armed, or hold
    until the SIM proof is green?
  - `OPENING_WINDOW_FIRE_V1=0` (item-10, you ruled off yesterday) — keep off / reconsider.
- 🔲 **P4.2** Commit CC's uncommitted EOD reports (AMENDMENTS_LOG, MEMS26_ISSUES_REGISTER,
  DESIGNS/MISSED_TRADES).

## P5 — GO (only after P1 SIM proof green)
Sim proof green → (Sim OFF) real order, supervised: 2 contracts · −$400 halt · 22:15 stop ·
System 6 · verify order→fill→P&L==Sierra on the first live fire.

---
## Owners
- **CC (Sierra machine + code):** P1.2 rebuild, P1.3-1.6 test/verify, P2.1-2.2 build+backtest,
  P3.3, P4.2.
- **Cowork (me):** P3.1 open-items review, P3.2 index refresh, P4.1 recommendation, orchestrate
  + verify every step (Rule 5).
- **Michael (Sierra + rulings):** Sim Mode toggle, P1.5 real-order go, P4.1 config rulings.
