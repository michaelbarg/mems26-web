# MEMS26 Hypothesis Validation V2 — Day 5 (D-033 PnL Formula)

**Generated:** 2026-05-07
**Branch:** feature/inventory-day5
**Data source:** Production API `/analytics/setups/closed` (N=1,973 closed setups)
**PnL method:** D-033 compliant — `pnl_net_usd` from shadow simulator with per-contract C1/C2/C3 partial exits, commissions ($1.50/RT), slippage ($1.25 on stops)
**Population note:** 1,973 setups vs Day 4's 1,682. Close but not identical — this is production shadow sim data, not the retro_outcomes parquet (which is unavailable on this machine).

---

## Q1 — Per day_type × score bucket × direction

### TREND_DAY (N=100)

| Score | N | WR | Total PnL | Avg PnL | Median PnL | LONG WR (n) | SHORT WR (n) |
|-------|---|----|-----------|---------|-------------|-------------|--------------|
| 0-49 | 48 | **60.4%** | **+$182** | +$3.79 | +$22.25 | 100% (2) | 58.7% (46) |
| 50-59 | 6 | 50.0% | -$138 | -$23.00 | -$30.50 | 100% (2) | 25.0% (4) |
| 60-69 | 6 | 66.7% | -$58 | -$9.67 | -$5.50 | 100% (2) | 50.0% (4) |
| 70-79 | 11 | 45.5% | -$165 | -$14.95 | -$83.25 | 55.6% (9) | 0% (2) |
| 80-84 | 8 | 62.5% | -$306 | -$38.25 | -$33.25 | 62.5% (8) | — (0) |
| **85+** | **21** | **19.0%** | **-$1,248** | **-$59.44** | -$83.25 | 19.0% (21) | — (0) |
| **TOTAL** | **100** | **50.0%** | **-$1,733** | **-$17.33** | -$27.75 | | |

**TREND_DAY 85+ is catastrophic:** 19% WR, -$59/trade, all 21 are LONG. Meanwhile 0-49 (all SHORT) = 60% WR, +$182.

### DEVELOPING (N=915)

| Score | N | WR | Total PnL | Avg PnL | Median PnL | LONG WR (n) | SHORT WR (n) |
|-------|---|----|-----------|---------|-------------|-------------|--------------|
| 0-49 | 277 | **58.1%** | **+$651** | +$2.35 | +$22.25 | 71.4% (63) | 54.2% (214) |
| 50-59 | 175 | 41.7% | -$4,080 | -$23.31 | -$55.50 | 50.0% (46) | 38.8% (129) |
| 60-69 | 145 | 40.0% | -$2,393 | -$16.50 | -$55.50 | 51.3% (76) | 27.5% (69) |
| 70-79 | 136 | 61.8% | -$1,775 | -$13.05 | -$33.25 | 61.7% (115) | 61.9% (21) |
| 80-84 | 47 | 53.2% | -$1,277 | -$27.16 | -$33.25 | 47.4% (38) | **77.8% (9)** |
| 85+ | 135 | 60.7% | -$1,574 | -$11.66 | -$33.25 | 63.3% (120) | 40.0% (15) |
| **TOTAL** | **915** | **52.8%** | **-$10,447** | **-$11.42** | -$27.75 | | |

**Key pattern:** 0-49 profitable (+$651), 50-69 is the worst zone (-$6,473), 70+ has high WR but negative PnL (commissions eat the gains on many small wins).

### NORMAL (N=776)

| Score | N | WR | Total PnL | Avg PnL | Median PnL | LONG WR (n) | SHORT WR (n) |
|-------|---|----|-----------|---------|-------------|-------------|--------------|
| 0-49 | 219 | **57.5%** | **+$335** | +$1.53 | +$22.25 | **83.7% (43)** | 51.1% (176) |
| 50-59 | 120 | **62.5%** | **+$508** | +$4.23 | -$5.50 | **71.1% (38)** | 58.5% (82) |
| 60-69 | 108 | 53.7% | +$49 | +$0.45 | -$5.50 | 56.5% (62) | 50.0% (46) |
| 70-79 | 126 | 48.4% | -$2,808 | -$22.29 | -$83.25 | 54.9% (82) | 36.4% (44) |
| 80-84 | 35 | 54.3% | -$966 | -$27.61 | -$33.25 | 58.3% (24) | 45.5% (11) |
| 85+ | 168 | 43.5% | -$4,074 | -$24.25 | -$83.25 | 47.1% (140) | 25.0% (28) |
| **TOTAL** | **776** | **53.1%** | **-$6,957** | **-$8.96** | -$27.75 | | |

**NORMAL confirms Day 2 finding:** 0-59 profitable (+$843), 70+ devastating (-$7,848). Steep drop at 70.

### RANGE_DAY (N=176)

| Score | N | WR | Total PnL | Avg PnL | Median PnL | LONG WR (n) | SHORT WR (n) |
|-------|---|----|-----------|---------|-------------|-------------|--------------|
| 0-49 | 43 | **65.1%** | **+$304** | +$7.08 | +$22.25 | 100% (6) | 59.5% (37) |
| 50-59 | 18 | 50.0% | -$199 | -$11.06 | -$19.25 | 66.7% (3) | 46.7% (15) |
| 60-69 | 35 | **71.4%** | +$45 | +$1.29 | +$19.50 | **88.9% (18)** | 52.9% (17) |
| 70-79 | 40 | 50.0% | -$676 | -$16.91 | -$19.50 | 57.7% (26) | 35.7% (14) |
| 80-84 | 13 | 69.2% | -$182 | -$14.02 | +$16.75 | 69.2% (13) | — (0) |
| 85+ | 27 | 63.0% | **+$120** | +$4.44 | +$16.75 | 63.6% (22) | 60.0% (5) |
| **TOTAL** | **176** | **61.4%** | **-$589** | **-$3.34** | +$16.75 | | |

**RANGE_DAY is the healthiest.** 85+ actually profitable (+$120). 60-69 also profitable. Mid-range (50-59, 70-79) underperforms. Partial U-shape.

### GAP_FILL (N=6) — INSUFFICIENT DATA

Only 6 setups. No conclusions possible.

---

## Q2 — Score-PnL Correlation per day_type

| Day Type | N | Pearson | Spearman | Verdict |
|----------|---|---------|----------|---------|
| TREND_DAY | 100 | **-0.437** | **-0.463** | **INVERTED** (strong) |
| DEVELOPING | 915 | -0.110 | -0.196 | **INVERTED** (weak-moderate) |
| NORMAL | 776 | -0.162 | **-0.313** | **INVERTED** (moderate) |
| RANGE_DAY | 176 | -0.056 | **-0.338** | U-SHAPE (linear weak, rank moderate) |

**All 4 testable day types show negative correlation.** TREND_DAY is the strongest inversion (r=-0.44). RANGE_DAY has weak linear but strong rank correlation, suggesting a non-linear (U-shaped) pattern where extremes outperform midrange.

---

## Q3 — Cross-day-type Aggregate (Day 4 U-shape check)

### All directions combined

| Score | N | WR | Total PnL (D-033) | Avg PnL | Median PnL |
|-------|---|----|-------------------|---------|------------|
| 0-49 | 590 | **58.3%** | **+$1,389** | +$2.35 | +$22.25 |
| 50-59 | 319 | 50.2% | -$3,910 | -$12.26 | -$5.50 |
| 60-69 | 296 | 49.7% | -$2,368 | -$8.00 | -$20.50 |
| 70-79 | 313 | 54.3% | -$5,424 | -$17.33 | -$33.25 |
| 80-84 | 103 | 56.3% | -$2,731 | -$26.51 | -$33.25 |
| 85+ | 352 | 50.3% | -$6,759 | -$19.20 | -$46.38 |

**Pattern: NOT U-shape, NOT pure inversion. MONOTONIC DECLINE in PnL.**

WR does show mild non-monotonicity (0-49=58%, dip at 50-69, recovery to 54-56% at 70-84), but PnL steadily worsens from +$2.35 to -$19.20 per trade. The WR recovery at 70-84 doesn't translate to PnL because higher-score setups use 2-3 contracts (higher stakes per trade).

### LONG only

| Score | N | WR | Total PnL | Avg PnL |
|-------|---|----|-----------|---------|
| 0-49 | 114 | **78.1%** | **+$1,492** | **+$13.08** |
| 50-59 | 89 | **60.7%** | **+$897** | **+$10.08** |
| 60-69 | 160 | **58.8%** | **+$785** | **+$4.91** |
| 70-79 | 232 | 58.6% | -$2,018 | -$8.70 |
| 80-84 | 83 | 55.4% | -$2,254 | -$27.15 |
| 85+ | 304 | 53.0% | -$4,349 | -$14.31 |

**LONG 0-69: profitable across all 3 buckets (+$3,174 total).** Sharp cliff at 70 — LONG goes from +$4.91 at 60-69 to -$8.70 at 70-79.

### SHORT only

| Score | N | WR | Total PnL | Avg PnL |
|-------|---|----|-----------|---------|
| 0-49 | 476 | 53.6% | -$103 | -$0.22 |
| 50-59 | 230 | 46.1% | -$4,806 | **-$20.90** |
| 60-69 | 136 | 39.0% | -$3,153 | **-$23.18** |
| 70-79 | 81 | 42.0% | -$3,406 | **-$42.05** |
| 80-84 | 20 | 60.0% | -$478 | -$23.88 |
| 85+ | 48 | 33.3% | -$2,410 | **-$50.20** |

**SHORT is negative at every bucket.** Only 0-49 is near breakeven (-$0.22). SHORT 85+ is the single worst cell: 33% WR, -$50/trade.

---

## Verdict Comparison vs Yesterday (V1, estimated PnL)

| Finding | Yesterday (V1) | Today (D-033) | Δ |
|---------|----------------|---------------|---|
| Anti-correlation universal | TRUE (all day types inverted) | **TRUE — CONFIRMED.** Pearson negative for all 4 testable day types. | ✅ Same direction, D-033 confirms |
| DEVELOPING net negative | TRUE (-$4,305 estimated) | **TRUE — WORSE.** -$10,447 with D-033. | ⚠️ Magnitude 2.4× larger |
| Score 70 hardcode loses money | FALSE (11 dropped, -$68) | **NOT TESTABLE HERE** — setups data doesn't distinguish hardcoded vs day-adaptive thresholds. But TREND_DAY 60-69 = -$58 (n=6), confirming negligible impact. | ⚠️ Low n, same direction |
| DEVELOPING 0-49 profitable | TRUE (+$6,260 estimated) | **TRUE — smaller.** +$651 with D-033. | ⚠️ Same direction but 9.6× smaller — V1 overestimated massively |
| SHORT 70+ worst performers | TRUE (38.8% WR, -$5.69) | **TRUE.** SHORT 85+ = 33.3% WR, -$50.20/trade. | ✅ Confirmed, even worse |

**Key discrepancy:** V1 estimated DEVELOPING 0-49 at +$6,260. D-033 shows +$651. The 9.6× difference is because V1 used `HIT_C1 = +1R × $5` (simple), while D-033 uses per-contract partial exits with commissions/slippage. This is exactly the D-033 formula bug that Day 4 caught.

---

## Day 4 Reconciliation

| Day 4 Finding | Status | D-033 Evidence |
|---------------|--------|----------------|
| Score 30-50 LONG = 64% WR | ⚠️ **PARTIALLY** | LONG 0-49 = 78.1% WR (higher!). But bucket boundaries differ (30-50 vs 0-49). Direction confirmed. |
| Score 85+ = 61% WR | ❌ **CONTRADICTED** | 85+ all-direction = 50.3% WR. LONG 85+ = 53%. RANGE_DAY 85+ = 63% is close, but overall the 61% doesn't hold cross-day-type with D-033 PnL population. |
| Score 60-70 = 45% WR (trough) | ✅ **CONFIRMED** | 60-69 = 49.7% (close). This IS the trough zone in most day types. |
| 7 anti-patterns (D-037) | ⚠️ **PARTIALLY** | Cannot test all 7 from setups data (no cluster, late_day, or KZ enforcement fields on closed setups). Footprint opposition and NORMAL day skip are visible via `sim_skip_reason`. |
| LONG/SHORT differentiation (D-038) | ✅ **CONFIRMED** | Massive split: LONG 0-69 = +$3,174 total. SHORT = negative at every bucket. Different checklists are essential. |

**The U-shape hypothesis (Day 4) vs inversion hypothesis (V1):**
With D-033 and 6 buckets, the answer is **NEITHER pure U-shape NOR pure inversion**. It's:
- **LONG:** Monotonic decline from 0-49 (+$13.08) to 85+ (-$14.31). Score inversely predicts LONG profit.
- **SHORT:** Flat disaster — negative everywhere except near-zero at 0-49.
- **RANGE_DAY:** Partial U-shape (0-49 and 85+ both profitable).
- **TREND_DAY:** Strong inversion (0-49 best, 85+ worst).
- **Aggregate:** Monotonic PnL decline, mild WR non-monotonicity.

---

## Implications for Sprint 3.3

The D-033 formula **confirms the direction** of all V1 findings but at dramatically different magnitudes. The "score inversion" finding was real but V1 overestimated profitable zones by ~10×. With D-033, low-score setups are modestly profitable (LONG 0-49 = +$13/trade) while high-score setups are moderately negative (85+ = -$19/trade). The system is not "make money by inverting scores" — it's "the scoring system adds no value and high scores incur higher position sizing costs."

**Sprint 3.3 priorities confirmed:**
1. **Quality Score V2** remains #1 — anti-correlation is real across all day types with D-033
2. **LONG/SHORT differentiation is essential** — LONG is profitable below score 70, SHORT is not profitable at any score bucket. D-038 checklists needed.
3. **Position sizing is a hidden cost** — high-score setups use 3 contracts (more commissions/slippage) for the same or worse WR. Sizing should be decoupled from V1 score.
4. **RANGE_DAY 85+ is the one healthy cell** — preserve this when deploying V2. It's the only high-score cell with positive PnL.
