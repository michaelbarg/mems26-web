# Backtest — System 6 exit signals on real trades (2026-07-05)

Read-only, real detectors, closed trades since 06-22 (bars from entry→exit).
`scripts/backtest_exit_signals.py`. net_pts>0 = exiting on the signal captured
MORE than the actual exit (avoided a give-back); <0 = exited too early.

```
signal                 n   net_pts  net_$/1c  saved  hurt  avg_pts
------------------------------------------------------------------
stall                 17      93.0       465     13     3     5.47
opposite_patterns      5     116.2       581      5     0    23.25
------------------------------------------------------------------
```

## Read
- **price_stall** — the workhorse: fired on 17 trades, **13 saved vs 3 hurt (81%)**,
  net **+93 pts (+$465/contract, ~+$1,395 on 3)**. Avg +5.5 pts/trade. This is
  exactly the "good trade came back to entry" money — exiting when the move
  stalled would have kept it.
- **opposite_patterns** — high-value, low-frequency: 5 trades, **5/5 saved**,
  net **+116 pts (+$581/contract)**, avg +23 pts. When 2 counter patterns fired
  mid-trade, exiting was right every time in this sample.

## Caveats (honest)
- Assumes exit at the signal-bar CLOSE (idealised fill). Real fills differ.
- opposite_patterns n=5 — directionally strong, not statistically large.
- Measures whole-position exit vs actual exit; the runner-only story is similar
  but not identical.
- **failed_volume deferred** — needs live CVD/level at each bar; not faked here.

## Verdict
Both signals are net-positive on your own trades → worth wiring as advisory in
DEMO (flag-OFF today), then let the decision journal confirm live before any
auto-act. Weights: lean on stall (proven, high-n) + opposite_patterns (rare but
decisive).
