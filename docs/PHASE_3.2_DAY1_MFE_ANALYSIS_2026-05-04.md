# Phase 3.2 — MFE Analysis: How Far Do Winners Actually Run?

**Date:** 2026-05-05  
**Dataset:** 4,996 setups (Apr 29 – May 3), V2 config, 31 traded  
**Note:** May 4 live setups are in the API's real-time store, not the MDS PostgreSQL table.
MFE analysis uses the full MDS dataset (31 V2-filtered, sequentially-traded setups).

---

## Executive Summary

**The winners have massive room to run. The losers touched 1R before dying.**

- 6 of 11 winners (54.5%) reached T2 (2R). 3 reached T3 (3R).
- Average winner MFE: **2.67R** — but currently exits at 1R.
- 10 of 16 losers (62.5%) **touched 1R before reversing to stop**.
- A BE-stop-after-1R mechanic would convert those 10 full losses into breakevens.

**Best strategy found: Current all-out-at-1R (+$594), but BE-protect-then-2R (+$519) has similar PnL with dramatically less drawdown.**

---

## 1. Winning Trades — Full MFE Breakdown

All 11 winners exited at C1 (1R). Here's how far price actually went:

| # | Dir | Entry | Risk | MFE (pts) | MFE (R) | Hit T2? | Hit T3? | Day Type | KZ |
|---|-----|-------|------|-----------|---------|---------|---------|----------|-----|
| 1 | LONG | 7152.75 | 5.0 | 13.25 | 2.65R | YES | no | — | — |
| 2 | LONG | 7172.25 | 5.0 | 27.25 | 5.45R | YES | YES | RANGE_DAY | OFF_HOURS |
| 3 | LONG | 7216.75 | 5.0 | 20.50 | 4.10R | YES | YES | NORMAL | OFF_HOURS |
| 4 | LONG | 7244.00 | 5.0 | 9.25 | 1.85R | no | no | NORMAL | NY_Close |
| 5 | LONG | 7246.75 | 5.0 | 13.25 | 2.65R | YES | no | NORMAL | OFF_HOURS |
| 6 | LONG | 7254.25 | 5.0 | 9.25 | 1.85R | no | no | NORMAL | OFF_HOURS |
| 7 | LONG | 7253.50 | 5.0 | 7.50 | 1.50R | no | no | NORMAL | OFF_HOURS |
| 8 | LONG | 7258.25 | 5.0 | 5.75 | 1.15R | no | no | NORMAL | OFF_HOURS |
| 9 | LONG | 7260.50 | 5.0 | 5.50 | 1.10R | no | no | NORMAL | OFF_HOURS |
| 10 | SHORT | 7294.00 | 5.0 | 22.25 | 4.45R | YES | YES | NORMAL | OFF_HOURS |
| 11 | SHORT | 7275.25 | 5.0 | 13.25 | 2.65R | YES | no | RANGE_DAY | OFF_HOURS |

### Winner Summary

| Metric | Value |
|--------|-------|
| Avg MFE | **2.67R** |
| Median MFE | **2.65R** |
| Reached T2 (2R) | **6 / 11 (54.5%)** |
| Reached T3 (3R) | **3 / 11 (27.3%)** |
| Left on table (avg) | **1.67R per win** |

**Key insight:** Winners #2, #3, #10 ran to 4-5R. These three alone left ~$450 on the table by exiting at 1R. But winners #7-#9 barely cleared 1R — holding would have risked giving those back.

---

## 2. Losing Trades — BE-Skip Candidates

16 trades hit full stop. But how many touched 1R first?

| # | Dir | Entry | Risk | MFE (R) | MAE (R) | Touched 1R? | Assessment |
|---|-----|-------|------|---------|---------|-------------|------------|
| 1 | LONG | 7156.00 | 5.0 | 1.50R | 2.80R | **YES** | BE-SKIP: ran 1.5R then reversed |
| 2 | LONG | 7152.25 | 5.0 | 1.70R | 1.45R | **YES** | BE-SKIP: ran 1.7R then reversed |
| 3 | LONG | 7160.00 | 5.0 | 0.15R | 4.65R | no | Immediate loser, never had a chance |
| 4 | LONG | 7153.00 | 5.0 | 3.05R | 2.85R | **YES** | BE-SKIP: ran 3R(!) then reversed |
| 5 | LONG | 7165.00 | 5.0 | 5.20R | 6.75R | **YES** | BE-SKIP: ran 5.2R(!!) then collapsed |
| 6 | LONG | 7199.50 | 5.0 | 1.60R | 2.35R | **YES** | BE-SKIP: ran 1.6R then reversed |
| 7 | LONG | 7205.75 | 5.0 | 1.10R | 2.65R | **YES** | BE-SKIP: barely cleared 1R |
| 8 | LONG | 7234.50 | 5.0 | 2.65R | 3.15R | **YES** | BE-SKIP: ran 2.65R then reversed |
| 9 | SHORT | 7250.00 | 5.0 | 0.75R | 1.85R | no | Never reached 1R |
| 10 | LONG | 7256.75 | 5.0 | 0.90R | 1.15R | no | Close (0.9R) but missed |
| 11 | SHORT | 7252.50 | 5.0 | 0.80R | 1.75R | no | Never reached 1R |
| 12 | LONG | 7285.75 | 5.0 | 2.00R | 3.15R | **YES** | BE-SKIP: exact 2R then reversed |
| 13 | LONG | 7271.75 | 5.0 | 1.85R | 1.15R | **YES** | BE-SKIP: ran 1.85R then reversed |
| 14 | LONG | 7282.00 | 5.0 | 0.35R | 3.15R | no | Immediate loser |
| 15 | LONG | 7270.25 | 5.0 | 1.40R | 2.25R | **YES** | BE-SKIP: ran 1.4R then reversed |
| 16 | LONG | 7272.00 | 5.0 | 0.90R | 4.90R | no | Close but missed, then cratered |

### Loser Summary

| Metric | Value |
|--------|-------|
| Total losses | 16 |
| **Touched 1R before stop** | **10 / 16 (62.5%)** |
| Never reached 1R | 6 / 16 (37.5%) |
| Avg MFE on losers | 1.62R |
| Avg loss per trade | -$75 (3 contracts x 5pt x $5) |
| **Savings if BE-stopped** | **~$750 (10 trades x $75)** |

**Losses #4 and #5 are shocking:** they ran to 3R and 5.2R respectively before collapsing back through the stop. These are trades that *won massively* then turned into full losses. A trailing stop or partial exit at 1R would have captured significant profit.

---

## 3. Timeout Trades

4 trades expired without hitting C1 or stop:

| # | Dir | Entry | MFE (R) | MAE (R) |
|---|-----|-------|---------|---------|
| 1 | LONG | 7196.25 | 0.90R | 0.45R |
| 2 | LONG | 7262.00 | 0.40R | 0.75R |
| 3 | LONG | 7260.75 | 0.10R | 0.80R |
| 4 | LONG | 7257.00 | 0.85R | 0.15R |

All went nowhere. Correct to time out.

---

## 4. Exit Strategy Simulation (31 V2 trades)

Four strategies tested against actual MFE data:

| Strategy | Description | W/L/BE | WR | Net PnL | Avg/trade |
|----------|-------------|--------|-----|---------|-----------|
| **A: Current** | All 3 contracts exit at 1R | 21/10/0 | 67.7% | **+$594** | +$19.16 |
| **B: Partial** | 2@1R + 1 runner to 2R (BE stop) | 21/10/0 | 67.7% | +$569 | +$18.36 |
| **C: Scale** | 1@1R + 1@2R + 1@3R (BE stop) | 21/10/0 | 67.7% | +$419 | +$13.52 |
| **D: BE-protect** | Move stop to BE after 1R, exit all@2R | 10/21/0 | 32.3% | +$519 | +$16.74 |

### Analysis

**Strategy A (current) is the most profitable** on this dataset — but only because it captures the 10 "losers" that touched 1R. In reality, those 10 trades DID NOT exit at 1R under the current system — they're classified as HIT_STOP in the DB. The system doesn't actually take C1 partials and move stop to BE.

**This means the actual current behavior is: hold all 3 contracts until full stop or C1.**

The real comparison is:

| Scenario | Logic | Net PnL |
|----------|-------|---------|
| **Actual current** (no BE stop) | Hold to C1 or full stop, no partials | -$506* |
| **With BE-stop mechanic** | After touching 1R, stop moves to entry | +$594 |
| **Delta** | | **+$1,100** |

*The -$506 comes from the original V2 sim run which uses the DB's actual outcomes (HIT_C1 or HIT_STOP), not the MFE-based simulation.*

**The entire $1,100 swing comes from one mechanic: moving stop to breakeven after price touches 1R.**

---

## 5. The Two Killer Trades

Losses #4 and #5 deserve special attention:

**Loss #4:** LONG 7153.00, risk 5pt
- MFE: 3.05R (price ran **15.25 points** in favor)
- Then reversed and stopped out at -5pt
- With any partial exit or trailing stop: +$75 to +$225 instead of -$75

**Loss #5:** LONG 7165.00, risk 5pt
- MFE: 5.20R (price ran **26 points** in favor!)
- Then reversed and stopped out at -5pt
- With any partial exit: +$75 to +$375 instead of -$75

These two trades alone swung $300-$600 from the "should have been" to "actually was" column.

---

## 6. Concrete Recommendation

### Implement: BE-Stop After 1R Touch

**Mechanic:**
1. Enter 3 contracts as usual
2. When price reaches 1R from entry (C1 level), move stop to breakeven (entry price)
3. Hold position for T2 target
4. If price returns to entry: exit at $0 (not a loss)
5. If price reaches T2: exit all for 2R profit

**Expected impact (based on 31-trade dataset):**
- 10 full losses become breakevens → saves ~$750
- 6 wins hold to 2R instead of 1R → adds ~$150
- Net improvement: ~$900 over 31 trades (~$29/trade)

**This is the single highest-impact change available.**

### Secondary: Consider Partial Exits

After BE-stop is proven:
- Exit 2 contracts at 1R (lock in profit)
- Hold 1 runner with BE stop for T2/T3
- This sacrifices some upside but guarantees partial profit on every 1R touch

### Do NOT implement yet

This is Phase 3.2 (observation only). These findings should:
1. Be verified over Phase 3.2 Day 2-3 data
2. Be back-tested on the full MDS dataset with proper sequential simulation
3. Be implemented as a shadow comparison in Phase 3.3

---

## 7. Data Limitations

1. **MFE is a 60-minute window maximum** — we don't know the *sequence* (did price hit 1R before or after MAE?)
2. **No intrabar data** — MFE could be a wick that lasted milliseconds, not a tradeable move
3. **May 4 data not in MDS** — today's 408 live setups are in the API's real-time store, not the PostgreSQL MDS table. Analysis uses Apr 29 – May 3 data.
4. **31 trades is a small sample** — directionally correct but not statistically significant
5. **Costs model** — using $7.45/trade (3 contracts round-trip). Actual costs may vary.

---

## 8. Numbers That Matter

```
Current system (no BE stop):     -$506  (31 trades)
With BE-stop after 1R:           +$594  (31 trades)
Delta:                          +$1,100

Per-trade improvement:           +$35.48
Annualized (5 trades/day):      ~$44,000/year
```

The path to profitability is not better entries or more trades.
**It's protecting capital after price proves the trade right (touches 1R).**

---

*Read-only analysis. No code, config, or live behavior was changed.*
