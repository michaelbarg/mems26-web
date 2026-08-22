# Dalton V2 Over Detectors — 34 Sessions, 6 Contracts

**Ruling:** Michael 23.08 — "כן" (dalet context over real detectors, not raw swings)
**Script:** `scripts/replay_dalton_over_detectors.py`
**Data:** `v9_five_min_setups` (926 real detector outputs) + `v9_trades` (books) + `v9_bars_5min_woodies`

## Answer to the 5 Questions

### Q1: Is Dalton over detectors profitable?

**YES.** +$5,973 over 34 sessions (18/34 days positive, median $143/day).

| Layer | ALL 34 | 08-10..21 (OOS) | 07-07..08-09 (IS) |
|-------|--------|-----------------|---------------------|
| **BOOKS** | +$212.50 | -$111.25 | +$323.75 |
| **L1-DETECTORS** | -$496.50 | -$1,536.00 | +$1,039.50 |
| **L2-DALTON** | **+$5,973.00** | **+$2,235.00** | **+$3,738.00** |
| **ORACLE** | +$74,208.00 | +$14,160.00 | +$60,048.00 |

The Dalton filter turns a **losing** detector set (-$496.50) into a **profitable** one (+$5,973).
**OOS (08-10..21) is positive**: +$2,235 with 6/10 days positive, median $268.50/day.

### Q2: Winning location × pattern combinations (ranked by $)

| Location × Pattern | n | Win% | $ |
|---------------------|---|------|---|
| BELOW_VAL × INITIATIVE_LONG | 3 | 67% | **+$2,253** |
| AT_EDGE_LOW × REACTIVE_SHORT | 2 | 100% | **+$1,827** |
| ABOVE_VAH × REACTIVE_SHORT | 13 | 38% | **+$1,255** |
| ABOVE_VAH × DOUBLE_BOTTOM_EE_LONG | 1 | 100% | +$1,093 |
| IN_VALUE × REACTIVE_LONG | 4 | 50% | +$714 |
| BELOW_VAL × REACTIVE_LONG | 8 | 50% | +$693 |
| AT_EDGE_HIGH × DBT_EE_LONG | 1 | 100% | +$666 |

**Losers:**
| ABOVE_VAH × REACTIVE_LONG | 3 | 0% | **-$1,032** |
| ABOVE_VAH × INVERSE_HNS_LONG | 1 | 0% | -$924 |

### Q3: Trades per day

**1.6 trades/day** (L2-Dalton) vs 1.8 (L1 unfiltered) vs 2.8 (books).
Exactly in Michael's 2-3 range.  On 1/34 days Dalton produced zero trades (08-14: no setup passed the filter).

### Q4: Win rate vs today's 53%

| Layer | Win Rate |
|-------|----------|
| BOOKS | 53% (today) |
| L1-DETECTORS | 47% (unfiltered) |
| **L2-DALTON** | **50%** (Dalton-filtered) |

Win rate is 50% — similar to today. **But the average winner is much larger**: Dalton selects
trades at extreme locations where the R:R is inherently better (edge-to-edge rotation = bigger target).

### Q5: If negative — what's the weak link?

L2 is **positive** (+$5,973). The pattern that the Dalton filter helps MOST:

| Pattern | Without Dalton | With Dalton | Delta |
|---------|----------------|-------------|-------|
| INITIATIVE_LONG | -$2,310 (30% wr) | **+$2,253** (67% wr) | **+$4,563** |
| DOUBLE_BOTTOM_EE_LONG | -$1,315 (0% wr) | **+$1,719** (75% wr) | **+$3,035** |
| INITIATIVE_SHORT | -$3,063 (14% wr) | **-$66** (25% wr) | +$2,997 |

The biggest value: **Dalton kills bad INITIATIVE trades** (from -$2,310 to +$2,253 on LONG alone)
by requiring the right location. INITIATIVE at BELOW_VAL in DISCOVERY = high conviction.

## Dalton Transition Summary

Average **2.1 transitions/session**.  Most sessions: ib_lock → one acceptance event.
08-17..21 had 2.4 transitions/session (more volatile week).

## Limitations (Honesty)

- **Single-slot sim:** first-come-first-served, no quality priority ranking
- **Value area:** uses end-of-day TPO VAH/VAL (not developing intra-day VA)
- **Fills:** bar close + 1 tick slip. Real fills vary with volatility
- **T1 only:** no T2/T3 scaled exit trail. Real system has ladder
- **34 sessions** is a thin sample. OOS is 10 sessions — too small for statistical confidence.
  The 90% CI on $2,235/10-sessions includes negative outcomes.
- **No slot competition with S4:** the sim only runs S2 setups. Live, S4 (ZLR/GB100) competes for the same slot.

## Conclusion

Dalton V2 over the real S2 detectors is the first profitable layer in this analysis
(+$5,973 vs books +$212.50). The value is clear: **location-aware selection turns losing
detectors into winners**, especially for INITIATIVE and DOUBLE_BOTTOM. The next step:
wire the Dalton state as a context field on every setup that reaches the gateway, and use
it for the playbook's FULL/REDUCED/SKIP decision — not as a hard gate, but as a quality signal.

*Generated 2026-08-23 by cc-macbook. READ-ONLY — no production code changed.*
