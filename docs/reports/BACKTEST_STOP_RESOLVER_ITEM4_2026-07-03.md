# Item-4 backtest — old stop vs STOP_RESOLVER_V1 (2026-07-03)

**Gate:** required before enabling `STOP_RESOLVER_V1` (CC left it in NOT-DONE).
**Data:** 86 real trades since 2026-06-22 (all shadow/demo, closed) × 2,374
canonical `v9_bars_5min_woodies`. **Read-only** — `scripts/backtest_stop_resolver_item4.py`.
Uses the REAL `resolve_stop()` CC built.

## Result

```
pattern             n  oldRisk  newRisk financed reject saved    ~R+
--------------------------------------------------------------------
REACTIVE_SHORT     28      7.3      6.1       10      0    13   44.8
INITIATIVE_SHORT   13      6.5     10.3        8      1     7   16.2
REACTIVE_LONG       9      8.3      6.3        1      0     0    0.0
ZLR                 8      4.5      8.3        4      0     3    6.2
HFE                 6      4.5      5.9        5      2     1    1.2
FAMIR               4      9.5      4.1        0      0     1    4.3
INITIATIVE_LONG     4      7.4      8.1        1      0     2    1.9
TLB                 3      9.7      7.5        0      1     0    0.0
BULL_FLAG_LONG      3     10.5      6.2        1      0     1    1.7
HTLB                3      8.3      3.8        0      0     0    0.0
BEAR_FLAG_SHORT     2     14.1      9.5        1      0     2    5.8
VEGAS               2     11.0      3.4        0      0     0    0.0
GHOST               1     13.0      8.5        0      0     0    0.0
--------------------------------------------------------------------
TOTAL              86                         31           30   82.2
```

## What it says

1. **36% of stops were "financed" (below the 0.5×ATR floor)** — 31/86. The exact
   problem Michael flagged. Concentrated where it hurt: REACTIVE_SHORT 10/28,
   INITIATIVE_SHORT 8/13, HFE 5/6, ZLR 4/8.
2. **30 trades hit their old (tight) stop while the new in-band stop would have
   held** — premature stop-outs the resolver prevents. This is consistent with
   the 07-02 EOD headline (right-direction shorts died −1R on tight stops).
3. **The resolver both widens AND tightens, per pattern.** Widens the tight
   ones (REACTIVE 7.3→6.1 is actually tighter avg but fewer sub-floor; ZLR
   4.5→8.3, INITIATIVE_SHORT 6.5→10.3 = wider). Tightens some (FAMIR 9.5→4.1,
   VEGAS 11→3.4, HTLB 8.3→3.8).

## Caveats — why this is EVIDENCE, not a P&L promise (do not enable on this alone)

- **`~R+` (82.2) is an UPPER BOUND**, not expected profit: it credits the full
  favorable excursion after entry / new risk. Real capture is a fraction (exit
  logic caps it). Treat the *count* (30 saved, 31 financed) as the signal, not
  the R sum.
- **The cost side is not netted.** A wider stop means a BIGGER loss on the
  trades that still fail. This pass counts saves, not the net. A full pass must
  net wider-loser $ against saved-R before enable.
- **Rung proxy ≠ the exact package §4 ladder.** Rungs here = generic bar
  extremes near entry. VEGAS/GHOST/FAMIR use pattern-internal levels (cup /
  shoulders / stages) not modelled → their rows are the fallback proxy; the
  tightening there is suspect and must use the real ladder.
- 3 trades hit `no_stop_in_band` (reject) — all rungs outside the band → fall
  back to the current anchor (safe).

## Recommendation

The financed-stop problem is **real and quantified** (36%, 30 preventable
stop-outs) — item-4 is the right lever. But **keep `STOP_RESOLVER_V1` OFF** until:
(a) it's wired at the S2/S4 anchor choke points with the REAL per-pattern
ladders (not the proxy), and (b) a net-P&L pass (saved-R minus wider-loser $)
is green. Both are the evening/next build. Enable = Michael + net-positive
backtest.
