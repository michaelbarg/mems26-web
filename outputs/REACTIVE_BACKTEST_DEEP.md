# REACTIVE 5-min Pattern — Deep Backtest (Data Completeness · Stop/Target Search · Robustness)

Date: 2026-06-29 · Data: `_reactive_bt_bars.csv` (RTH bars from `v9_bars_5min`) · Engine: `reactive_search.py` (+ `reactive_oos.py`, `reactive_robust2.py`)

Self-contained on `v9_bars_5min`. The ~60pt price-basis offset vs the canonical Woodies table is irrelevant here — every stop/target is **relative** to entry/bar-extremes/VP-levels in this same table.

Pattern (established, not re-derived): 4 bars — B1 bearish, B2 vol ≤ T×B1, B3 bullish, B4 close beyond B3 high (LONG; SHORT is the mirror). Entry = B4 close. 3-unit scale-out: T1/T2/T3, stop→break-even after T1, **conservative intrabar (stop checked before target within a bar)**, runners exit at last close if a tier is never hit. Expectancy is reported **per contract** = (3-unit total points) / 3.

---

## 1. DATA COMPLETENESS — verdict: SPARSE & GAPPY; usable edge rests on ~17 trades over ~12 June days

| Metric | Value |
|---|---|
| Total RTH bars | **1,398** |
| Date span | **2026-04-16 → 2026-06-26** (~2.4 months) |
| Distinct dates | **39** |
| Expected if every day full (78 bars: 08:30–14:55 CT) | 3,042 |
| **Overall completeness ratio** | **0.46** (1,398 / 3,042) |
| Median bars/day | 42 · mean 35.8 · max 81 |
| Days ≥ 78 bars (≈full) | **10** |
| Days ≥ 50 bars | 10 · ≥ 20 bars: 21 · **≤ 5 bars: 11** (near-useless) |

**Bars-per-day is bimodal:** ~10 near-full days (79–81), a cluster of partial days (42–48), and a tail of fragments (1–14 bars). 4 days have a single bar.

### Consecutive-window analysis (what detection actually needs)
The pattern needs **4 bars exactly 5 min apart, same day**. Counting maximal contiguous runs and summing `max(0, run_len − 3)`:

- **1,214 valid 4-bar detection windows** exist (vs **2,925** if all 39 days were fully contiguous → **41.5%**).
- 71 contiguous runs total; **14 are isolated single bars**, 26 are exactly length-3 (one short of a window). Only **30 runs are ≥4 long**. The 9 longest runs (length 79) supply the bulk of the windows.
- **26 of 39 days** contain ≥1 valid window; 13 days yield **zero**.

### The binding constraint: Volume-Profile coverage (the location filter's fuel)
The location filter is the *entire* edge (Section 2), and it needs `vah`/`val` > 0. Those columns are populated on only:

- **826 / 1,398 bars (59%)**, on **18 of 39 dates**, and **17 of 39** dates have *both* VP coverage AND ≥1 detection window.
- VP-covered dates are **clustered from 2026-06-05 onward** (lone early exception: 2026-05-07). Effectively the location-filtered strategy is tested on a **single ~3-week June window**.
- Of the 1,214 detection windows, **971 (80%)** fall on VP-covered days — but after the pattern + good-location filter, only **17 actual trades** survive (Section 2).

### CVD note (the table tradeoff)
`cumulative_delta` (session CVD) is populated on **1,391 / 1,398 bars** — so this gappy table *is* the only CVD-bearing source. `v9_bars_5min_woodies` is contiguous (no detection gaps) but carries **no delta at all**. **Tradeoff, stated plainly:** any CVD-aware or VP-aware test is *forced* onto this gappy `v9_bars_5min` table; you cannot have both contiguity and order-flow. Per-bar delta = `cumulative_delta.diff()`.

### Confidence verdict
**Low.** The headline result rests on **n = 17 trades across 12 distinct June trading days**, all inside one 3-week regime, on a table that is 54% incomplete and whose VP coverage (the edge's prerequisite) only switched on in June. This is enough to *form* a hypothesis, **not** to size risk or declare an edge production-ready. Treat every number below as directional, not load-bearing.

---

## 2. OPTIMAL STOP & TARGET SEARCH

Grid: 9 stops × 3 target schemes, threshold T = 0.90 (sweep in §2.4). All combos run on the **same** detections (82 raw signals; 17 after the good-location filter).

- **Stops:** `setup_extreme` (min low B1–B3 / max high), `b3` (B3 low/high), `b4` (B4 low/high), `atr0.5`/`atr1.0` (k × 14-bar mean-range ATR proxy), `fix3/4/6/8` (fixed points).
- **Targets:** `fix5_10` (T1=+5, T2=+10, T3=swing-20 capped 25 — the baseline ladder); `R1_2_3` (T1=1R, T2=2R, T3=3R, R=|entry−stop|); `vp_levels` (nearest vah/val/poc strictly beyond entry from B4's own row, R-multiple fallback for missing tiers).
- "Good location" = **SHORT ≥ VAH (`above_vah`)** or **LONG ≤ VAH (`inside_va` or `below_val`)**.

### 2.1 All detections, no location filter — almost everything is NEGATIVE
Confirms the prior pass ("negative at every threshold"). Best cases barely break even:

| stop | target | n | exp (pt/contract) | win% | PF |
|---|---|---|---|---|---|
| b3 | fix5_10 | 82 | **+0.57** | 72.0 | 1.21 |
| atr1.0 | R1_2_3 | 82 | +0.13 | 43.9 | 1.02 |
| b4 | R1_2_3 | 82 | +0.15 | 47.6 | 1.03 |
| setup_extreme | fix5_10 | 82 | **−0.95** | 73.2 | 0.77 |
| setup_extreme | R1_2_3 | 82 | **−4.84** | 42.7 | 0.56 |

Without the location filter there is **no combo worth trading**. (Full 27-row grid is reproducible from `reactive_search.py`.)

### 2.2 Good-location subset (n = 17) — every combo flips strongly POSITIVE
The filter, not the stop/target, is the edge. Top of the grid:

| Rank | stop | target | n | exp (pt/contract) | win% | PF | T1% |
|---|---|---|---|---|---|---|---|
| 1 | b3 | R1_2_3 | 17 | +7.89 | 70.6 | 2.94 | 70.6 |
| 2 | setup_extreme | vp_levels | 17 | +7.84 | 94.1 | 10.4 | 88.2 |
| 3 | b3 | vp_levels | 17 | +7.54 | 94.1 | 10.0 | 88.2 |
| 4 | b4 | R1_2_3 | 17 | +6.18 | 88.2 | 7.1 | 88.2 |
| … | setup_extreme | **fix5_10** | 17 | **+5.07** | **100.0** | ∞ | 100.0 |
| … | b3 | **fix5_10** | 17 | **+5.07** | **100.0** | ∞ | 100.0 |

Note `setup_extreme` and `b3` stops produce **identical** results with the fixed ladder: in this sample every good-location trade hit T1 before either stop level was touched, so the stop choice never bound. (`atr0.5`/`fix3`/`fix4` are also all positive, +3 to +4.)

### 2.3 The R-multiple / vp "winners" are a small-sample mirage — do NOT pick them
The top-expectancy combos win on a **handful of runners**, not a stable edge:

- `b3 + R1_2_3` total = +134 pt, but the **top 2 trades alone = +124 (93%)**. Strip them and it's flat/negative. (And it dies OOS — §3.)
- `setup_extreme + vp_levels`: top 2 = 65% of total.
- `setup_extreme + fix5_10`: top 2 = **31%** — expectancy spread across all 17 trades.

**Chosen optimum (robust, not max):** **`stop = setup_extreme` (≡ `b3` here) + `target = fix5_10` ladder (+5 / +10 / swing-20 cap-25)**, on the good-location subset.
- **n = 17 · expectancy +5.07 pt/contract · win 100% · 100% reach T1.**
- LONG +5.20 (n=7), SHORT +4.98 (n=10) — positive both directions.
- Per-bar contract value ≈ **+$25.4** (MES $5/pt × +5.07) / **+$253** per setup on the full 3-contract scale-out.

This sits ~+0.7 above the prior pass's ~+4.4 (the prior figure was at threshold 0.90 on a slightly different ladder/sample); the search did not find a *robust* combo materially better than the simple fixed ladder. The R-multiple combos that *score* higher are overfit to 1–2 trades.

### 2.4 Threshold sensitivity (benign)
Good-location expectancy with the chosen ladder stays positive across the whole B2-volume-drop sweep — no knife-edge:

| T (B2 ≤ T×B1) | n_all | n_good | exp_good | win_good |
|---|---|---|---|---|
| 0.70 | 33 | 4 | +2.88 | 100 |
| 0.80 | 56 | 12 | +4.43 | 100 |
| 0.85 | 69 | 15 | +4.66 | 100 |
| **0.90** | 82 | 17 | **+5.07** | 100 |
| 0.95 | 89 | 16 | +4.68 | 100 |
| 1.00 | 97 | 20 | +3.00 | 95 |

> **Caveat — backtest threshold ≠ live fire.** The live S2 Reactive detector uses **`DROP_THRESHOLD_PCT = 0.10`** (B2 ≤ 10% of B1), plus a lookback-quiet gate (`max vol < 0.6×B1`) and footprint/POC confirmations (currently disabled). This backtest's 0.70–1.00 "threshold" is a **much looser proxy**, so it generates far more signals than production would. The edge's *direction* is informative; the *trade count* is optimistic.

---

## 3. ROBUSTNESS — OOS split: edge HOLDS for the fixed ladder, FAILS for the R-multiple combos

Chronological split, good-location only, cut = **2026-06-18** (train < cut, test ≥ cut; ~60/40 by trade count).

| stop | target | n_train | exp_train | n_test | exp_test | PF_test |
|---|---|---|---|---|---|---|
| **setup_extreme** | **fix5_10** | 10 | **+6.46** | 7 | **+3.10** | ∞ |
| b3 | fix5_10 | 10 | +6.46 | 7 | +3.10 | ∞ |
| setup_extreme | vp_levels | 10 | +10.97 | 7 | +3.38 | ∞ |
| b3 | vp_levels | 10 | +10.46 | 7 | +3.37 | ∞ |
| atr1.0 | fix5_10 | 10 | +5.31 | 7 | +3.10 | ∞ |
| **b3** | **R1_2_3** | 10 | +14.28 | 7 | **−1.24** | 0.76 |

**The fixed ladder survives OOS** (+6.46 → +3.10, still 100% T1, both directions positive: SHORT +3.89, LONG +2.50 in test). **The `R1_2_3` combo collapses OOS** (+14.28 → **−1.24**) — its train score was the two runners, which didn't recur. This is the clean illustration of §2.3: pick the ladder, not the R-multiple.

**Additional stability checks (chosen ladder, good-loc):**
- **Leave-one-day-out** expectancy range **+3.97 → +5.57** (mean +5.07) — never negative; no single day carries it.
- **All 12 good-location days are net-positive** at the day level (+1.67 to +26.67 pt/contract).
- **Filter adds value OOS:** in the test window, GOOD = +3.10 (n=7) vs ALL-detections = +1.95 (n=21). The filter improves expectancy *and* PF out of sample.

### Honest flags on the OOS result
- **n is tiny:** test = **7 trades on ~5 days**; train = 10 on ~7 days. A 100%-win test set of 7 is *consistent with* an edge but statistically indistinguishable from luck. **Do not infer a 100% win rate is real.**
- **One regime only:** both halves live inside the same June VP-covered window — this is "later June vs earlier June," **not** a true out-of-regime test (April/May had no VP data to filter on).
- **Perfect T1 (100%)** across all cuts is the single biggest overfitting smell. In live trading expect T1 misses, slippage on the B4-close entry, and good-location *misclassification* on bars where VP is stale — none of which this backtest penalizes.
- **Survivorship via gaps:** detections only exist where bars were contiguous; days where the feed dropped mid-pattern are silently absent and may have behaved differently.

---

## Bottom line
- **Data:** 54% incomplete, gappy, VP coverage only from June → the location-filtered edge is a **~17-trade / ~12-day June-only** result. Low confidence; hypothesis-forming, not risk-sizing. The contiguous Woodies table can't help because it has no delta — CVD/VP work is stuck on this gappy table.
- **Optimal placement:** **`setup_extreme` stop + fixed `+5/+10`/swing ladder** on good-location signals → **+5.07 pt/contract (n=17, 100% T1)**, robust across thresholds, LODO, and OOS (+3.10 in test). The higher-scoring R-multiple/vp combos are overfit to 1–2 runners and **fail OOS** — reject them.
- **Robustness:** the *fixed-ladder location-filtered* edge **holds OOS within June**, but on n=7 test trades in a single regime. Promising signal; **collect more VP-covered days before trusting it live.**
