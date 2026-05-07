# TPO Score Audit — Day 5
**Version**: V8.5.5-TPO-AUDIT  
**Date**: 2026-05-07  
**Branch**: feature/inventory-day5  
**Mode**: READ-ONLY analysis  

---

## PART 1: Source Code Audit

### Layer 1: DLL — `sc_study/MES_AI_DataExport.cpp`

#### File: `sc_study/MES_AI_DataExport.cpp:352-375`

**Current Day Market Profile (lines 352-358)**
```cpp
// Build price-volume map for today's session
float SH=sc.High[idx],SL=sc.Low[idx],TV=0; std::map<int,float> pvm;
for(int i=idx;i>=0;i--){
    if(sc.BaseDateTimeIn[i].GetDate()<today) break;
    // distribute bar volume evenly across 0.25pt price increments
    float vps=bv/((int)((bh-bl)/0.25f)+1);
    for(float p=bl;p<=bh+0.001f;p+=0.25f) pvm[(int)(p*4)]+=vps;
}
// POC = price level with highest volume
float POC=cp,maxV=0;
for(auto&kv:pvm) if(kv.second>maxV){maxV=kv.second; POC=kv.first/4.0f;}
// VAH/VAL = expand from POC until VAPercent% of total volume enclosed
float vat=TV*(VAPercent.GetFloat()/100), vav=maxV, VAH=POC, VAL=POC;
// ... alternating up/down expansion ...
```

**TPO POC — 30-bar bar-count (lines 359-361)**
```cpp
float tpo_poc=cp; int tpo_max=0; std::map<int,int>tpo_map;
int tpo_back=(idx>=30)?30:idx;
for(int i=idx-tpo_back;i<=idx;i++)
    for(float p=sc.Low[i];p<=sc.High[i]+0.001f;p+=0.25f)
        tpo_map[(int)(p*4)]++;
for(auto&kv:tpo_map) if(kv.second>tpo_max){tpo_max=kv.second; tpo_poc=kv.first/4.0f;}
```

**Previous Day POC/VAH/VAL (lines 363-375)**: Same volume-weighted algorithm applied to previous session bars.

**JSON Output (lines 1017, 1068-1094)**
```json
"market_profile": { "poc", "vah", "val", "session_high", "session_low",
                    "tpo_poc", "prev_day_poc", "in_value_area", "above_poc" }
"tpo": {
  "current_day":  { "poc_price", "vah", "val", "in_value_area", "above_poc" },
  "previous_day": { "poc_price", "vah", "val" }
}
```

#### Behavior Summary
- **Inputs**: All bars in current session (OHLCV), previous session bars
- **Logic**: Volume-weighted POC, value area expansion for VAH/VAL
- **Output**: Raw price levels + boolean flags (in_value_area, above_poc)
- **Direction-aware**: NO — levels are computed symmetrically
- **Critical observations**: DLL computes NO score. It only exports raw POC/VAH/VAL prices and two booleans.

---

### Layer 2: Bridge — `bridge/json_bridge.py`

#### File: `bridge/json_bridge.py:418-426, 494-503, 587`

```python
# Line 418: Read TPO from DLL
tpo = raw.get("tpo")  # V7.11.0: may be None

# Lines 419-426: Fallback — fill tpo VAH/VAL from market_profile if null
if tpo and isinstance(tpo, dict):
    cd = tpo.get("current_day")
    if cd and isinstance(cd, dict) and cd.get("vah") is None and mp.get("vah") is not None:
        cd["vah"] = mp["vah"]
        cd["val"] = mp.get("val")

# Lines 494-503: Market profile passthrough
"profile": {
    "poc":          mp.get("poc", 0),
    "vah":          mp.get("vah", 0),
    "val":          mp.get("val", 0),
    "tpo_poc":      mp.get("tpo_poc", 0),
    "prev_day_poc": mp.get("prev_day_poc", 0),
    "in_va":        mp.get("in_value_area", False),
    "above_poc":    mp.get("above_poc", False),
}

# Line 587: TPO passthrough
"tpo": tpo,  # opaque pass to backend
```

#### Behavior Summary
- **Inputs**: Raw DLL JSON (`tpo` object + `market_profile` dict)
- **Logic**: Pure passthrough. Only transformation: fallback fills `tpo.current_day.vah/val` from `market_profile` when null.
- **Output**: Same TPO object forwarded to backend
- **Direction-aware**: NO
- **Critical observations**: Bridge computes NO score. Zero transformation of TPO data.

---

### Layer 3: Backend — Score Computation — `backend/quality_score.py`

#### File: `backend/quality_score.py:85-113`

**This is THE scoring function. The entire TPO Score is computed here.**

```python
# TPO (dynamic weight)
tpo = market_data.get("tpo") or {}
tpo_cd = tpo.get("current_day") or {}
price = market_data.get("price") or market_data.get("current_price") or 0
max_tpo = weights["tpo"]                    # 20-35 depending on day type
tpo_pos_pts = max_tpo // 2                  # Component 1: 50% of max
tpo_va_pts  = max_tpo - tpo_pos_pts         # Component 2: 50% of max

if tpo_cd and tpo_cd.get("poc_price") and price > 0:
    poc = tpo_cd["poc_price"]
    above_poc = price > poc

    # COMPONENT 1: Position relative to POC
    if (direction == "LONG" and above_poc) or \
       (direction == "SHORT" and not above_poc):
        breakdown["tpo"] += tpo_pos_pts     # +12 (NORMAL day)

    # COMPONENT 2: Value Area membership
    vah = tpo_cd.get("vah") or 0
    val = tpo_cd.get("val") or 0
    if vah and val and val <= price <= vah:
        breakdown["tpo"] += tpo_va_pts      # +13 (NORMAL day)
    elif not vah or not val:
        partial = tpo_va_pts // 2
        breakdown["tpo"] += partial         # +6 (partial credit)
```

#### Behavior Summary
- **Inputs**: `tpo.current_day.poc_price`, `vah`, `val`, current `price`, `direction`
- **Logic**: Two binary checks summed:
  1. Price on correct side of POC for direction → 50% of max
  2. Price inside Value Area (between VAL and VAH) → 50% of max
- **Output**: Integer score 0 to max_tpo (day-type dependent)
- **Direction-aware**: YES — Component 1 checks LONG=above POC, SHORT=below POC
- **Max score conditions**: Price above POC (for LONG) AND inside Value Area → full points
- **Min score conditions**: No POC data, OR wrong side of POC AND outside Value Area → 0

---

### Layer 4: Backend — Day Config — `backend/day_config.py`

#### File: `backend/day_config.py:5-11`

```python
QUALITY_WEIGHTS = {
    "TREND_DAY":  {"vegas": 40, "tpo": 20, "fvg": 25, "footprint": 15},
    "RANGE_DAY":  {"vegas": 20, "tpo": 35, "fvg": 25, "footprint": 20},
    "GAP_FILL":   {"vegas": 25, "tpo": 30, "fvg": 25, "footprint": 20},
    "NORMAL":     {"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20},
    "DEVELOPING": {"vegas": 30, "tpo": 25, "fvg": 25, "footprint": 20},
}
```

| Day Type | TPO Max | pos_pts (//2) | va_pts (remainder) |
|----------|---------|---------------|-------------------|
| TREND_DAY | 20 | 10 | 10 |
| RANGE_DAY | 35 | 17 | 18 |
| GAP_FILL | 30 | 15 | 15 |
| NORMAL | 25 | 12 | 13 |
| DEVELOPING | 25 | 12 | 13 |

---

### Layer 5: Backend — Setup Creation — `backend/main.py`

#### File: `backend/main.py:1040-1129`

```python
for log_direction in ('LONG', 'SHORT'):
    score_result_dir = calculate_quality_score(data, log_direction, day_type)
    # ...
    _bd = score_result_dir.get("breakdown", {})
    _tpo_s = int(_bd.get("tpo", 0))
    # ...
    _attempt_data = {
        "tpo_score": _tpo_s,       # stored as INTEGER in DB
        # ...
    }
    result_id = await insert_attempt(_attempt_data)
```

#### Behavior Summary
- Both LONG and SHORT are scored and logged for every market snapshot
- TPO score extracted from breakdown dict, stored as integer in `setup_attempts.tpo_score`
- No additional transformation or gate on TPO score alone
- Total score gate: minimum 10 to log, 45-70 for position sizing (uses sum of all components)

---

### Layer 5b: Backend — Validation Gates

**No TPO-specific gate exists.** The only gates use `total_score` (sum of all 4 components):
- `score_dir < 10` → skip logging entirely
- Position sizing uses total score thresholds (45-70 depending on day type)

TPO Score is a component of the total but is never independently gated.

---

## PART 2: Scoring Decision Tree

### TPO Score Formula (NORMAL / DEVELOPING day, max=25)

```
TPO Score = Component_1 + Component_2

Component_1: Position vs POC (max 12 pts)
├── POC data available?
│   ├── NO  → 0 pts
│   └── YES → Is price on "correct" side?
│       ├── LONG  + price > POC  → +12
│       ├── SHORT + price < POC  → +12
│       └── Otherwise            → +0

Component_2: Value Area Membership (max 13 pts)
├── POC data available?
│   ├── NO  → 0 pts
│   └── YES → VAH and VAL both available?
│       ├── NO  → partial credit → +6 (tpo_va_pts // 2)
│       └── YES → VAL ≤ price ≤ VAH?
│           ├── YES → +13
│           └── NO  → +0
```

### Discrete Score Values (NORMAL day)

| TPO Score | Conditions |
|-----------|-----------|
| **0** | No POC data (tpo_cd empty or poc_price missing or price=0) |
| **0** | POC exists, wrong side of POC, outside Value Area |
| **6** | POC exists, wrong side of POC, VAH/VAL missing (partial credit) |
| **12** | POC exists, correct side of POC, outside Value Area, VAH/VAL available |
| **12** | POC exists, correct side of POC, VAH/VAL missing but no partial (impossible: partial always awarded) |
| **13** | POC exists, wrong side of POC, inside Value Area |
| **18** | POC exists, correct side of POC, VAH/VAL missing (12 + 6 partial) |
| **25** | POC exists, correct side of POC, inside Value Area (12 + 13) — **PERFECT** |

### For RANGE_DAY (max=35):
| TPO Score | Conditions |
|-----------|-----------|
| **0** | No POC data |
| **9** | Wrong side, VAH/VAL missing (partial) |
| **17** | Correct side, outside VA |
| **18** | Wrong side, inside VA |
| **26** | Correct side, VAH/VAL missing (17 + 9 partial) |
| **35** | Correct side, inside VA (17 + 18) — **PERFECT** |

### What Makes Score MAX (25 for NORMAL)
1. TPO current_day data exists with valid POC
2. Price is above POC (for LONG) or below POC (for SHORT)
3. Price is between VAL and VAH (inside the Value Area)

### What Makes Score MIN (0)
1. No TPO data at all, OR
2. Price on wrong side of POC AND price outside Value Area

### Steep Gradients
The score jumps in large steps (0 → 12/13 → 25). There are only 4-5 discrete values possible per day type. The binary nature of both checks means **there is no gradient based on distance** — a price 0.25pt above POC scores the same as a price 15pt above POC.

---

## PART 3: Empirical Validation

**Data source**: PostgreSQL production database (Render), 1,987 closed setups with PnL data.

### Q1: TPO Score Distribution

#### All Directions (N=1,987)
| TPO Score Bucket | Count | % |
|:-----------------|------:|------:|
| 0-5 | 138 | 6.9% |
| 6-10 | 262 | 13.2% |
| 11-15 | 443 | 22.3% |
| 16-20 | 420 | 21.1% |
| 21-25 | 602 | 30.3% |
| 26+ | 122 | 6.1% |

#### By Direction
| Bucket | LONG (N=990) | SHORT (N=997) |
|:-------|-----:|-----:|
| 0-5 | 59 (6.0%) | 79 (7.9%) |
| 6-10 | 53 (5.4%) | 209 (21.0%) |
| 11-15 | 131 (13.2%) | 312 (31.3%) |
| 16-20 | 287 (29.0%) | 133 (13.3%) |
| 21-25 | 388 (39.2%) | 214 (21.5%) |
| 26+ | 72 (7.3%) | 50 (5.0%) |

**Observation**: LONG setups cluster at high TPO scores (39% at 21-25). SHORT setups spread across mid-range. This reflects the bull-market bias: price spends more time above POC inside VA.

---

### Q2: Profitability per TPO Score Bucket

#### All Directions
| TPO Score | N | Win Rate | Total PnL | Avg PnL | Median PnL |
|:----------|---:|--------:|---------:|-------:|----------:|
| 0-5 | 138 | **60.9%** | **+$1,571.75** | +$11.39 | +$22.25 |
| 6-10 | 262 | 32.8% | -$3,496.50 | -$13.35 | -$27.75 |
| 11-15 | 443 | 39.7% | -$5,115.50 | -$11.55 | -$27.75 |
| 16-20 | 420 | 43.3% | -$2,012.25 | -$4.79 | -$27.75 |
| **21-25** | **602** | **33.2%** | **-$10,805.75** | **-$17.95** | -$33.25 |
| 26+ | 122 | 61.5% | -$344.00 | -$2.82 | +$16.75 |
| **TOTAL** | **1,987** | **40.4%** | **-$20,202.25** | **-$10.17** | -$27.75 |

#### LONG Only
| TPO Score | N | Win Rate | Total PnL | Avg PnL |
|:----------|---:|--------:|---------:|-------:|
| 0-5 | 59 | **67.8%** | **+$1,427.25** | +$24.19 |
| 6-10 | 53 | 30.2% | -$1,097.50 | -$20.71 |
| 11-15 | 131 | 38.9% | -$1,751.75 | -$13.37 |
| 16-20 | 287 | 43.6% | -$1,020.00 | -$3.55 |
| 21-25 | 388 | 41.2% | -$3,688.50 | -$9.51 |
| 26+ | 72 | 65.3% | +$495.00 | +$6.88 |

#### SHORT Only
| TPO Score | N | Win Rate | Total PnL | Avg PnL |
|:----------|---:|--------:|---------:|-------:|
| 0-5 | 79 | 55.7% | +$144.50 | +$1.83 |
| 6-10 | 209 | 33.5% | -$2,399.00 | -$11.48 |
| 11-15 | 312 | 40.1% | -$3,363.75 | -$10.78 |
| 16-20 | 133 | 42.9% | -$992.25 | -$7.46 |
| **21-25** | **214** | **18.7%** | **-$7,117.25** | **-$33.26** |
| 26+ | 50 | 56.0% | -$839.00 | -$16.78 |

**Critical finding**: SHORT direction + TPO 21-25 is catastrophic: **18.7% win rate, -$33.26 avg PnL**.

---

### Q3: Distance to POC vs TPO Score

**Note**: VAH/VAL prices at entry are not stored in the database (only POC price is recoverable from `score_reasons`). Analysis limited to POC distance.

#### Profitability by Distance from POC (985 setups with extractable POC)

| Distance from POC | N | % | Avg PnL | Win Rate |
|:-------------------|---:|-----:|-------:|--------:|
| 0-1pt | 158 | 16.0% | -$10.84 | 39.2% |
| 1-2pt | 87 | 8.8% | -$25.28 | 23.0% |
| 2-3pt | 74 | 7.5% | -$15.96 | 32.4% |
| 3-5pt | 125 | 12.7% | -$16.83 | 30.4% |
| 5-10pt | 181 | 18.4% | -$21.28 | 35.9% |
| 10+pt | 360 | 36.5% | -$13.03 | 35.0% |

**Observation**: Proximity to POC does NOT improve win rate. In fact, 0-1pt from POC (39.2%) is among the better buckets, but 1-2pt (23.0%) is the worst. No meaningful edge gradient.

---

### Q4: The KEY Question — High TPO Score (20-25) Breakdown

**Sample**: 632 setups with TPO Score 20-25 (466 with extractable POC)

| Metric | Count | % |
|:-------|------:|------:|
| Within 2pt of POC | 148 | **31.8%** |
| In TPO Value Area | 421 | **90.3%** |
| Outside Value Area | 45 | 9.7% |
| >3pt from POC | 277 | **59.4%** |

#### Proximity vs Profitability (TPO 20-25 only)
| POC Distance | N | Avg PnL | Win Rate |
|:-------------|---:|-------:|--------:|
| Within 1pt | 92 | -$11.10 | 34.8% |
| Within 2pt | 148 | -$16.32 | 27.7% |
| 2-3pt | 41 | -$21.57 | 22.0% |
| 3-5pt | 77 | -$29.72 | 27.3% |
| >5pt | 200 | -$26.75 | 31.0% |

#### Value Area Status (TPO 20-25)
| Category | N | Avg PnL | Win Rate |
|:---------|---:|-------:|--------:|
| In Value Area | 421 | -$23.08 | 29.0% |
| Outside Value Area | 45 | -$27.11 | 24.4% |

#### Direction Split (TPO 20-25)
| Direction | N | Win Rate | Avg PnL | % within 2pt POC | % in VA |
|:----------|---:|--------:|-------:|------------------:|--------:|
| LONG | 313 | 36.7% | -$14.81 | 21.7% | 90.1% |
| SHORT | 153 | **11.8%** | **-$41.18** | 52.3% | 90.8% |

### Michael's Hypothesis Test

> "TPO Score gives high values to mid-range setups with no edge"

**CONFIRMED.**

- **90.3%** of high-TPO setups are inside the Value Area (between VAL and VAH) — this is mid-range by definition
- **59.4%** are more than 3pt from POC, meaning they're floating in the value area with no proximity to any specific level
- Being "in the value area" is the *condition that awards points*, not a byproduct — the score literally rewards mid-range positioning
- These setups have **29.0% win rate** and **-$23.08 avg PnL** — no edge

---

## PART 4: Summary Verdict

### Question 1: Does TPO Score reward proximity to POC, VAH, VAL, or none?

**NONE.** TPO Score has zero distance-sensitivity. It uses two binary checks:
1. Is price above/below POC? (yes/no)
2. Is price between VAL and VAH? (yes/no)

A price 0.25pt above POC scores identically to a price 15pt above POC. A price touching VAH from inside scores identically to a price at dead center of the value area. **There is no proximity gradient.**

### Question 2: Is TPO Score direction-aware?

**YES** — but only in Component 1 (position vs POC). LONG requires above POC, SHORT requires below POC. Component 2 (value area membership) is direction-agnostic.

### Question 3: Do high TPO Score setups (20-25) outperform low (0-10)?

**NO. The opposite is true.**

| Bucket | Win Rate | Avg PnL |
|:-------|--------:|-------:|
| 0-5 (low) | **60.9%** | **+$11.39** |
| 21-25 (high) | 33.2% | -$17.95 |

TPO Score is **inversely correlated** with profitability. The 21-25 bucket is the single largest loss center in the entire dataset (-$10,805.75 total).

### Question 4: Is the score MEANINGFUL or BROKEN?

## **VERDICT: `SCORE_BROKEN` — TPO Score is a Value-Area-Membership Proxy, Not an Edge Measure**

The score is broken in a specific, diagnosable way:

1. **It rewards being INSIDE the value area** — the zone where price spends 70% of its time and where there is NO structural edge (no liquidity pool, no rejection level, no breakout trigger).

2. **It does NOT reward proximity to extremes** — VAH and VAL are only used as boundary checks ("is price between them?"), never as target levels ("how close is price to them?"). A setup at VAH (potential rejection = real edge) scores the same as a setup at POC (mid-range = no edge).

3. **The direction check is backwards for mean-reversion** — for a LONG setup, being above POC gets points. But a LONG near VAL (below POC) is a classic mean-reversion entry with structural support. The score penalizes this.

4. **The "perfect" score (25/25) describes the WORST setup** — price above POC, inside Value Area = mid-range LONG with no level proximity, no sweep, no rejection. This is where 90% of losing LONG trades originate.

5. **Score=0 is the best performer** because it indicates either: (a) no TPO data (the score doesn't contaminate total), or (b) price outside Value Area near extremes (where actual edges exist).

---

### Summary One-Liners

```
Direction-aware:          YES (Component 1 only)
High score → Profitable:  NO  (inverted — high score = worst PnL)
High score → Near extremes: NO (90% are mid-range Value Area)
Verdict:                  SCORE_BROKEN
```

---

*Generated 2026-05-07 by TPO Score Audit, Day 5 inventory analysis.*
