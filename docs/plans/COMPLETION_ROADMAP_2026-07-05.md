# What "done" requires — completion roadmap (2026-07-05)

Framing: the tool is ~90% BUILT but ~0% ENABLED. "Completion" is not mostly code —
it's finishing a few pieces, then ENABLING + PROVING profitability in a clean
demo window, then the LIVE gates. Four blocks:

## A. Remaining BUILD (code that doesn't exist / half-done)
1. item-20 reconcile → periodic loop + alert (last wiring gap; module + endpoint done).
2. item-11 — sizing consolidation (retire legacy `calculate_size`, V2-only).
3. item-12 — TT_SPEC_V2 (the dead/shallow TT detector — fix or retire; 0 fires ever).
4. item-13 — PB_SHAPE_FILTER_V1 (pullback shape).
5. item-16 — VOL_REGIME (volatile day: wider stops + entry-confirm; contracts stay 3).
6. item-17 — entry-side "why no trade" journal.
7. System 6 finish: outcome-fill hook at trade close (learning loop's 2nd half) +
   reframe counter_flow as CVD-divergence (literature) + T2/T3 perspective in the
   runner path.
8. 3 shallow S4 patterns (TT/FAMIR/HTLB) — fix per the pattern audit or retire.
9. Mechanism-C behavioral test (test debt).

## B. VALIDATION (before real money)
1. Enable the proven pieces as ONE package in DEMO (flag-ON): resolver (item-4),
   zones (item-22), doctrine (item-18), System 6 advisory.
2. Run a CLEAN window: 5 demo days on the improved system, ≥+2R cumulative,
   ZERO mechanical faults.
3. De-biased backtests (initial stops) for a tighter number; confirm each enabled
   flag actually helps live, not just in backtest.

## C. LIVE gates (Michael's own criteria)
1. Demo net-positive over the clean window (currently −0.67R).
2. Zero mechanical faults in the window.
3. RISK_HALT_V1 live (−$450) + a consecutive-loss number.
4. Sierra reconcile live (no orphans) — item-20 loop.
5. Michael's explicit sign-off.

## D. Decisions only Michael can make
1. Which flags to enable + WHEN to start the validation window.
2. The consecutive-loss number.
3. counter_flow refinement (CVD-divergence) confirm.
4. Go-live sign-off.

## The one-line definition of done
Every profitability lever ENABLED, a clean 5-day demo window proving ≥+2R with
zero mechanical faults, the safety halts + reconcile live, and Michael's sign-off.
The code is nearly there; the PROOF is the remaining distance.
