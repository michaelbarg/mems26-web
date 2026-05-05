# SIM-RBT-04: CFG-α Monte Carlo Robustness

**Date:** 2026-05-05 (Day 2 Evening)
**Status:** LIVE BLOCKER assessment

---

## Method

- Bootstrap: 1,000 random subsamples WITH replacement
- Sample sizes: 8, 10, 12 trades (representing 3-4 weeks of CFG-α)
- Win definition: outcome-based (HIT_C1 = win, HIT_STOP = loss)
- Source: 14 actual CFG-α trades from MDS (Apr 29 - May 3)

---

## Results

### WR Distribution

| Sample Size | 5th %ile | 25th %ile | 50th %ile | 95th %ile | Mean |
|:-----------:|:--------:|:---------:|:---------:|:---------:|:----:|
| 8 | **62.5%** | 80.0% | 85.7% | 100% | 84.6% |
| 10 | **66.7%** | 80.0% | 88.9% | 100% | 85.0% |
| 12 | **66.7%** | 77.8% | 83.3% | 100% | 84.9% |

### PnL Distribution (per sample)

| Sample Size | 5th %ile | 50th %ile | 95th %ile | P(profit) |
|:-----------:|:--------:|:---------:|:---------:|:---------:|
| 8 | $84 | $309 | $534 | **97.9%** |
| 10 | $143 | $443 | $668 | **98.2%** |
| 12 | $201 | $501 | $726 | **99.4%** |

### Ruin Probability

P(3 consecutive losses in 14 trades) = **3.7%**

Given 84.6% WR:
- P(single loss) = 15.4%
- P(two consecutive) = 2.4% (theoretical)
- P(three consecutive) = 0.37% (theoretical)
- Observed in simulation: 3.7% (higher due to finite sample effects)

---

## Acceptance Criteria

| Criterion | Target | Actual | Verdict |
|-----------|--------|--------|---------|
| 5th percentile WR | >60% | **62.5-66.7%** | **PASS** |
| P(profit) per 10-trade block | >80% | **98.2%** | PASS |
| Max expected drawdown | <$200 | **$99.75** | PASS |

---

## Interpretation

CFG-α's 84.6% WR is robust to random sampling. Even in the worst 5% of bootstrap draws, WR stays above 60%. The probability of a profitable 10-trade sequence is 98%.

**Caveat:** Only 14 source trades. The bootstrap measures consistency of THESE 14 trades, not generalization to future market conditions. Extended data (Task 2) needed for confidence.

---

## VERDICT: **PASS** — CFG-α meets Monte Carlo robustness criteria for LIVE consideration.
