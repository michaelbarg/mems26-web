# SIM — NEW #68 Stack vs ACTUAL (read-only historical simulation)

**Date run:** 2026-06-21 · **Author:** Cowork agent · **Scope:** 11 RTH days (2026-06-05 … 06-19)
**Status:** READ-ONLY. No trading code, `.env`, or DB modified. Sim flags set in-process only:
`DAYTYPE_POSITION_GATE=1`, `DAYTYPE_TARGETS_STRUCTURAL=1`, `DAYTYPE_PLAYBOOK=1`.

## What this simulates

For each actually-fired setup in `v9_trades`, apply the NEW #68 logic using the **real modules**
(no reimplementation):

1. **Day-type** per day — `GET /api/v9/day_type/classify_replay` → `final.day_type`
   (`Normal_Variation`→`Variation`).
2. **Direction gate** — `backend.v9.systems.daytype_position_gate.decide(...)` → ALLOW/BLOCK.
3. **3-contract structural targets** — `backend.v9.systems.structural_targets.resolve_structural_targets(...)`
   (falls back to fixed-R T1/T2/T3 = 1R/2R/3R when it returns None).
4. **Forward 3-contract management** on that day's 5-min bars (`v9_bars_5min_woodies`):
   C1→t1 (then stop→BE), C2→t2, C3 trails (hwm∓1R, floor BE) or →t3; all stop out on the
   protective stop. 1 contract each, **$5/pt/contract** (MES). True initial risk =
   `cross_context[0].metadata.stop_initial` (NOT the trailed `stop` column).

## Per-day result

| date | day_type | #setups | #blocked | new-sim net $ | actual net $ | Δ ($) | notes |
|------|----------|--------:|---------:|--------------:|-------------:|------:|-------|
| 2026-06-05 | Trend_Normal    |  3 |  0 |  +1,148.44 |   +316.88 |  +831.56 | roll/partial (38 bars); C1×3 |
| 2026-06-08 | Neutral_Extreme |  0 |  0 |       0.00 |      0.00 |     0.00 | no fires |
| 2026-06-09 | Neutral_Center  |  2 |  0 |  +2,138.75 |   +582.50 | +1,556.25 | roll day; 1 trade had 2.5-pt stop (R-artifact) |
| 2026-06-10 | Variation       |  3 |  1 |     -45.00 |    -71.25 |   +26.25 | roll/partial (46 bars); all 3 stops <5pt |
| 2026-06-11 | Neutral_Center  | 34 |  0 |  -3,193.75 | -1,764.10 | -1,429.65 | **sim WORSE** — chop day, structural targets repeatedly stopped |
| 2026-06-12 | Variation       | 23 |  2 |  +4,101.25 |   -329.50 | +4,430.75 | **UNRELIABLE** — 15/23 entries out of bar range (roll scale mismatch) |
| 2026-06-15 | Variation       | 26 |  8 |    -548.74 |   -394.45 |  -154.29 | clean; sim ≈ actual (both small losses) |
| 2026-06-16 | Trend_DD        | 30 | 11 |  +4,618.75 |   -657.63 | +5,276.38 | clean down-trend; gate blocked 11 counter-trend longs |
| 2026-06-17 | Trend_DD        |  0 |  0 |       0.00 |      0.00 |     0.00 | no fires |
| 2026-06-18 | Normal          | 26 | 13 |    +685.01 |    -56.30 |  +741.31 | clean; gate blocked 13 wrong-side trades |
| 2026-06-19 | Variation       | 12 |  0 |    -476.25 |   -373.10 |  -103.15 | clean (partial 42 bars); 0 targets hit |
| **TOTAL** | — | **159** | **35** | **+8,428.46** | **-2,746.95** | **+11,175.41** | see caveats |

**Sub-aggregates (honesty split):**

- **CLEAN full-session days** (06-11, 06-15, 06-16, 06-18, 06-19 — entries inside bar range):
  sim **+1,085.02** vs actual **-3,245.58** → Δ **+4,330.60**. Blocked-trade actual = **-1,708.03**.
- **ROLL / partial / scale-mismatch days** (06-05, 06-09, 06-10, 06-12):
  sim **+7,343.44** vs actual **+498.63** → Δ **+6,844.81**. **~81% of the headline Δ lives here and is not trustworthy.**
- **No-fire days** (06-08, 06-17): both flat.

**Contract hit counts (allowed+simulated trades):** C1 hits = 53 · C2 = 17 · C3 = 4.

## Key findings

1. **The direction gate skipped net-losing trades.** Across all days, **35 setups were BLOCKED**;
   their combined ACTUAL P&L was **-$1,581.98**. The gate removed a net-losing cohort, not winners.
   Most visible on the trend days: 06-16 (Trend_DD, downtrend) blocked 11 counter-trend LONGs whose
   actual results were mostly losses (e.g. -202.5, -191.25, -187.5, -172.5, -153.75); 06-18 (Normal)
   blocked 13 wrong-side-of-POC trades.

2. **Structural "hold-with-the-trend" management beats tiny scratch-targets on trend days.** On 06-16,
   actual trades booked tiny scratches (+$20…+$80) or small losses; the new stack held the surviving
   shorts toward Trend_DD structural targets (t1≈IBL−ext) as price fell 7636→7583, so the kept
   contracts ran. This is the intended #68 edge and it shows up clearly — but see caveat (a).

3. **The new stack is NOT uniformly better.** On **06-11 (Neutral_Center, a chop day)** the sim did
   **worse** (-$3,194 vs -$1,764 actual): the gate allows both sides on Neutral days, and structural
   targets to the opposite IB edge got stopped repeatedly in two-sided rotation. This is the most
   important counter-evidence — on balance days, "fade both edges to structure" bleeds when there is
   no follow-through, and there is currently **no chop veto** (both chop gates are standing-OFF).

4. **The headline +$11.2k Δ is dominated by unreliable days.** Removing the roll/scale-mismatch days,
   the clean-day Δ is **+$4.3k** — still favorable, but ~4× smaller, and itself driven mostly by the
   single 06-16 trend day. On a per-day basis the new stack helped on 5 days, hurt on 3, was flat on
   3. **Direction of the result is encouraging; the magnitude is an upper bound, not a forecast.**

5. **Fail-safe paths fired as designed.** `resolve_structural_targets` returned None (→ fixed-R
   fallback) on a meaningful share of Neutral_Center trades (e.g. 06-11: 17 structural / 17 fixed-R)
   when a structural target landed on the wrong side of entry — correct fail-safe, not a bug.

## Caveats (read before trusting any number)

- **(a) Optimistic fill model.** This is a 5-min-bar management/direction sim, **not tick-accurate**.
  Within a bar the protective stop is checked first (conservative), but favorable target fills and the
  profit-locking trail are otherwise granted whenever a bar's range reaches the level — with **zero
  slippage/commission**. On trend days this overstates the runner capture. Treat sim P&L as an
  **upper bound**.
- **(b) CVD is ignored in the fire-time direction.** Per the live system today, CVD feeds only the S1
  day-type classifier, **not** the direction gate. This sim's direction decisions therefore use only
  day-type + price-vs-structure (IB/VA/POC), exactly like live — but it means the sim cannot model any
  future CVD-based direction filter.
- **(c) session_high/low are bar-derived approximations.** The gate's Trend breakout-state uses
  `session_high/session_low` computed as max-high / min-low of the day's 5-min bars up to each entry
  (not the live TPO session extremes). Close, but not identical to the live feed.
- **(d) Multi-row TPO per day — CASH row used.** `v9_tpo_sessions` has multiple rows per date
  (e.g. 06-18: GLOBEX id=145 and CASH id=146). The sim uses the **`session_type='CASH'` row** (latest
  id), matching the `classify_replay` endpoint's own rule. This affects POC/VAH/VAL and therefore the
  gate + targets.
- **(e) Roll-day / partial-day data quality (06-05, 06-09, 06-10, 06-12).** Entry prices on some
  roll-affected days do **not** line up with the `v9_bars_5min_woodies` price scale or the CASH TPO
  levels (e.g. 06-12: 14/23 entries fell outside the day's bar range → marked `ENTRY_OUT_OF_BAR_RANGE`
  and **excluded** from sim P&L; 06-09: an entry at 7489 vs CASH IB 7390–7417). Days 06-05/06-10/06-12
  also have <60 RTH bars or scale gaps. **Their sim figures are not reliable** — quarantined in the
  ROLL sub-aggregate above.
- **(f) Tiny initial stops inflate $-per-trade indirectly.** Several trades carry a `stop_initial`
  within <5 pts of entry (06-10: 3/3, 06-19: 5/12, 06-16: 4/30). With far structural targets these
  produce very large R-multiples; the BE-move and trail then trigger almost immediately, making the
  trail capture generous. The $-amounts remain bounded by real price movement, but these trades
  amplify the sim's optimism.
- **(g) Nontrend handling.** None of the 11 days classified as `Nontrend`, so this gap was not
  exercised. For completeness: the live position gate does **not** block Nontrend (it returns
  fail-open / "playbook handles SKIP"), a known gap — had a Nontrend day appeared, the sim would have
  taken those trades, same as live.
- **(h) Pattern argument is informational.** `daytype_position_gate.decide()` branches only on
  day-type + direction + price, not on `pattern`; the pattern token passed is for the record only and
  does not change ALLOW/BLOCK.
- **(i) Small samples.** Single-day, single-contract-roll windows; 6 of 11 days have <30 fired
  setups and 2 have zero. Do not over-fit.

## Raw evidence (key commands)

Day-type per day (real endpoint):
```
$ curl -s -H "Authorization: Bearer ***" ".../day_type/classify_replay?date=2026-06-16" → final.day_type=Trend_DD
  06-05 Trend_Normal · 06-08 Neutral_Extreme · 06-09 Neutral_Center · 06-10 Normal_Variation(→Variation)
  06-11 Neutral_Center · 06-12 Normal_Variation · 06-15 Normal_Variation · 06-16 Trend_DD
  06-17 Trend_DD · 06-18 Normal · 06-19 Normal_Variation
```

Actual P&L per day (`v9_trades`):
```
SELECT count(*), sum(pnl_usd) FROM v9_trades WHERE entry_ts::date = :d
  06-05 n=3  +316.88 | 06-08 n=0 0 | 06-09 n=2 +582.50 | 06-10 n=3 -71.25
  06-11 n=34 -1764.10 | 06-12 n=23 -329.50 | 06-15 n=26 -394.45 | 06-16 n=30 -657.63
  06-17 n=0 0 | 06-18 n=26 -56.30 | 06-19 n=12 -373.10   → 11-day actual total = -2,746.95
```

TPO multi-row example (CASH row used):
```
SELECT session_type, ib_high, ib_low, poc_price, vah_price, val_price FROM v9_tpo_sessions WHERE trading_date='2026-06-18'
  GLOBEX  ibh=7581.75 ibl=7535.50 poc=7563.0 vah=7641.50 val=7489.25
  CASH    ibh=7581.75 ibl=7535.50 poc=7566.5 vah=7571.25 val=7564.00   ← used
```

Blocked-trade helpfulness (all days):
```
35 BLOCKED setups · combined ACTUAL pnl = -1,581.98  (negative ⇒ gate skipped a net-losing cohort)
```

Trace validating 06-16 id=116 (SHORT 7629.25, t1=7587.5): min low after entry = 7582.75 ⇒ t1 legitimately
reached; C1 booked at t1, C2/C3 exited on the profit-locking trail as price pulled back — mechanically
consistent with the bars.

## Bottom line

Directionally, the #68 stack would have **improved** these 11 days — chiefly by (1) blocking a
net-losing −$1.6k cohort of wrong-side / counter-trend trades and (2) holding with-trend runners to
structural targets on the one clean trend day (06-16). But the **+$11.2k headline Δ is not a credible
P&L estimate**: ~81% of it sits on roll/scale-mismatch days that the fill model can't represent, the
5-min/zero-slippage fills are optimistic, and the new logic demonstrably **bleeds on chop days**
(06-11) where no chop veto is active. Honest read: **encouraging shape, magnitude unproven** — the
clean-day Δ (+$4.3k, mostly one trend day) is the most defensible figure, and even that argues for
adding a chop/Neutral guard before leaning on the structural-fade days.
