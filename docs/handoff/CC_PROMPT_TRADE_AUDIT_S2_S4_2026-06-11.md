# CC Prompt — Per-Trade Audit + S2 Silence + S2/S4 Deep Planning (2026-06-11)

**Contract:** follow `docs/handoff/CC_HANDOFF_CONTRACT.md` — anti-tautological tests,
mandatory NOT-DONE section, paste raw command+output for every claim (Rule 5).
**Discipline:** diagnose first, fix second; read current code before proposing changes;
flag-gated default-OFF for any trading-logic change; Standing Decisions stay OFF.

## Context (verified by Cowork from live DB/API, 2026-06-11 evening)

- 42 trades in `v9_trades` (ids 10–62), ~30 fired today 06-11. Data dumps:
  `docs/reports/trades_full.json` (API-enriched) + `docs/reports/mgmt_log.json`.
- Trades page works (verified in Chrome on MACBOOK — code/CORS/env all clean).
- Today's flags ON: `S1_PROVISIONAL_DAYTYPE=1 STOP_ANCHORS_V2=1 MEMS_MIN_RISK_POINTS=2 MEMS_MAX_RISK_POINTS=60`.

## Q1 — S2 near-silence (TOP PRIORITY — Michael: "S2 fired only once, something blocked it; there were clear S2 patterns")

Today S2 produced only: 2 fires (ids 33 REACTIVE_SHORT 10:15 ET, 43 REACTIVE_LONG 12:15 ET)
and only 2 pre_fire rejections (20:30 IL risk 73>60; 22:15 IL R:R<1.0 reward=10.06 risk=17.75).
So detections themselves are scarce — the block is UPSTREAM of pre_fire.

Audit the full S2 path for 06-11 RTH: `five_min_system.py` `_detect_reactive`/`_detect_initiative`
→ dispatcher → gateway → pre_fire. For every 5-min bar in RTH answer: did detection run,
what condition failed (geometry? volume? day_type gate? arming? `S2_REQUIRE_COT_AMT` regression?
`belly`/`poc` None-handling? bar staleness on the 5min stream?). Add (flag-gated, default-OFF)
DEBUG logging of per-bar S2 condition outcomes if needed to answer definitively.
Deliverable: a table of every S2 candidate bar today × which condition killed it.

## Q2 — pnl_r units bug (winners)

For losers `pnl_r=-1.0` exactly; for winners `pnl_r == pnl_usd / 1.25` (i.e. **ticks**, not R).
Examples: id 20 pnl_usd=582.50 → pnl_r=233.0; id 30 50.50→40.40; id 13 66.88→26.75.
Find where winner pnl_r is written (trade close path / trade_manager) and fix to true
R-multiple (= pnl_pts / initial risk pts, sizing-weighted). Regression test RED-on-revert.

## Q3 — Shared stop anchors / re-fire storm (HFE)

Six trades share stop 7323.25 (ids 45–49 +44) and six share 7387.25 (ids 52–57, 59,61? verify).
HFE re-fired SHORT 6× consecutively into a rising market (ids 45–49, then 52–57, 59),
risk growing 17.75→39pts as price moved away from the fixed anchor; combined HFE damage
today ≈ −$1,957 on 4 stop-outs (49, 56, 57, 59). Questions:
1. Where does the HFE stop anchor come from (STOP_ANCHORS_V2 path)? Is a stale/rolling level
   reused across hours? Is that intended?
2. Is there ANY re-entry cooldown / same-pattern-same-direction limiter / consecutive-loss
   breaker? If not, propose one (flag-gated): e.g. block same pattern+direction for N bars
   after a stop-out, or after 2 consecutive losses on the pattern that session.

## Q4 — Per-trade spec-conformance audit (Michael: "did the system act as it should?")

For each of today's trades verify against intended behavior and mark OK/VIOLATION:
- entry matched pattern definition (HFE/TLB/ZLR/REACTIVE per spec docs)
- stop = intended anchor; risk pts within [2,60] gates (note ids 24/26/27 risk 1.0–2.0pt
  fired 06-10 BEFORE the gate — confirm timing, not a gate failure)
- T1 = SA.t1_price ladder value for that risk bucket (0.4–0.8R observed — confirm ladder rows)
- SMART_BE applied after T1 (mgmt_log) and stop moved exactly to BE+1T
- exit_reason consistent with price path (STOP_HIT at BE = scratch, not loss)
- id 22 `manual` exit pnl=0 — explain; ids 58/60 exit_reason None — open or close-failure?
- TIME_STOP on ids 20/31 — which time stop fired, per which rule?

## Q5 — Inputs for T1/T2/runner redesign (do NOT implement — analysis only)

Today's structure: T1 scalp 0.4–0.8R → SMART_BE → runner has NO T2/T3 (Option 1) and NO trail
→ runner exits on opposite signal/time-stop. Result: winners avg ≈ +$60, full losers −1R on
17–39pt risks (−$330…−$585). Win 69%, PF 0.93 — structurally negative edge.
Produce data CC-side: for each closed trade, the runner's max favorable excursion after T1
(from bars) vs where a CCI-cross T2/T3 (§1.6) or a 2-stage trail would have exited.
We need numbers to choose between: (a) wider T1 ladder, (b) implement §1.6 CCI-cross T2/T3,
(c) progressive trail (C.2/C.4 orphans in `gateway/trade_management.py`), (d) cap risk via
tighter MAX_RISK or risk-normalized sizing. Michael decides at the gate — bring the table.

## NOT-DONE / Out of scope

- No re-enabling of chop gates / COT-AMT (Standing Decisions).
- No LIVE changes; everything SHADOW + flags default-OFF.
- Frontend untouched.

## Report

Write findings to `docs/reports/TRADE_AUDIT_S2_S4_2026-06-11.md` with raw evidence per claim,
then update `docs/plans/ROADMAP_TO_LIVE.html` + `docs/plans/STATUS_BOARD.md` per protocol.
