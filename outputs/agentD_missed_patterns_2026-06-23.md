# Agent D — Missed-Pattern / Pattern-Alignment Analysis — 2026-06-23 RTH

**Instrument:** MES (3 contracts, $15/pt). **Day type (canonical):** Normal (verified `classify_replay`, 67/67 windows).
**Question (Michael):** *"Where the strategy doesn't trade, which patterns COULD have fired"* — map the LSMA-flip strategy against the day's actual S2/S4 fires.

**Side convention:** `close > lsma` = **ABOVE** (trend wants LONG); `close < lsma` = **BELOW** (trend wants SHORT). "Agrees-trend?" = does the fire's direction match the LSMA side it printed on.

> **Read this first — two different P&L numbers, do not conflate them:**
> - **Base LSMA-flip strategy (Michael's rule, seed long + flip at each cross, exit only at flip):** `+111.0 pts ≈ +$1,665`, 6 trades, 67% win — this is what the *flip* strategy earns on the price path.
> - **The 13 raw S2/S4 shadow fires (their own actual P&L):** net **−$138** for the day. The patterns themselves lost money; the flip strategy made money. That gap is the whole story below.

---

## (a) 13-Fire Alignment Table

| ct | sys | pattern | dir | side (LSMA) | agrees-trend? | actual $ | high-vol? (>1.5× tr20) | cvd-agrees? |
|----|-----|---------|-----|-------------|---------------|---------:|------------------------|-------------|
| 08:55 | S4 | TLB | SHORT | ABOVE | **FIGHT** | −124 | no (0.73×) | no |
| 09:05 | S4 | HFE | SHORT | ABOVE | **FIGHT** | −68 | no (0.67×) | no |
| 09:10 | S4 | HFE | SHORT | ABOVE | **FIGHT** | −41 | no (0.80×) | no |
| 09:15 | S4 | HFE | SHORT | ABOVE | **FIGHT** | −34 | no (0.59×) | yes |
| 10:20 | S2 | BEAR_FLAG_SHORT | SHORT | BELOW | AGREE | +45 | no (0.63×) | yes |
| 10:20 | S2 | REACTIVE_SHORT | SHORT | BELOW | AGREE | +38 | no (0.63×) | yes |
| 10:25 | S2 | REACTIVE_SHORT | SHORT | BELOW | AGREE | −266 | no (0.80×) | no |
| 12:45 | S2 | REACTIVE_SHORT | SHORT | BELOW | AGREE | +143 | no (0.70×) | yes |
| 12:55 | S2 | REACTIVE_SHORT | SHORT | BELOW | AGREE | +18 | no (1.39×) | no |
| 13:30 | S2 | REACTIVE_SHORT | SHORT | BELOW | AGREE | +62 | no (0.76×) | yes |
| 13:30 | S4 | ZLR | SHORT | BELOW | AGREE | +66 | no (0.76×) | yes |
| 13:50 | S2 | REACTIVE_LONG | LONG | BELOW | **FIGHT** | −90 | **YES (1.75×)** | yes |
| 14:00 | S4 | FAMIR | LONG | ABOVE | AGREE | +113 | **YES (1.62×)** | no |

**Agree vs Fight (by fire's own actual $):**
- **AGREE-with-trend fires:** n=8, sum = **+$219**
- **FIGHT-the-trend fires:** n=5, sum = **−$357**
- **All 13 fires:** **−$138**

Every "fight" fire lost money except none (all five negative). Trend-side agreement flipped the sign of the book.

### Per-pattern roll-up
| pattern | n | agree | fight | total $ | agree $ | fight $ |
|---------|--:|------:|------:|--------:|--------:|--------:|
| FAMIR | 1 | 1 | 0 | **+113** | +113 | 0 |
| ZLR | 1 | 1 | 0 | **+66** | +66 | 0 |
| BEAR_FLAG_SHORT | 1 | 1 | 0 | **+45** | +45 | 0 |
| REACTIVE_SHORT | 5 | 5 | 0 | −5 | −5 | 0 | (4 of 5 green; the lone −266 at 10:25 sinks it) |
| REACTIVE_LONG | 1 | 0 | 1 | **−90** | 0 | −90 |
| TLB | 1 | 0 | 1 | **−124** | 0 | −124 |
| HFE | 3 | 0 | 3 | **−143** | 0 | −143 |

---

## (b) LSMA-Flip → Aligned-Fire Map (±2 bars)

Opening side at 08:30 = ABOVE → seed LONG with the opening drive. **5 flips during RTH.**

| # | flip @ | from → to | new-dir | aligned fire within ±2 bars? | verdict |
|---|--------|-----------|---------|------------------------------|---------|
| 1 | 09:30 | ABOVE → BELOW | SHORT | — none — | **SKIP** (pattern-gate goes FLAT) |
| 2 | 10:45 | BELOW → ABOVE | LONG | — none — | **SKIP** |
| 3 | 11:55 | ABOVE → BELOW | SHORT | — none — | **SKIP** |
| 4 | 14:00 | BELOW → ABOVE | LONG | REACTIVE_LONG/L@13:50 (−90), FAMIR/L@14:00 (+113) | **CONFIRMED** |
| 5 | 14:55 | ABOVE → BELOW | SHORT | — none — | **SKIP** |

**Confirmed flips: 1 of 5. Skipped flips: 4 of 5.** The S2/S4 fire cluster does **not** line up with the LSMA crosses on this day — 4 of the 5 crosses have zero pattern support in the ±2-bar window. (Aside: 14:55 itself was a 2.91× volume spike but printed no S2/S4 fire — the gate would skip it anyway; it was only a −$15 leg so no loss.)

---

## (c) Missed-Opportunity Quantification — base legs vs pattern-gating

Each base LSMA-flip leg, and whether a pattern-gated version keeps it:

| leg | entry → exit | dir | pts | $ (3 MES) | aligned fire at flip? |
|-----|--------------|-----|----:|----------:|------------------------|
| 1 | 08:30 → 09:30 | LONG | +43.50 | **+652** | NO → would SKIP |
| 2 | 09:30 → 10:45 | SHORT | +31.25 | **+469** | NO → would SKIP |
| 3 | 10:45 → 11:55 | LONG | +24.75 | **+371** | NO → would SKIP |
| 4 | 11:55 → 14:00 | SHORT | +23.50 | **+352** | NO → would SKIP |
| 5 | 14:00 → 14:55 | LONG | −11.00 | **−165** | YES (REACTIVE_LONG, FAMIR) → KEEP |
| 6 | 14:55 → 15:00 | SHORT | −1.00 | −15 | NO → would SKIP |
| | | | **+111.00** | **+1,665** | |

**The four legs that make the money (+$652, +$469, +$371, +$352 = +$1,845) all occur at flips with NO aligned pattern fire.** The *only* flip a pattern filter would confirm (14:00 LONG) is the day's one **losing** leg (−$165).

- **Profit FORGONE by skipping unconfirmed flips:** **+$1,845**
- **Loss AVOIDED by skipping unconfirmed flips:** −$15 (leg 6 only)
- **Net effect of pattern-gating vs base on this day: −$1,830** → on 2026-06-23, requiring a pattern to confirm the flip is **strongly counter-productive.** The base unfiltered flip rule is the winner; the fires would have you flat through every good move and long into the only bad one.

### Losing-position / earlier-signal windows
| leg | dir | window | worst adverse (MAE) | realized | note |
|-----|-----|--------|--------------------:|---------:|------|
| 4 | SHORT | 11:55→14:00 | −5.0 pts (−$75) at 12:20 | +$352 | minor heat, recovered |
| 5 | LONG | 14:00→14:55 | **−11.75 pts (−$176) at 14:15** | **−$165** | the day's pain leg — taken *because* patterns confirmed it |

The 14:00 LONG is the textbook case where the patterns actively hurt: REACTIVE_LONG (13:50, on a 1.75× volume bar, CVD rising) + FAMIR (14:00) both fired LONG right as price poked above the LSMA, the strategy went long at 7446, and price fell to a −$176 MAE before closing the leg at −$165. An aligned **SHORT** signal would have been the correct read there, but none fired; the long-side patterns were the trap.

### Single clearest missed opportunity
**The 09:30 SHORT flip (leg 2, +$469).** No S2/S4 short fired within ±2 bars of the 09:30 cross. The first aligned shorts — BEAR_FLAG_SHORT + REACTIVE_SHORT — did not print until **10:20–10:25**, ~50 minutes and ~36 pts later, essentially at the 10:45 leg bottom (7440 vs the 7476 flip). **97% of that leg's range was already gone before any short pattern confirmed.** A pattern-gated strategy waits for a fire that arrives only after the move is over; the LSMA flip itself was the timely signal.

---

## (d) Conclusion — which patterns confirm the LSMA, which fight it

On 2026-06-23 (a Normal day), the **reliable trend-confirmers** — patterns whose fire direction matched the LSMA side and made money — were **FAMIR (+$113), ZLR (+$66), and BEAR_FLAG_SHORT (+$45)**, plus REACTIVE_SHORT which was directionally right on 4 of 5 fires (its book is only red because of a single −$266 outlier at 10:25). The clear **LSMA-fighters to filter out** are **HFE (3 fires, all SHORT into an ABOVE/long market, −$143)** and **TLB (SHORT above the LSMA, −$124)** — both fired counter-trend in the 08:55–09:15 opening drive and lost on every fire; **REACTIVE_LONG** also fought (long below the LSMA, −$90) and was the high-volume bait into the day's worst leg. The deeper finding for the flip strategy specifically: the S2/S4 fires are **mis-timed relative to the LSMA crosses** — 4 of 5 flips have no aligned fire, and those four unconfirmed flips are exactly the +$1,845 of winners, so **requiring pattern confirmation would have cost −$1,830 and left only the one losing trade.** Net: keep the raw LSMA-flip rule unfiltered on Normal days; use the patterns (best: FAMIR/ZLR/REACTIVE_SHORT in agreement) as a *trend-side veto* to drop counter-LSMA HFE/TLB/REACTIVE_LONG fires, **not** as an entry gate on the flip.
