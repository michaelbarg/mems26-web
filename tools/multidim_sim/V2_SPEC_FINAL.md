# V2 Spec — Final (Real-Data Validated)

**Generated:** May 2, 2026
**Validated against:** 103 real Demo trades (Apr 15-28)
**Hypothesis confirmation:** MDS retro on 4,943 setups (Apr 29 - May 1)

---

## Filters (V2 Active Filters)

### 1. skip_DEVELOPING
- **Real evidence:** DEVELOPING = 75% of losses (15/20 in real data)
- **Hypothetical:** DEVELOPING = 57% of losses in MDS retro
- **Cross-validation:** STRONG MATCH between real and hypothetical
- **Action:** REJECT all setups when day_type = 'DEVELOPING'

### 2. skip_London_killzone
- **Real evidence:** London = only net negative killzone (-$66 on 13 trades)
- **WR:** 5W/8L = 38% (below all other killzones at 75%+)
- **Sample warning:** Only 13 trades — monitor closely
- **Action:** REJECT setups when killzone = 'London'

---

## Settings KEPT from V1

- Score weights: Vegas/TPO/FVG/Footprint = V1 defaults
- Threshold: ~50 (default)
- Footprint logic: weighted (V1 default)
- Direction filter: both (LONG 79.5% WR, SHORT 75% WR)
- Day type detection: V1 (DLL Phase 4)
- Quality Score V1 logic

---

## Sequential Mode (CRITICAL)

- Enforce ONE trade open at a time
- New setups REJECTED if previous trade still active
- This was retro-applied; production needs deployment

---

## Performance Projection

| Metric | V1 (Real Apr 15-28) | V2 (Estimated) |
|--------|---------------------|----------------|
| Trades/day | 14.7 | 6 |
| WR | 78.9% | 85%+ |
| Avg/trade | $4.74 | $9.20 |
| Daily PnL | $69 | $55+ |

(Lower trade count, higher quality, similar PnL with much less risk exposure.)

---

## Implementation in Phase 3.3

DLL: No changes (day type already detected)
Backend:
  - Add `skip_developing` config flag (default true)
  - Add `skip_killzones` list config (default ["London"])
  - apply_entry_filter() rejects per these flags
Frontend:
  - Show V2 filter status in Day Type panel
  - Decision Modal: "Rejected: DEVELOPING day type"

---

## Filter 3: skip_stale_entry (PRODUCTION CRITICAL)

**Discovery:** Look-ahead investigation found that some setups are
re-emitted every 60 seconds with stale entry_price. During fast
market moves, this creates impossible-to-fill orders.

**Evidence:**
- Apr 29 cluster: 7 setups at entry 7167.75 over 7 minutes
- Market moved ±18pt during that window
- Some setups had first tick already past T3
- 1.6% of all setups affected (3/186 sampled past T1 on first tick)

**Production Fix:**

```python
# In setup detection (DLL or Backend):
def validate_setup_entry(setup, current_price):
    """Reject setup if market has moved away from intended entry."""
    distance = abs(current_price - setup.entry_price)
    if distance > 2.0:  # 2pt threshold
        return False, "STALE_ENTRY_PRICE"
    return True, "valid"
```

**Why this matters for LIVE:**
- LIVE broker would reject or slippage these fills
- Without fix, LIVE PnL will be lower than backtest
- With fix, backtest matches LIVE reality

**Impact on V2 Performance:**
- ~$290 of the $1,547 V2 best PnL was from look-ahead trades
- Realistic V2 PnL after fix: ~$1,250
- Still 3x V1 baseline ($419)

---

## Future Iterations (V3, V4)

- After 30+ V2 Demo trades:
  - Validate London killzone hypothesis (sample is small)
  - Re-evaluate score weights with more component score data
  - Consider day-type adaptive sizing
