# Which opening signals carry direction? — testing the fusion hypothesis (2026-07-24)

**Question (Michael):** would fusing level-crossing acceptance/rejection + volume + bar
behavior + how the prior day ended + where today opens identify the opening type — and
therefore direction — more correctly than today's detector (which scored ~53% at first commit)?

**Method:** per RTH day (34 days, 30 directional), compute each candidate signal's directional
call from the first 30 min + prior-day context, and score it against the ACTUAL direction (RTH
open→close, |move|<8pt = range, excluded). Script: `scripts/opening_signal_edge.py`.

## Per-signal directional hit-rate

| Signal | Hit-rate | Fires | Read |
|--------|----------|-------|------|
| A — first-30 min momentum (geometry only) | **65%** | 26 | already beats the engine's 53% |
| B — gap direction (open vs prior close) | **43%** | 23 | **anti-predictive — gaps FADE, don't follow** |
| C — prior-day direction (continuation) | 61% | 23 | modest edge |
| D — open beyond PDH/PDL, take the break | 62% | 8 | ok, low coverage |
| E — level-break ACCEPTED in 30 min | 64% | 14 | your acceptance idea works |
| F — hi-volume + 30 min momentum | **69%** | 13 | **volume adds ~+7 pts** |
| F′ — lo-volume + 30 min momentum | 62% | 13 | low-conviction opens are worse |
| **G — FUSION: hi-vol + momentum, acceptance agrees, skip conflicts** | **73%** | **11** | **the recipe** |
| H — G + require prior-day confirm too | 62% | 8 | over-filtering hurts |

Engine baseline (first real-time commit, ~30 min): **53%**.

## What the data says

1. **Your hypothesis holds: fusion beats the current detector — 53% → 73%.** The winning
   combination is **volume-confirmed opening momentum, cross-checked against level acceptance,
   and skipped when they conflict or volume is low.**
2. **Surprise — the current classifier (53%) is WORSE than raw first-30-min momentum (65%).**
   It over-thinks the open with level geometry and loses information a simple momentum read keeps.
3. **Volume is real (+7 pts).** High opening volume → the momentum is trustworthy (69%); low
   volume → it is not (62%, and those are the whipsaw days). This is Dalton conviction, measured.
4. **Gap is a trap (43% — worse than a coin flip).** Gap-and-go loses; gaps fade. The detector
   must NOT bias with the gap direction.
5. **Half the value is knowing when NOT to trade.** G fires on only ~40% of days (11/30). The
   other 60% are low-conviction / rotational (auction) — exactly the days that produce
   counter-trend whipsaws. Skipping them is as valuable as the 73% directional call.

## Proposed opening-type v3 (direction-first)

Fuse, in the first 30–45 min, in priority order:
1. **Volume gate first** — below-median opening volume ⇒ AUCTION ⇒ no opening trade.
2. **Direction = 30-min momentum** (the strongest base), NOT the level-geometry label.
3. **Level acceptance confirms / vetoes** — accepted break agreeing with momentum = high
   confidence; a break the other way = conflict ⇒ skip.
4. **Ignore the gap as a directional input** (it is anti-predictive); use it only for the
   auction-location context.
5. Prior-day EOD momentum = weak tiebreaker only (adding it as a hard filter hurt).

Then enter with the confirmed direction on a pullback (the PULLBACK-CONT path just built).

## Caveats
Small sample — G rests on 11 fire-days; 73% is suggestive, not conclusive. Recent regime only.
"Actual" = open→close (intraday swing that closes flat = range). Next step: forward-validate G in
shadow and widen the sample; grade S4 `trend_state` the same way as a faster confirmer.
