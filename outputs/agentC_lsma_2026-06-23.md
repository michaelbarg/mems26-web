# Agent C — LSMA-flip: Day-type gating + Confluence stacking (2026-06-23 RTH, MES)

**Strategy:** Always-in LSMA-flip. Seed LONG with the opening drive at 08:30; FLIP at
every LSMA cross (TREND rule: LONG above LSMA, SHORT below); exit ONLY at a flip. Each
flip's NEW-direction entry is gated by the filters under test; when blocked, go FLAT.
$ at $15/pt (3 MES). Engine: `outputs/lsma_pattern_sim.py`, data: `outputs/sim_data_2026-06-23.json`
(79 RTH bars, 13 fires). Day-type is canonically **Normal** (classify_replay 67/67);
per-bar the first 12 RTH bars are tagged "Opening", the remaining 67 "Normal".

**Base reference (trend, no filter): 6 trades, 67% win, +111.0 pts (~$1665).**

## Results — ranked by $

| # | Config (env) | Trades | Win% | Pts | $ | Blocked |
|---|---|---:|---:|---:|---:|---:|
| 1 | `DT_OK=Normal REQ_CVD=1` | 4 | **100%** | **+123.0** | **+1845** | 2 |
| 2 | `DT_OK=Normal` (skip Opening) | 6 | 67% | +111.0 | +1665 | 0 |
| 2 | `DT_OK=Opening,Normal` (both) | 6 | 67% | +111.0 | +1665 | 0 |
| 2 | *base — no filter* | 6 | 67% | +111.0 | +1665 | 0 |
| 5 | `DT_OK=Normal REQ_PATTERN=1` (PAT_WIN=2) | 2 | 50% | +32.5 | +488 | 4 |
| 6 | `DT_OK=Opening` alone | 1 | 100% | +43.5 | +652 | 5 |
| 6 | `DT_OK=Normal REQ_TREND=1` | 1 | 100% | +43.5 | +652 | 5 |
| 6 | `DT_OK=Normal REQ_CVD=1 REQ_TREND=1` (triple) | 1 | 100% | +43.5 | +652 | 5 |
| 6 | `DT_OK=Normal REQ_CVD=1 REQ_TREND=1 REQ_PATTERN=1` (quad) | 1 | 100% | +43.5 | +652 | 5 |
| 10 | `DT_OK=Normal REQ_CVD=1 DIRRULE=meanrev` | 3 | 67% | -31.5 | -472 | 3 |

### Notes on the rows
- **Day-type gating alone is a no-op here.** All flips and the seed land on Normal bars
  (the 08:30 seed is on an "Opening" bar but the seed is not day-type-gated; `DT_OK` only
  gates *flip entries*, and every flip after 09:30 is `dt=Normal`). So `DT_OK=Normal`,
  `DT_OK=Opening,Normal`, and base are identical (6/67%/$1665). `DT_OK=Opening` keeps only
  the seed trade and blocks all 5 Normal flips.
- **CVD slope is the only filter that *adds* $.** It removes exactly the two late
  wrong-side entries (14:00 LONG, 14:55 SHORT) whose CVD was rising/against, lifting win%
  to 100% and $ to the day's best while still trading 4 times.
- **Woodies trend gate is too strict for a flip system.** `REQ_TREND=1` demands BLUE-for-long /
  RED-for-short, but at an LSMA cross the Woodies trend label is typically still the *old*
  color (or GRAY), so 5 of 6 entries are vetoed - collapses to the seed only.
- **REQ_PATTERN starves the system.** Aligned S2/S4 fires exist near only 2 of the flips, and
  one of those (10:45 LONG) had a *short* fire nearby that doesn't align, so it drops to 2
  trades / 50%.
- **Mean-reversion is wrong for this day** even with the winning CVD filter (-$472); 06-23
  trended enough intraday that fading the LSMA loses.

## Blocked flips -> patterns available (best config: `DT_OK=Normal REQ_CVD=1`)

```
blocked flip 14:00 LONG  [cvd-against]  patterns available = ['REACTIVE_LONG/L', 'FAMIR/L']
blocked flip 14:55 SHORT [cvd-against]  patterns available = none
```

- **14:00 LONG blocked (cvd-against):** CVD was *rising* (~10.2k, up from ~8k) while price
  cut below->above; an upside reversal was confirmed by **REACTIVE_LONG (S2)** and
  **FAMIR (S4)** fires here. CVD vetoed the flip, but the confluence (two long fires) shows
  this is the one blocked flip where a pattern *was* present - a candidate to whitelist
  later. On 06-23 staying flat was correct (price drifted back down into the close).
- **14:55 SHORT blocked (cvd-against):** no S2/S4 pattern present; CVD strongly up into the
  close vetoed a late short. Correct skip - avoids a wrong-side trade in the last 5 minutes.

All six base flips and their context (for reference):
```
seed 08:30 LONG  (open-drive)         dt=Opening
FLIP 09:30 SHORT trend=BLUE dt=Normal cvd=9058   -> taken (winner)
FLIP 10:45 LONG  trend=RED  dt=Normal cvd=6930   -> taken (winner)
FLIP 11:55 SHORT trend=BLUE dt=Normal cvd=8168   -> taken (winner)
FLIP 14:00 LONG  trend=RED  dt=Normal cvd=10167  -> BLOCKED (cvd-against)  [REACTIVE_LONG, FAMIR present]
FLIP 14:55 SHORT trend=GRAY dt=Normal cvd=12168  -> BLOCKED (cvd-against)  [no pattern]
```

## Conclusion

Day-type gating **does not help on its own** for 06-23: every flip already falls on a
"Normal" bar, so restricting to Normal is a no-op and restricting to Opening throws away
all the good trades. The single lever that improves on base is **CVD-slope confirmation**:
`DT_OK=Normal REQ_CVD=1` raises win-rate from 67% -> **100%** and $ from $1665 -> **$1845**
while only dropping from 6 to 4 trades, because it surgically removes the two late wrong-side
entries. Stacking *more* filters on top (trend and/or pattern) does **not** improve $ - it
just shrinks the book to the single seed trade ($652), since the Woodies trend label lags the
LSMA cross and aligned fires are sparse. Net: on this Normal/balance day, one well-chosen
order-flow confirmation (CVD) beats both naive trend-following and heavy confluence stacking;
day-type as a *gate* adds nothing here, though as a *lens* it correctly argues against the
blind always-in flip that the CVD filter then trims back.
