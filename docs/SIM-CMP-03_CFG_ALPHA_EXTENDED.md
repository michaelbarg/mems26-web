# SIM-CMP-03: CFG-α Extended Backtest

**Date:** 2026-05-05 (Day 2 Evening)
**Status:** LIVE BLOCKER assessment

---

## Data Availability

| Source | Status | Coverage |
|--------|--------|----------|
| MDS Parquet (full) | Available | Apr 29 - May 3 (5 days) |
| SCID files | Not found | N/A |
| Additional parquets | May 2 copy (subset) | Redundant |

**Limitation:** Only 5 trading days available. 30+ days needed for 100-trade target.

---

## Results

### CFG-α Performance (Sequential, Outcome-Based)

| Metric | Value |
|--------|-------|
| Period | 5 days (Apr 29 - May 3) |
| Total trades | **14** |
| Wins | 11 |
| Losses | 2 |
| Timeouts | 1 |
| WR (decisive) | **84.6%** |
| Net PnL | **+$559.50** |
| Avg/trade | +$39.96 |
| Trades/day | 2.8 |
| Max Drawdown | $99.75 |
| Sharpe (daily) | 2.74 |

### Per-Day Breakdown

| Date | Trades | W | L | WR | Net PnL |
|------|--------|---|---|-----|---------|
| Apr 29 | 4 | 4 | 0 | 100% | +$267.00 |
| Apr 30 | 6 | 4 | 2 | 67% | +$100.50 |
| May 1 | 4 | 3 | 0 | 100% | +$192.00 |
| May 3 | 0 | - | - | - | $0 |

**Note:** May 3 had 0 CFG-α trades (weekend data, only 244 setups total).

### No Losing Days

All 3 active trading days were profitable. Worst day (Apr 30) still net positive despite 2 losses.

---

## Acceptance Criteria

| Criterion | Target | Actual | Verdict |
|-----------|--------|--------|---------|
| WR | ≥70% | **84.6%** | **PASS** |
| Trade count | >100 | **14** | **FAIL** |
| Consecutive profitable days | ≥5 | 3 (of 3 active) | Incomplete |

---

## Projection to 100 Trades

At 2.8 trades/day:
- Need ~36 trading days for 100 trades
- Projected dates: requires data through June 15

At current WR (84.6%):
- Expected: 85 wins, 15 losses over 100 trades
- Expected PnL: ~$4,000 (at $40/trade average)
- 95% CI on WR (binomial): 57-96% (wide due to small N)

---

## Risk Factors

1. **Small sample:** 14 trades is statistically weak. True WR could be anywhere from 57-96%.
2. **No bad-day data:** May 1 (DEVELOPING-heavy) produced 0 losses for CFG-α, but this may be luck.
3. **Market regime:** All 5 days were in one market regime. Regime change untested.
4. **Sequential dependency:** 2.8 trades/day assumes proper one-at-a-time enforcement.

---

## VERDICT: **CONDITIONAL PASS**

- WR criterion: PASS (84.6% >> 70%)
- Volume criterion: FAIL (14 << 100)
- Recommendation: **Proceed to shadow LIVE with real-time tracking. Accumulate to 50+ trades before full LIVE sizing.**
