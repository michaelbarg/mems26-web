# Direction-ID accuracy — real-time replay over all RTH days (2026-07-24)

**Question (Michael):** across the days we have in data, replaying in real-time, does the
system identify **direction** correctly?

**Method:** for every RTH day in `v9_bars_5min_woodies` (≥40 bars), re-ran the **validated
day-type engine** (`classify_session`) **bar-by-bar with no lookahead** — exactly what it would
have shown live — feeding it the same directional context the live path gets (prior-day H/L,
prior VAH/VAL). Recorded the engine's `dir_bias` (UP/DOWN) as it evolves, and compared to each
day's **actual** direction (RTH open→close; |move| < 8 pt = RANGE, not graded).
**Validation:** the FINAL (end-of-day) number below = **83%**, which matches the live
`classify_replay` endpoint exactly → the reproduction is faithful.
Script: `scripts/direction_accuracy_replay.py`.

## Headline — the directional read CONVERGES to the truth over the day

| When | Accuracy | Note |
|------|----------|------|
| **COMMIT** (first UP/DOWN call, ~30 min) | **53%** | essentially a coin-flip |
| **@60 min** (IB-lock) | **64%** | |
| **@2 h** | **78%** | |
| **FINAL** (end of day) | **83%** | but this is too late to trade on |
| **committed correctly AND held (0 flips)** | **30%** | the real "confident early" rate |
| avg direction flips / day | **1.4** | it changes its mind ~1–2×/day |

Sample: **34 days** (30 directional, 4 range), mostly 2026-06-08 → 07-23.

## What this means

The engine is **good at direction by the close (83%)** but **only a coin-flip when it first
commits (~30 min, 53%)** — and it **flips 1.4×/day**. Trades fire in the **first hour**, exactly
when the read is weakest. Only **30% of days** did it call direction right early *and* hold it.

This quantifies the live pain (counter-trend entries, whipsaws) and explains why the direction
work was needed. The flags now live all target this window: `OPENING_TYPE_SEEDS` (seed +
escalation-only, no flip), `RESPONSIVE_WITH_DAY_TREND` + dir_bias-held-6-bars (obey the
converging trend, block counter-trend), `EXTREME_CHASE_GUARD` (don't chase the extreme),
`OPENING_FIRE` PULLBACK-CONT (enter on the pullback, not the chase). The root — a weak *early*
classifier — remains the deepest lever.

## Per-day detail

```
date           move actual commit(t)     @60m  @2h   final C? F? flips
2026-06-08   -26.75 DOWN   DOWN@17:50    UP    DOWN  DOWN  =  =  2
2026-06-09   -128.5 DOWN   UP@16:55      DOWN  DOWN  DOWN  x  =  1
2026-06-10  -139.75 DOWN   UP@16:55      UP    -     DOWN  x  =  3
2026-06-11    25.25 UP     UP@16:55      DOWN  DOWN  UP    =  =  2
2026-06-12     9.75 UP     UP@16:55      UP    UP    UP    =  =  0
2026-06-15    30.75 UP     UP@16:55      UP    UP    UP    =  =  0
2026-06-16    -40.0 DOWN   DOWN@16:55    DOWN  DOWN  DOWN  =  =  0
2026-06-17   -104.0 DOWN   DOWN@16:55    DOWN  DOWN  DOWN  =  =  0
2026-06-18    -12.5 DOWN   UP@17:45      -     UP    -     x  .  0
2026-06-19     -2.0 RANGE  DOWN@16:55    DOWN  UP    DOWN  .  .  4
2026-06-22    -33.0 DOWN   UP@16:55      UP    DOWN  DOWN  x  =  1
2026-06-23      5.5 RANGE  DOWN@16:55    UP    DOWN  DOWN  .  .  2
2026-06-24   -18.75 DOWN   UP@16:55      DOWN  UP    DOWN  x  =  3
2026-06-25    -57.0 DOWN   DOWN@16:55    UP    UP    UP    =  x  1
2026-06-26    -1.75 RANGE  DOWN@16:55    UP    UP    DOWN  .  .  2
2026-06-29    39.75 UP     UP@16:55      DOWN  UP    UP    =  =  2
2026-06-30    49.25 UP     UP@16:55      UP    UP    UP    =  =  0
2026-07-01     10.0 UP     DOWN@16:55    UP    UP    DOWN  x  x  2
2026-07-02    -28.5 DOWN   UP@16:55      UP    DOWN  DOWN  x  =  1
2026-07-03      2.5 RANGE  UP@16:55      UP    UP    UP    .  .  0
2026-07-06    28.75 UP     UP@16:55      UP    UP    UP    =  =  0
2026-07-07    -27.5 DOWN   DOWN@16:55    DOWN  DOWN  DOWN  =  =  0
2026-07-08    19.75 UP     DOWN@16:55    DOWN  DOWN  UP    x  =  7
2026-07-09     44.0 UP     UP@16:55      DOWN  UP    UP    =  =  2
2026-07-10    28.75 UP     UP@16:55      UP    UP    UP    =  =  2
2026-07-13    -32.5 DOWN   UP@16:55      -     -     DOWN  x  =  1
2026-07-14    10.75 UP     DOWN@16:55    DOWN  UP    -     x  .  2
2026-07-15   -10.25 DOWN   UP@16:55      DOWN  DOWN  UP    x  x  2
2026-07-16   -44.75 DOWN   UP@16:55      DOWN  DOWN  DOWN  x  =  1
2026-07-17    -34.5 DOWN   DOWN@16:55    DOWN  -     DOWN  =  =  2
2026-07-20    -51.0 DOWN   UP@16:55      DOWN  UP    DOWN  x  =  3
2026-07-21     9.25 UP     UP@16:55      UP    UP    UP    =  =  0
2026-07-22     10.5 UP     DOWN@16:55    UP    UP    UP    x  =  1
2026-07-23     -9.5 DOWN   DOWN@16:55    DOWN  DOWN  DOWN  =  =  0
```
`C?` = first-commit correct · `F?` = final correct · `=` right / `x` wrong / `.` range.

## Caveats
- Small sample (34 days), recent regime. "Actual" = open→close (a day can swing intraday yet
  close near open → RANGE). FLAT threshold = 8 pt.
- COMMIT grades the engine's *first* UP/DOWN statement (~30 min in); most days that is bar 6.
- This grades the S1 **day-type dir_bias**. S4's per-bar Woodies `trend_state` (BLUE/RED) is a
  separate, faster directional signal — a follow-up could grade it the same way.
