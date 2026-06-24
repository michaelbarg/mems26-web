# P&L Backtest BY DAY-TYPE — current corrected #68 stack (read-only)

**Date run:** 2026-06-22 · **Author:** Cowork agent · **Scope:** 11 RTH days (2026-06-05 … 06-19)
**Status:** READ-ONLY. No trading code, `.env`, or DB modified. Sim flags set **in-process only**:
`DAYTYPE_POSITION_GATE=1`, `DAYTYPE_TARGETS_STRUCTURAL=1`, `DAYTYPE_PLAYBOOK=1`.

This re-runs the same approach as `SIM_NEW_STACK_2026-06-21.md` but **fresh**, after the
**Neutral location-gate fix** (Neutral_Center / Neutral_Extreme are now SHORT-only above POC,
LONG-only below POC — no longer "both sides all day"). The fix is **confirmed live in the module**:
the prior run blocked **0** trades on Neutral days; this run blocks **18**.

## What this simulates (real modules — no reimplementation)

For each actually-fired setup in `v9_trades`:

1. **Day-type** per day — `GET /api/v9/day_type/classify_replay` → `final.day_type`
   (`Normal_Variation`→`Variation`).
2. **Direction gate** — `backend.v9.systems.daytype_position_gate.decide(...)` → ALLOW / BLOCK.
3. **Structural 3-contract targets** — `backend.v9.systems.structural_targets.resolve_structural_targets(...)`;
   returns `None` → fall back to fixed-R (T1/T2/T3 = 1R/2R/3R).
4. **Forward 3-contract management** on that day's 5-min bars (`v9_bars_5min_woodies`, ts > entry):
   C1→t1 then stop→BE · C2→t2 · C3 trails (hwm∓1R, floor BE) or →t3 · **all contracts stop out on
   the protective stop (checked first within a bar)** · any contract still open at session end is
   **marked-to-last-close**. **$5/pt/contract (MES), 1 contract each (C1/C2/C3).** True initial risk =
   `cross_context[0].metadata.stop_initial` (NOT the trailed `stop` column).

## Results BY DAY-TYPE

### (a) ALL 11 DAYS

| day-type | #days | #trades | #blocked | new-stack net $ | actual net $ | Δ $ |
|----------|------:|--------:|---------:|----------------:|-------------:|----:|
| Neutral_Center  | 2 | 36 | 18 |   −505.00 | −1,181.60 |   +676.60 |
| Neutral_Extreme | 1 |  0 |  0 |      0.00 |      0.00 |      0.00 |
| Normal          | 1 | 26 | 13 |   +980.00 |    −56.30 | +1,036.30 |
| Trend_DD        | 2 | 30 | 11 | +5,528.75 |   −657.63 | +6,186.38 |
| Trend_Normal    | 1 |  3 |  0 | +1,616.25 |   +316.88 | +1,299.37 |
| Variation       | 4 | 64 | 11 | +6,210.00 | −1,168.30 | +7,378.30 |
| **GRAND TOTAL** | **11** | **159** | **53** | **+13,830.00** | **−2,746.95** | **+16,576.95** |

### (b) CLEAN-TPO DAYS ONLY — excludes 06-05 / 06-09 / 06-15 (POC outside IB) + out-of-range entries

| day-type | #days | #trades | #blocked | new-stack net $ | actual net $ | Δ $ |
|----------|------:|--------:|---------:|----------------:|-------------:|----:|
| Neutral_Center  | 1 | 34 | 17 | −2,160.00 | −1,764.10 |   −395.90 |
| Neutral_Extreme | 1 |  0 |  0 |      0.00 |      0.00 |      0.00 |
| Normal          | 1 | 26 | 13 |   +980.00 |    −56.30 | +1,036.30 |
| Trend_DD        | 2 | 30 | 11 | +5,528.75 |   −657.63 | +6,186.38 |
| Variation       | 3 | 38 |  3 | +6,608.75 |   −773.85 | +7,382.60 |
| **CLEAN-TPO TOTAL** | **8** | **128** | **44** | **+10,957.50** | **−3,251.88** | **+14,209.38** |

### (c) FULLY-CLEAN — most defensible cut (excludes contaminated-TPO **and** roll days 06-09…06-12)

Days: **06-08, 06-16, 06-17, 06-18, 06-19.**

| day-type | #days | #trades | #blocked | new-stack net $ | actual net $ | Δ $ |
|----------|------:|--------:|---------:|----------------:|-------------:|----:|
| Neutral_Extreme | 1 |  0 |  0 |      0.00 |      0.00 |      0.00 |
| Normal          | 1 | 26 | 13 |   +980.00 |    −56.30 | +1,036.30 |
| Trend_DD        | 2 | 30 | 11 | +5,528.75 |   −657.63 | +6,186.38 |
| Variation       | 1 | 12 |  0 |   −476.25 |   −373.10 |   −103.15 |
| **FULLY-CLEAN TOTAL** | **5** | **68** | **24** | **+6,032.50** | **−1,087.03** | **+7,119.53** |

> **The +Δ is concentrated in two days.** Of the headline figure, **06-16 (Trend_DD) = +$6,186** and
> **06-12 (Variation) = +$7,460** account for essentially all of it. 06-12 is roll-contaminated and the
> single most optimism-inflated day (actual −$329.50 → sim +$7,130). Even the FULLY-CLEAN +$7,120 Δ is
> **+$6,186 from the one clean trend day (06-16)** — strip that and the remaining four clean days net
> roughly +$934 sim Δ. **Direction of the result is favorable; the magnitude rests on one trend day.**

**Contract hit counts (allowed+simulated, 104 sim trades):** C1 = 50 · C2 = 24 · C3 = 5.
**Target resolution:** 98 structural · 6 fixed-R fallback (structural returned `None` → correct fail-safe).

## Blocked cohort — the gate skipped a NET-LOSING set

**53 setups BLOCKED · combined ACTUAL P&L = −$2,049.53** (−$2,063.03 on clean-TPO days). The gate
removed losers, not winners. Breakdown of the new **Neutral location-gate** (the fix this run validates):

- **18 Neutral_Center trades now blocked** (prior run: 0). Example (06-11, POC=7303.25):
  `SHORT entry=7297.50 < POC` and `LONG entry=7308.50 > POC` → both wrong-side-of-value, blocked.
- 06-16 (Trend_DD, downtrend) blocked **11** counter-trend LONGs; 06-18 (Normal) blocked **13**
  wrong-side-of-POC trades; 06-15 (Variation) blocked **8** against-expansion trades.

## Per-day appendix

| date | day-type | #tr | #blk | #OOR | struct/fixR | sim net $ | actual net $ | Δ $ | data flag |
|------|----------|----:|-----:|-----:|:-----------:|----------:|-------------:|----:|-----------|
| 06-05 | Trend_Normal    |  3 |  0 | 0 | 3/0  | +1,616.25 |   +316.88 | +1,299.37 | 🔴 POC outside IB; 38 bars |
| 06-08 | Neutral_Extreme |  0 |  0 | 0 | 0/0  |      0.00 |      0.00 |      0.00 | no fires |
| 06-09 | Neutral_Center  |  2 |  1 | 0 | 1/0  | +1,655.00 |   +582.50 | +1,072.50 | 🔴 POC outside IB + roll |
| 06-10 | Variation       |  3 |  1 | 0 | 2/0  |    −45.00 |    −71.25 |    +26.25 | roll |
| 06-11 | Neutral_Center  | 34 | 17 | 0 | 17/0 | −2,160.00 | −1,764.10 |   −395.90 | roll; **sim worse** (chop) |
| 06-12 | Variation       | 23 |  2 | 2 | 19/0 | +7,130.00 |   −329.50 | +7,459.50 | roll; **most optimistic** |
| 06-15 | Variation       | 26 |  8 | 0 | 15/3 |   −398.75 |   −394.45 |     −4.30 | 🔴 POC outside IB; sim≈actual |
| 06-16 | Trend_DD        | 30 | 11 | 0 | 19/0 | +5,528.75 |   −657.63 | +6,186.38 | clean; trend runner edge |
| 06-17 | Trend_DD        |  0 |  0 | 0 | 0/0  |      0.00 |      0.00 |      0.00 | no CASH TPO; no fires |
| 06-18 | Normal          | 26 | 13 | 0 | 10/3 |   +980.00 |    −56.30 | +1,036.30 | clean; 13 wrong-side blocked |
| 06-19 | Variation       | 12 |  0 | 0 | 12/0 |   −476.25 |   −373.10 |   −103.15 | clean; 0 targets hit |

🔴 = contaminated TPO (POC outside IB). "roll" = roll-contaminated bars per project rule (06-09…06-12).
OOR = entry outside the day's bar price range → ALLOWED by gate but **excluded from sim P&L** (2 total, both 06-12).

## 🔴 DATA QUALITY (verified against DB)

- **Contaminated TPO (POC sits OUTSIDE the IB → geometrically impossible):** **06-05** (poc 7430.75 vs IB
  7505.75–7552.75), **06-09** (poc 7355.25 vs IB 7390.75–7417.0), **06-15** (poc 7628.5 vs IB
  7598.25–7622.5). Gate/management on these is unreliable; quarantined in cut (b)/(c). **All other 8 days
  have POC inside IB** (verified — no additional contaminated day).
- **Roll-contaminated (partial/synthetic bars):** **06-09 … 06-12.** Note 06-12's bars are now scale-
  consistent (only 2/23 entries out of range, vs the prior run's 15/23) — re-ingested — but it remains a
  roll day and is the dominant, least-trustworthy delta. Quarantined in cut (c).
- **Out-of-range entries excluded from sim:** 2 (06-12 id=65 @7377.5, id=66 @7385.25, below bar low 7389.5).
- **06-17 has no CASH TPO row** and no fires → flat, no gate exercised.

## Caveats — state these whenever the numbers are quoted

- **Optimistic 5-min / zero-slippage fill model → UPPER BOUND, not a forecast.** Within a bar the
  protective stop is checked first (conservative), but favorable target/trail fills are granted whenever a
  bar's range touches the level, with **zero slippage/commission**, and **any contract still open at
  session end is marked-to-last-close**. This is what inflates the trend/continuation days: e.g. 06-16
  id=116 SHORT 7629.25 — C1 booked at t1=7587.5 (min low reached 7577.75 ✓), but C2/C3 never hit t2=7563
  and were **marked-to-close at 7584.5** for +44.75 pts each. Mechanically correct; optimistic.
- **CVD is NOT in the gate's direction.** The new `direction_context` drives **DISPLAY only**; the gate
  decides on day-type + price-vs-structure (IB/VA/POC) exactly like live. The sim cannot model any future
  CVD-based direction filter.
- **No chop veto is active** (both chop gates standing-OFF). On **06-11 (Neutral_Center chop day)** the sim
  is **worse than actual** (−$2,160 vs −$1,764) even after the location fix — fading the correct edge to
  structure still bleeds with no follow-through. This is the most important counter-evidence.
- **session_high/low are bar-derived approximations** (max-high / min-low of the day's 5-min bars up to
  each entry), used only by the Trend breakout-state — close to, but not identical to, the live TPO feed.
- **CASH TPO row used** (latest id per date), matching the `classify_replay` rule; affects POC/VAH/VAL and
  therefore both gate and targets.
- **Small single-day samples**, single contract-roll window, 6 of 11 days <30 fires, 3 days flat. The
  pattern token passed to `decide()` is informational (the gate branches on day-type/direction/price, not
  pattern). Do not over-fit.

## Bottom line

After the Neutral location-gate fix, the corrected #68 stack would have **improved** these 11 days on every
aggregation, chiefly by (1) **blocking a −$2,050 net-losing cohort** of wrong-side / counter-trend / wrong-
side-of-value trades — including **18 newly-blocked Neutral trades** the prior version let through — and (2)
holding with-trend runners to structural targets on the one clean trend day (06-16). But the **+$16.6k (all)
/ +$14.2k (clean-TPO) / +$7.1k (fully-clean) headline deltas are an upper bound, not a P&L estimate:** they
are dominated by 06-16 (+$6.2k) and the roll-contaminated 06-12 (+$7.5k, the most fill-inflated day), the
5-min/zero-slippage/mark-to-close fills are optimistic, and the stack still **bleeds on the one chop day
(06-11)** where no chop veto exists. Honest read: **shape is encouraging, magnitude unproven — the
Neutral fix is doing real work, but the dollar figure leans on a single trend day and needs a chop guard
before the structural-fade days can be trusted.**

---
*Evidence: per-day, per-trade JSON and traces produced read-only from `postgresql://localhost/mems26`
via the real `daytype_position_gate` / `structural_targets` modules + `classify_replay` endpoint. POC-inside-
IB, bar-range, and stop_initial paths verified directly against the DB. No code, `.env`, or DB row was
modified.*
