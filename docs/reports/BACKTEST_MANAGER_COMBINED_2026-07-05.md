# Combined smart-manager backtest (2026-07-05)

Full exit logic (HOLD while pattern intact + one-timeframing; EXIT on structure
break / stall / 2-opposite) vs the ACTUAL exits, on 83 real trades since 06-22.
`scripts/backtest_manager_combined.py`, real detectors, read-only.

```
  trades   net_pts  net_$/1c  net_$/3c  better  worse     avg
-------------------------------------------------------------
      83     574.5      2872      8618      29      3    6.92
```

## The honest read
**Direction: strongly positive and consistent.** 29 trades better, only 3 worse,
avg +6.9 pts. This agrees with the clean sub-backtests (stall +93, opposite
+116). The structure-based "hold while intact, exit on break" clearly improves
exit timing over the current "T1 → BE → stopped at BE" behaviour.

**Magnitude: OPTIMISTIC — do not read +$8,618 as expected profit.** Two biases
inflate it:
1. **Stop floor = the recorded (often BE-adjusted) stop**, not the initial stop
   → downside is truncated; the sim rarely takes a full-initial-risk loss.
2. **24-bar-close fallback** when nothing triggers → can exit at a favourable
   endpoint on trend days, flattering the sum.

So treat +574 pts as an UPPER-ish bound on the timing edge, not a P&L figure.
The robust, defensible claim is the win/loss COUNT (29:3) and the sign (positive).

## Conclusion
The integrated manager beats current management on exit timing — enough to wire
it as **advisory in DEMO** and confirm live via the decision journal, before any
auto-act. To de-bias the magnitude: re-run with the INITIAL stop (from the
management log SMART_BE.from) and a structural endpoint instead of the fixed
24-bar close. That's the next refinement if you want a tighter number.
