# Agent B — LSMA-flip × PATTERN filters (S2 vs S4) — 2026-06-23 RTH (MES)

**Strategy:** always-in LSMA-flip. Seed LONG on the opening drive; at each LSMA cross FLIP
(TREND: LONG above the line, SHORT below); exit only at a flip. A flip's new-direction entry
is taken only if an aligned S2/S4 pattern fired within `PAT_WIN` bars; otherwise go FLAT until
the next allowed flip. P&L in points, $ at $15/pt (3 MES).

**Reference base (trend, no filter):** `6 trades, 67% win, +111.0 pts (~$+1665), 0 blocked`.

There are exactly **5 LSMA flips** this session (after the opening seed):
09:30->SHORT, 10:45->LONG, 11:55->SHORT, 14:00->LONG, 14:55->SHORT.
The opening seed (08:30 LONG) plus those flips give the 6 base trades.

## Results — ranked by $

| # | Config (env) | Trades | Win% | Pts | $ | Blocked |
|---|--------------|:------:|:----:|:---:|:--:|:------:|
| — | *BASE* `DIRRULE=trend` (no filter) | 6 | 67% | +111.0 | **+1665** | 0 |
| 1 | `REQ_PATTERN=1 PAT_WIN=3 PAT_SET=HFE` | 2 | **100%** | +74.8 | **+1121** | 4 |
| 1= | `REQ_PATTERN=1 PAT_WIN=3 PAT_SET=HFE,ZLR` | 2 | 100% | +74.8 | +1121 | 4 |
| 3 | `REQ_PATTERN=1 PAT_WIN=3` (any, all sys) | 3 | 67% | +63.8 | +956 | 3 |
| 3= | `REQ_PATTERN=1 PAT_WIN=4` (any) | 3 | 67% | +63.8 | +956 | 3 |
| 3= | `REQ_PATTERN=1 PAT_WIN=3 SYS_SET=4` (S4 only) | 3 | 67% | +63.8 | +956 | 3 |
| 3= | `REQ_PATTERN=1 PAT_WIN=4 SYS_SET=4` | 3 | 67% | +63.8 | +956 | 3 |
| 3= | `REQ_PATTERN=1 PAT_WIN=3 PAT_SET=ZLR,TLB,HFE,FAMIR` (all-S4 set) | 3 | 67% | +63.8 | +956 | 3 |
| 3= | `REQ_PATTERN=1 PAT_WIN=3 PAT_SET=HFE,FAMIR` | 3 | 67% | +63.8 | +956 | 3 |
| 10 | `REQ_PATTERN=1 PAT_SET=REACTIVE_SHORT` (PAT_WIN=2 or 3) | 1 | 100% | +43.5 | +652 | 5 |
| 11 | `REQ_PATTERN=1 PAT_WIN=2` (any) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=1` (any) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=2 SYS_SET=2` (S2 only) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=2 SYS_SET=4` (S4 only) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=2 SYS_SET=2,4` (both) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=3 SYS_SET=2` (S2 only) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=4 SYS_SET=2` (S2 only) | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_WIN=2 PAT_SET=REACTIVE_SHORT,REACTIVE_LONG` | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `...PAT_WIN=3 PAT_SET=REACTIVE_SHORT,REACTIVE_LONG` | 2 | 50% | +32.5 | +488 | 4 |
| 11= | `REQ_PATTERN=1 PAT_SET=ZLR,FAMIR` (WIN=2 or 3) | 2 | 50% | +32.5 | +488 | 4 |
| 20 | **meanrev** `REQ_PATTERN=1 PAT_WIN=3` | 1 | 0% | -43.5 | **-652** | 5 |
| 20= | **meanrev** `REQ_PATTERN=1 PAT_SET=REACTIVE_SHORT` | 1 | 0% | -43.5 | -652 | 5 |

### Raw line — top pattern-filtered config
```
[2026-06-23] DIRRULE=trend OPEN_SEED=1 REQ_PATTERN=1 PAT_SET=HFE SYS=all DT_OK=- REQ_TREND=0 REQ_CVD=0
  -> 2 trades, 100% win, +74.8 pts (~$+1121) | 4 flips blocked
```

## Why the numbers land where they do (flip <-> fire alignment)

The pattern filter is effectively binary per flip: each of the 5 flips either has an aligned
fire in-window or it doesn't. The session's 11 fire-bars cluster in three pockets
(08:55-09:15 opening, 10:20-13:30 midday, 13:50-14:00 late), while the flips fall at 09:30 /
10:45 / 11:55 / 14:00 / 14:55. At `PAT_WIN<=2` **no flip catches a fire** -> only the opening
seed + the next forced exit survive (2 trades, +$488). At `PAT_WIN=3` the 09:10/09:15 HFE fires
reach the 09:30 SHORT flip, and the 13:50/14:00 fires reach the 14:00 LONG flip.

**S2 vs S4:** S4 strictly dominates S2 here. The only flip S2 can authorize at any window is the
14:00 LONG (REACTIVE_LONG @13:50), which is the day's one *losing* long flip — so S2-only never
beats the +$488 floor (its qualifying flip is a loser). S4's HFE block authorizes the 09:30
SHORT flip, the single most profitable leg, which is why every S4-inclusive config >= +$956 and
the HFE-isolated config tops out at +$1121 by also *excluding* the FAMIR-authorized losing
14:00 long.

## Blocked flips -> patterns available (top config: `REQ_PATTERN=1 PAT_WIN=3 PAT_SET=HFE`)

```
ENTER (seed)  08:30 LONG @7432.50                                  (opening drive)
EXIT          09:30  +43.50  ->  ENTER SHORT @7476.00   OK gated by HFE 09:10/09:15 (S4)
EXIT          10:45  +31.25  ->  blocked LONG  [no-pattern]  patterns available = none   -> FLAT
blocked flip  11:55  SHORT   [no-pattern]  patterns available = none                     -> FLAT
blocked flip  14:00  LONG    [no-pattern]  patterns available = ['FAMIR/L']              -> FLAT
blocked flip  14:55  SHORT   [no-pattern]  patterns available = none                     -> FLAT
```

Note: HFE excludes FAMIR, so the 14:00 LONG (which *would* fire under FAMIR and lost in the
wider all-S4 set) is correctly skipped — that exclusion is exactly what lifts HFE-only to +$1121
over the +$956 of the all-S4 / `HFE,FAMIR` sets. ZLR (13:30, S4) sits near no new flip, so
`HFE,ZLR` is identical to `HFE` to the dollar.

## Conclusion

On 2026-06-23, **S4 patterns gate the flips far more profitably than S2**: the only flip S2 can
authorize is the day's losing 14:00 long, while S4's **HFE** block authorizes the big 09:30
SHORT — the most valuable leg — so every S4-inclusive config reaches +$956 and the HFE-isolated
filter tops the family at **+$1121 (2 trades, 100% win)**. A `PAT_WIN` of **3 bars** is the
minimum that lets opening fires reach the 09:30 flip (WIN <= 2 collapses to a no-fire +$488
floor), and the pattern filter's best move is *exclusion*: dropping FAMIR removes the losing
14:00 long. The mean-reversion direction rule inverts every leg and turns the best pattern
config negative (-$652), so on a trend day like this the trend rule + an S4/HFE pattern gate is
the right pairing — though even the best filter (+$1121) still trails the unfiltered base
(+$1665), i.e. the gate's value here is risk-reduction (100% win, fewer trades), not raw $.
