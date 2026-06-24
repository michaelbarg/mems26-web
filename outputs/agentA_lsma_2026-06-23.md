# Agent A — LSMA-flip variation study: DIRECTION + TREND-STATE + CVD (2026-06-23 RTH)

**Strategy:** Always-in LSMA-flip. Start LONG on the opening drive; at each LSMA cross,
flip (TREND rule: LONG above LSMA, SHORT below). Exit only at a flip. Each new-direction
entry can be gated; when blocked, go FLAT until the next allowed flip.

**Engine:** `outputs/lsma_pattern_sim.py` on `outputs/sim_data_2026-06-23.json`
(79 RTH bars, 13 S2/S4 fires). P&L in points, $ at $15/pt (3 MES).

**Day shape (matters for interpretation):** canonical day_type = **Normal**. Close-to-close
net move is only **+3.5 pts** (7432.5 -> 7436.0), but the session round-tripped: it rose to
**7486.25** intraday then sold back off — i.e. an up-then-down swing, not a clean one-way
trend. 11 of 13 fires were SHORT. trend_state split: GRAY 30 / RED 27 / BLUE 22 bars.
The base TREND LSMA-flip still nets **+111 pts** because it correctly caught the up leg long
and the down leg short across 6 flips.

## Results — ranked by $ (descending)

| Config (env line) | Trades | Win% | Pts | $ | Blocked |
|---|---:|---:|---:|---:|---:|
| `DIRRULE=trend REQ_CVD=1 CVD_WIN=1` | 4 | **100%** | +123.0 | **+$1,845** | 2 |
| `DIRRULE=trend REQ_CVD=1 CVD_WIN=4` | 5 | 80% | +112.0 | +$1,680 | 1 |
| `DIRRULE=trend` (base, no filter) | 6 | 67% | +111.0 | +$1,665 | 0 |
| `DIRRULE=trend REQ_CVD=1 CVD_WIN=2` | 6 | 67% | +111.0 | +$1,665 | 0 |
| `DIRRULE=trend REQ_CVD=1 CVD_WIN=3` | 6 | 67% | +111.0 | +$1,665 | 0 |
| `DIRRULE=trend OPEN_SEED=0` | 5 | 60% | +67.5 | +$1,012 | 0 |
| `DIRRULE=trend REQ_TREND=1` | 1 | 100% | +43.5 | +$652 | 5 |
| `DIRRULE=trend REQ_TREND=1 REQ_CVD=1 CVD_WIN=1` | 1 | 100% | +43.5 | +$652 | 5 |
| `DIRRULE=trend REQ_TREND=1 REQ_CVD=1 CVD_WIN=2` | 1 | 100% | +43.5 | +$652 | 5 |
| `DIRRULE=trend REQ_TREND=1 REQ_CVD=1 CVD_WIN=3` | 1 | 100% | +43.5 | +$652 | 5 |
| `DIRRULE=trend REQ_TREND=1 OPEN_SEED=0` | 0 | — | +0.0 | $0 | 5 |
| `DIRRULE=meanrev REQ_CVD=1 CVD_WIN=1` | 3 | 67% | -31.5 | -$472 | 3 |
| `DIRRULE=meanrev REQ_TREND=1 REQ_CVD=1 CVD_WIN=1` | 2 | 50% | -32.5 | -$488 | 4 |
| `DIRRULE=meanrev REQ_CVD=1 CVD_WIN=4` | 2 | 50% | -42.5 | -$638 | 4 |
| `DIRRULE=meanrev REQ_CVD=1 CVD_WIN=2` | 1 | 0% | -43.5 | -$652 | 5 |
| `DIRRULE=meanrev REQ_CVD=1 CVD_WIN=3` | 1 | 0% | -43.5 | -$652 | 5 |
| `DIRRULE=meanrev REQ_TREND=1 REQ_CVD=1 CVD_WIN=2` | 1 | 0% | -43.5 | -$652 | 5 |
| `DIRRULE=meanrev OPEN_SEED=0` | 5 | 40% | -67.5 | -$1,012 | 0 |
| `DIRRULE=meanrev REQ_TREND=1 OPEN_SEED=0` | 4 | 25% | -68.5 | -$1,028 | 1 |
| `DIRRULE=meanrev` (base) | 6 | 33% | -111.0 | -$1,665 | 0 |
| `DIRRULE=meanrev REQ_TREND=1` | 5 | 20% | -112.0 | -$1,680 | 1 |

### Raw output — top config (quoted, not paraphrased)

```
[2026-06-23] DIRRULE=trend OPEN_SEED=1 REQ_PATTERN=0 PAT_SET=- SYS=all DT_OK=- REQ_TREND=0 REQ_CVD=1
  -> 4 trades, 100% win, +123.0 pts (~$+1845) | 2 flips blocked
```

## Best config — blocked flips -> patterns available

Config: `DIRRULE=trend REQ_CVD=1 CVD_WIN=1` (CVD 1-bar slope must agree with the new
direction).

```
blocked flip 14:00 LONG  [cvd-against]  patterns available = ['REACTIVE_LONG/L', 'FAMIR/L']
blocked flip 14:55 SHORT [cvd-against]  patterns available = none
```

Reading: the 1-bar CVD slope vetoed exactly the two late-session counter-flips that the base
took and (net) gave back. Notably the **14:00 LONG** the CVD blocked is the same bar where the
two LONG fires (REACTIVE_LONG, FAMIR) printed — so on this day the order-flow tape (CVD down)
disagreed with the long-pattern signals, and trusting CVD was the correct call. The 14:55 SHORT
had no aligned fire at all. Blocking both flips kept the strategy flat through the chop and
preserved the +123 pts earned on the clean up-then-down legs.

## Conclusion

On this Normal, round-trip (up-then-down) day, **direction is everything**: every TREND variant
is positive and every MEANREV variant is negative — fading the LSMA here loses ~$1,000-1,700, so
mean-reversion is the wrong regime read. Within TREND, the **CVD 1-bar slope filter is the single
best add**: it lifts the base from +$1,665 / 67% to **+$1,845 / 100%** by vetoing the two
late-day counter-trend flips (incl. the 14:00 long that fought a falling CVD), the only real
improvement any filter delivered. The **trend_state (BLUE/RED) gate is too strict** — it sits in
GRAY most of the session and blocks 5 of 6 flips, collapsing to a single +$652 trade and leaving
most of the move on the table; useful as a no-trade signal but not as the primary entry gate.
**Recommended for a trend day like this: `DIRRULE=trend REQ_CVD=1 CVD_WIN=1`** (short CVD window),
not trend_state confirmation.
