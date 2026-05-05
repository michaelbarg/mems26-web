# MEMS26 — Tier R-Multiple Sizing Model

**Companion to:** `MEMS26_SIMULATION_REGISTRY_V3.1.md`
**Created:** Tuesday, 5 May 2026 (Phase 3.2 Day 2, evening)
**Status:** 📋 Spec ready for validation, then implementation in Phase 3.3
**Purpose:** Replace raw-contract sizing with risk-normalized sizing

---

## Why This Document Exists

V3.0 of the simulation registry proposed Tier sizing in raw contracts:
- Tier-S = 3 contracts
- Tier-A = 2 contracts
- Tier-B = 1 contract

External review identified this as **dangerous asymmetric risk**:

```
Scenario: 4 Tier-B winners @ 1 contract = +$80
          1 Tier-S loser  @ 3 contracts = -$120
          Net: -$40 despite 80% WR
```

This document specifies the corrected approach: **R-Multiple sizing where Tier defines RISK BUDGET, and contracts are derived from stop distance.**

---

## Table of Contents

1. [The Core Concept](#1-concept)
2. [Mathematical Formula](#2-formula)
3. [Day-Type Risk Adjustment](#3-day-type)
4. [Worked Examples](#4-examples)
5. [Daily Risk Cap (Safety)](#5-cap)
6. [Edge Cases & Special Rules](#6-edge-cases)
7. [Implementation Checklist](#7-implementation)
8. [Validation Plan](#8-validation)

---

<a name="1-concept"></a>
## 1. The Core Concept

### Old Way (Dangerous)
```
"Confidence = High → 3 contracts"
"Confidence = Low → 1 contract"

Problem: Stop distance varies but contract count doesn't.
         A 3-contract trade with 8pt stop risks 2.4x more
         than a 3-contract trade with 5pt stop.
         "High confidence" doesn't mean "I can lose more $".
```

### New Way (R-Multiple)
```
"Confidence = High → I'm willing to risk 1.5% of my account"
"Confidence = Low → I'm willing to risk 0.5% of my account"

Solution: Tier sets the risk budget.
          Stop distance determines how that budget translates to contracts.
          Risk per trade is constant within Tier.
          Position naturally scales with confidence AND volatility.
```

### Key Principle

```
TIER = "How much am I willing to lose if this is wrong?"
STOP = "How wrong does it need to go before I'm out?"
CONTRACTS = derived from above two
```

This is how professional traders size positions. We're aligning to industry standard.

---

<a name="2-formula"></a>
## 2. Mathematical Formula

### Step 1: Determine Tier from Confluence Score

```
confluence_score = sum(CONF-01..06 individual scores) / 6 * 100  # normalized 0-100

if confluence_score >= 90:
    tier = "S"
elif confluence_score >= 70:
    tier = "A"
elif confluence_score >= 50:
    tier = "B"
else:
    return REJECT  # confluence too low
```

### Step 2: Get Risk Budget for Tier (Day-Type Adjusted)

```python
RISK_PCT_BY_TIER_AND_DAY = {
    "TREND_DAY":   {"S": 2.0, "A": 1.5, "B": 1.0},
    "RANGE_DAY":   {"S": 1.0, "A": 0.5, "B": None},   # B skipped on RANGE
    "NORMAL":      {"S": 1.5, "A": 1.0, "B": 0.5},
    "GAP_FILL":    {"S": 1.5, "A": 1.0, "B": None},   # B skipped on GAP
    "DEVELOPING":  None,  # ALL TIERS REJECTED at entry
}

risk_pct = RISK_PCT_BY_TIER_AND_DAY[day_type][tier]
if risk_pct is None:
    return REJECT
```

### Step 3: Calculate Position Size

```python
# MES contract specs
TICK_VALUE = 5.0  # $5 per point per contract for MES
ACCOUNT_VALUE = current_account_balance  # from broker API

# Risk in dollars
account_risk_dollars = ACCOUNT_VALUE * (risk_pct / 100)

# Risk per contract (function of stop distance)
contract_risk_dollars = stop_distance_pts * TICK_VALUE

# Number of contracts (rounded down)
contracts = math.floor(account_risk_dollars / contract_risk_dollars)

# Safety: minimum 1, maximum 5
contracts = max(1, min(contracts, 5))

# Final risk check
actual_risk = contracts * contract_risk_dollars
if actual_risk > ACCOUNT_VALUE * 0.025:  # never risk more than 2.5%
    contracts = 1  # absolute floor
```

### Step 4: Final Validation

```python
if contracts == 0:
    return REJECT  # stop too wide for any contracts at this risk level

if actual_risk > daily_remaining_budget:
    return REJECT  # daily cap reached

return EXECUTE(contracts, stop_pts, targets)
```

---

<a name="3-day-type"></a>
## 3. Day-Type Risk Adjustment Rationale

### Why TREND_DAY allows higher risk
```
TREND_DAY = strongest edge (per Day Type Spec V2)
- Vegas stable
- Range > 0.7 ATR
- Pullbacks easy to identify
- Targets are wide (T2 = 3-4R)
- Statistical edge: 60%+ WR per plan

→ Higher conviction = higher acceptable risk
→ But still capped at 2.0% (can't blow account on one trade)
```

### Why RANGE_DAY restricts risk
```
RANGE_DAY = chop, no clear direction
- Vegas flipping
- Mean reversion only
- T2 narrow (POC/VWAP, ~2R)
- Higher false-positive rate

→ Lower conviction = lower acceptable risk
→ Tier-B skipped entirely (low confidence × chop = bad)
```

### Why DEVELOPING is fully rejected
```
DEVELOPING = lowest WR (38% per data)
- Validated through 75% of real losses occurring on DEVELOPING days
- Even Tier-S setups underperform here
- Not a sizing issue — entry shouldn't happen
```

### Why NORMAL is the baseline
```
NORMAL is the median day type.
All other day types adjust up (TREND/GAP) or down (RANGE) from this baseline.
This makes the model interpretable.
```

---

<a name="4-examples"></a>
## 4. Worked Examples

### Example 1: Tier-S on TREND_DAY, Tight Stop
```
Account:           $5,000
Day type:          TREND_DAY
Confluence score:  92 → Tier-S
Risk pct:          2.0%
Account risk $:    $5,000 × 2.0% = $100

Setup:
  entry: 7250
  stop:  7245 (5pt)
  
Contract risk $:   5 × $5 = $25
Contracts:         floor($100 / $25) = 4
Capped at:         min(4, 5) = 4 contracts
Actual risk:       4 × $25 = $100 ✓
Risk pct check:    $100 / $5,000 = 2.0% ✓

→ EXECUTE 4 contracts, stop 7245
```

### Example 2: Tier-S on TREND_DAY, Wider Stop
```
Account:           $5,000
Day type:          TREND_DAY
Confluence score:  92 → Tier-S
Risk pct:          2.0%
Account risk $:    $100

Setup:
  entry: 7250
  stop:  7242 (8pt)
  
Contract risk $:   8 × $5 = $40
Contracts:         floor($100 / $40) = 2
Actual risk:       2 × $40 = $80
Risk pct check:    $80 / $5,000 = 1.6% ✓ (below 2.0% target due to floor)

→ EXECUTE 2 contracts, stop 7242
   [Note: same Tier-S as example 1, but only 2 contracts due to wider stop]
```

### Example 3: Tier-A on NORMAL, Standard Stop
```
Account:           $5,000
Day type:          NORMAL
Confluence score:  78 → Tier-A
Risk pct:          1.0%
Account risk $:    $50

Setup:
  entry: 7250
  stop:  7245 (5pt)
  
Contract risk $:   5 × $5 = $25
Contracts:         floor($50 / $25) = 2
Actual risk:       2 × $25 = $50 ✓

→ EXECUTE 2 contracts, stop 7245
```

### Example 4: Tier-B on RANGE_DAY → Rejected
```
Account:           $5,000
Day type:          RANGE_DAY
Confluence score:  62 → Tier-B
Risk pct:          None (Tier-B skipped on RANGE)

→ REJECT (Tier-B not allowed on RANGE_DAY)
```

### Example 5: Wide Stop, Even Tier-S Limited
```
Account:           $5,000
Day type:          NORMAL
Confluence score:  91 → Tier-S
Risk pct:          1.5%
Account risk $:    $75

Setup:
  entry: 7250
  stop:  7235 (15pt — at the threshold)
  
Contract risk $:   15 × $5 = $75
Contracts:         floor($75 / $75) = 1
Actual risk:       1 × $75 = $75 ✓
Risk pct check:    $75 / $5,000 = 1.5% ✓

→ EXECUTE 1 contract, stop 7235
   [Note: floor of 1 contract — this is the MAX risk per Tier-S]
```

### Example 6: Stop Too Wide → Rejected by STOP-05
```
Account:           $5,000
Day type:          NORMAL
Confluence score:  91 → Tier-S
Risk pct:          1.5% → $75

Setup:
  entry: 7250
  structural_stop:  7232 (18pt!)
  ATR_5min × 1.2:   12pt
  
STOP-05 logic:    structural (18pt) > ATR×2 (24pt — but cap is 15pt absolute)
                  ATR×1.2 (12pt) used as fallback
                  Continue with 12pt stop

Contract risk $:   12 × $5 = $60
Contracts:         floor($75 / $60) = 1
Actual risk:       $60 ✓

→ EXECUTE 1 contract, stop using ATR fallback (12pt)
```

---

<a name="5-cap"></a>
## 5. Daily Risk Cap (Safety Net)

### The Hard Cap
```
MAX_DAILY_RISK_PCT = 3.0%  # never lose more than 3% account in one day
LIVE_DAILY_DOLLAR_CAP = $200  # absolute LIVE override (per memory)

cumulative_risk_today = sum of (contract_risk * contracts) for all today's trades

if cumulative_risk_today + new_trade_risk > min(MAX_DAILY_RISK_PCT × account, $200):
    REJECT new trade (cap reached)
```

### How This Interacts with Tiers

```
Account: $5,000
Daily cap: min(3% × $5000, $200) = min($150, $200) = $150

Trade 1: Tier-S, 5pt stop, 4 contracts → risk $100
Trade 2: Tier-A, 5pt stop, 2 contracts → risk $50
[Cumulative: $150 — at cap]

Trade 3: Any setup → REJECTED (daily cap reached)
```

### Why $200 LIVE Override

```
Per memory: "Daily cap: $200 max loss"

For LIVE Day 1 (small account, learning):
   Daily cap = $200 absolute
   This may be more restrictive than 3% rule
   Whichever is LOWER applies

This protects against scaling errors during early LIVE.
```

---

<a name="6-edge-cases"></a>
## 6. Edge Cases & Special Rules

### Edge Case 1: Account Balance Unknown/Stale
```
If account_value cannot be fetched:
   Use last known value
   If last known > 24h old:
      Default to conservative $5,000
   Log warning
```

### Edge Case 2: Stop = 0 or Negative
```
If stop_distance_pts <= 0:
   REJECT setup — invalid stop
```

### Edge Case 3: Risk Calculation < 1 Contract
```
If account_risk_dollars / contract_risk_dollars < 1.0:
   This means even 1 contract exceeds the risk budget
   
   Decision rule:
   - If exceeds budget by <50%: ALLOW with 1 contract (rounding up)
   - If exceeds budget by >50%: REJECT (stop is too wide for this Tier)
   
   Logic: small overage on tight setups is acceptable
          big overage = the Tier is wrong for this setup
```

### Edge Case 4: Active Trade in Progress
```
Per memory: "Sequential mode: required (one trade at a time)"

If any trade is currently OPEN:
   REJECT new setup (regardless of Tier)
   Wait for current trade to close
```

### Edge Case 5: Daily Trade Count Reached
```
Per memory: "Max trades: 5/day"

If daily_trade_count >= 5:
   REJECT all new setups
```

### Edge Case 6: Tier Boundary
```
Confluence score = 70 → Tier-A (boundary case)
Confluence score = 69 → Tier-B

This is intentionally sharp. No "fuzzy" tiers.
Clear boundaries make the system predictable.
```

---

<a name="7-implementation"></a>
## 7. Implementation Checklist

### Backend Changes Required

```python
# backend/sizing/tier_calculator.py (NEW)

class TierCalculator:
    """R-Multiple position sizing based on Confluence Score and Day Type"""
    
    RISK_PCT_BY_TIER_AND_DAY = {
        "TREND_DAY":   {"S": 2.0, "A": 1.5, "B": 1.0},
        "RANGE_DAY":   {"S": 1.0, "A": 0.5, "B": None},
        "NORMAL":      {"S": 1.5, "A": 1.0, "B": 0.5},
        "GAP_FILL":    {"S": 1.5, "A": 1.0, "B": None},
        "DEVELOPING":  None,
    }
    
    MAX_DAILY_RISK_PCT = 3.0
    LIVE_DAILY_DOLLAR_CAP = 200.0
    MAX_CONTRACTS = 5
    MIN_CONTRACTS = 1
    TICK_VALUE = 5.0
    
    def determine_tier(self, confluence_score: float) -> Optional[str]:
        if confluence_score >= 90: return "S"
        if confluence_score >= 70: return "A"
        if confluence_score >= 50: return "B"
        return None  # REJECT
    
    def calculate_position(
        self,
        confluence_score: float,
        day_type: str,
        stop_distance_pts: float,
        account_value: float,
        cumulative_risk_today: float
    ) -> dict:
        """Returns {contracts, risk_dollars, tier, status, reason}"""
        # ... full implementation per spec
```

### Files to Create
```
backend/sizing/tier_calculator.py     (NEW, ~150 lines)
backend/sizing/tests/test_tier.py     (NEW, ~200 lines, all examples covered)
backend/config.py                     (ADD: RISK_PCT_BY_TIER_AND_DAY)
backend/main.py                       (MODIFY: integrate before /trade/execute)
docs/TIER_R_MULTIPLE_SPEC.md          (THIS FILE — already in repo)
```

### Files NOT to Modify
```
DLL / Sierra code
Bridge files
Frontend (initially — can show tier in UI later)
quality_score.py (Tier replaces sizing logic, score still drives confluence)
```

### Integration Point
```python
# In backend/main.py, in the /trade/execute or setup processing flow:

# 1. Setup detected and scored
setup = process_setup(...)

# 2. Apply entry filters (V2: skip DEVELOPING etc.)
if not passes_entry_filters(setup):
    return REJECT

# 3. Calculate Confluence Score
confluence = calculate_confluence(setup)

# 4. NEW: Tier-based position sizing
position = tier_calculator.calculate_position(
    confluence_score=confluence,
    day_type=setup.day_type,
    stop_distance_pts=setup.stop_distance,
    account_value=get_account_value(),
    cumulative_risk_today=get_today_risk()
)

if position["status"] == "REJECT":
    log(position["reason"])
    return REJECT

# 5. Execute with calculated position
execute_trade(setup, contracts=position["contracts"], stop=setup.stop)
```

---

<a name="8-validation"></a>
## 8. Validation Plan

### SIM-TIER-01: Backtest R-Multiple vs Raw Contracts
```
Method:    Run MDS dataset twice
            Once with V3.0 raw contracts (3/2/1)
            Once with V3.1 R-multiple
Compare:   PnL, max drawdown, sharpe ratio
Expected:  R-multiple has lower DD, similar PnL
Acceptance: R-multiple max DD < raw contracts max DD by >20%
```

### SIM-TIER-02: Stress Test Scenarios
```
Method:    Run on different account sizes
            $1,000 / $5,000 / $25,000
            With same setups
Expected:  Risk per trade scales linearly
            Max DD scales linearly with account
            WR unchanged (sizing doesn't affect outcomes)
Acceptance: Risk consistency verified across account sizes
```

### SIM-TIER-03: Daily Cap Effectiveness
```
Method:    Find days with 5+ winning Tier-S setups
            Check that daily cap correctly blocks #3+
Expected:  No day exceeds 3% account loss
Acceptance: Across 30 days, max single-day loss <= cap
```

### Walk-Forward Validation
```
Train period: First 70% of MDS data
Test period:  Last 30%
Acceptance:   OOS PnL degradation < 30%
              OOS WR degradation < 5pp
```

---

## Document Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 5 May 2026 night | Initial spec — R-Multiple model fully detailed |

---

## References

- `MEMS26_SIMULATION_REGISTRY_V3.1.md` — Parent registry document
- `MEMS26_DAY_TYPE_SPEC_V2.md` — Day Type definitions
- Memory: "Sequential mode: required (one trade at a time)"
- Memory: "Daily cap: $200 max loss"
- Memory: "Max trades: 5/day"
- Memory: "Position size: 1 contract initially" (LIVE Day 1 override)

---

**Maintained by:** Michael (with Claude assistance)
**Status:** Locked spec, awaiting SIM-TIER-01..03 validation
**Implementation target:** Phase 3.3 Day 1 (8 May 2026)
