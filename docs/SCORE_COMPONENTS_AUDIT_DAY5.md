# Score Components Audit — Day 5 (Vegas + FVG + Footprint)
**Version**: V8.5.6-COMPONENT-AUDIT  
**Date**: 2026-05-07  
**Branch**: feature/inventory-day5  
**Mode**: READ-ONLY analysis  
**Prior**: TPO Score audit (commit d1d0a78) found SCORE_BROKEN  

---

## PART 1: Vegas Score Audit

### 1A: Source Code Audit

#### Layer 1: DLL — `sc_study/MES_AI_DataExport.cpp:759-848`

**EMA Computation (lines 760-769)**
```cpp
sc.ExponentialMovAvg(sc.BaseDataIn[SC_LAST], EMA144, 144);
sc.ExponentialMovAvg(sc.BaseDataIn[SC_LAST], EMA169, 169);
float tunnel_top = (ema144_val > ema169_val) ? ema144_val : ema169_val;
float tunnel_bot = (ema144_val < ema169_val) ? ema144_val : ema169_val;
float tunnel_width = fabs(ema144_val - ema169_val);
const char* vegas_pos = (cp > tunnel_top) ? "ABOVE" : (cp < tunnel_bot) ? "BELOW" : "INSIDE";
```

**Trend Detection with Hysteresis (lines 771-816)**
```cpp
// 2-bar confirmation + 0.5pt minimum distance for flip
int raw_dir = (ema_distance > 0) ? 1 : -1;  // EMA144 > EMA169 = BULLISH
if (raw_dir != sticky_dir && abs_ema_dist > 0.5f) {
    pending_flips++;
    if (pending_flips >= 2) {  // Must persist 2 bars
        sticky_dir = raw_dir;  // Flip confirmed
    }
}
const char* vegas_trend = (sticky_dir == 1) ? "BULLISH" : "BEARISH";
```

**Flip Counter (lines 827-848)**: Counts RTH-only trend flips per day, resets at date boundary. Used for day type classification.

**JSON Export (lines 1044-1053)**:
```json
"vegas": {
  "ema144": float, "ema169": float,
  "tunnel_top": float, "tunnel_bot": float, "tunnel_width": float,
  "price_position": "ABOVE|BELOW|INSIDE",
  "trend": "BULLISH|BEARISH",
  "data_quality": "FULL|PARTIAL|INSUFFICIENT"
}
```

**DLL behavior**: Computes EMAs, tunnel geometry, trend with hysteresis, position. Exports raw data. No scoring.

#### Layer 2: Bridge — `bridge/json_bridge.py:417, 584`

Pure pass-through. No transformation, no enrichment. Vegas object forwarded as-is to backend.

#### Layer 3: Backend — `backend/quality_score.py:22-83`

**The complete Vegas scoring logic:**

```python
# Step 1: Flow-Vegas disagreement detection
flow_disagree = "AGREE"
if vtrend == "BULLISH" and vpos == "BELOW" and fp_delta < -200:
    flow_disagree = "STRONG_DISAGREE"
elif vtrend == "BEARISH" and vpos == "ABOVE" and fp_delta > 200:
    flow_disagree = "STRONG_DISAGREE"

# Step 2: Real flow direction (uses price position + footprint delta)
real_flow_long = (vpos == "ABOVE" or fp_delta > 100)
real_flow_short = (vpos == "BELOW" or fp_delta < -100)

# Step 3: Score assignment
if flow_disagree == "STRONG_DISAGREE":
    if direction_matches_flow: pts = max_vegas * 0.5   # 15 pts
    else: pts = 0
elif trend_matches:
    if vwidth >= 0.5:    pts = max_vegas          # 30 pts (FULL)
    elif vwidth >= 0.2:  pts = max_vegas * 0.75   # 22 pts
    else:                pts = max_vegas * 0.5    # 15 pts
elif vtrend == "NEUTRAL":
    pts = max_vegas * 0.3                          # 9 pts
else:  # trend opposes direction
    if weak_disagree and direction_matches_flow:
        pts = max_vegas * 0.25                     # 7 pts
    else: pts = 0
```

#### Behavior Summary
- **Inputs**: vegas.trend, vegas.tunnel_width, vegas.price_position, footprint delta, direction
- **Logic**: Trend match + width modulation + flow override
- **Direction-aware**: YES — full scoring depends on direction matching Vegas trend
- **Max (30)**: Trend matches direction AND tunnel width >= 0.5pt
- **Min (0)**: Trend opposes direction with no flow override

---

### 1B: Decision Tree (NORMAL day, max=30)

```
Vegas Score Decision Tree:
│
├── Flow STRONG_DISAGREE? (Vegas trend contradicted by price position + delta)
│   ├── Direction matches real flow → 15
│   └── Direction doesn't match flow → 0
│
├── Trend MATCHES direction?
│   ├── Width >= 0.5pt → 30 (PERFECT)
│   ├── Width >= 0.2pt → 22
│   └── Width < 0.2pt → 15
│
├── Trend is NEUTRAL?
│   └── → 9
│
└── Trend OPPOSES direction?
    ├── WEAK_DISAGREE + flow hints favor → 7
    └── Otherwise → 0
```

**Discrete values (NORMAL day)**: 0, 7, 9, 15, 22, 30

---

### 1C: Empirical Validation (N=1,992)

#### By Vegas Score Bucket — All Directions
| Vegas Score | N | Win Rate | Total PnL | Avg PnL |
|:------------|---:|--------:|---------:|-------:|
| 0-5 | 778 | **47.7%** | -$3,194 | -$4.11 |
| 6-15 | 376 | 30.1% | -$8,162 | -$21.71 |
| 16-25 | 147 | **55.1%** | **+$578** | **+$3.93** |
| 26-30 | 635 | 36.1% | -$7,200 | -$11.34 |
| 31-40 | 56 | 16.1% | -$2,473 | -$44.16 |

#### By Direction — High Vegas (26-30)
| Direction | N | Win Rate | Avg PnL |
|:----------|---:|--------:|-------:|
| LONG | 532 | 38.2% | -$8.50 |
| SHORT | 103 | 25.2% | -$26.00 |

#### Granular Standout Values
| Vegas | N | Win Rate | Avg PnL | Note |
|------:|---:|--------:|-------:|:-----|
| 0 | 745 | 47.8% | -$3.27 | No Vegas data = moderate performance |
| 15 | 125 | 20.8% | **-$39.68** | Narrow tunnel match = worst |
| 20 | 50 | **80.0%** | **+$24.59** | Medium width match = best |
| 30 | 635 | 36.1% | -$11.34 | Full score = below average |
| 40 | 56 | 16.1% | -$44.16 | TREND_DAY full = catastrophic |

#### Vegas Trend vs Direction Match
| Category | N | Win Rate | Avg PnL |
|:---------|---:|--------:|-------:|
| BULLISH trend, direction matches | 839 | 41.7% | -$8.84 |
| BULLISH trend, direction opposes | 788 | 40.2% | -$9.88 |
| BEARISH trend, direction matches | 184 | 21.7% | **-$29.76** |
| BEARISH trend, direction opposes | 181 | **53.0%** | **+$1.28** |

#### Vegas Tunnel Width
| Width (pts) | N | Win Rate | Avg PnL |
|:------------|---:|--------:|-------:|
| < 0.5 | 4 | 0.0% | -$56.88 |
| 0.5-1.0 | 162 | 35.8% | -$5.54 |
| **1.0-2.0** | **167** | **44.9%** | **+$11.90** |
| > 2.0 | 410 | 35.6% | -$22.86 |

---

### 1D: KEY Test

**Does Vegas Score reward "stable trend" (real edge) or just "trend + direction match" (data presence)?**

1. **Trend match is not an edge**: BEARISH_MATCH (Vegas bearish, SHORT trade) has the WORST win rate (21.7%). BEARISH_OPPOSES is the BEST (53%). Matching Vegas trend direction is anti-predictive for SHORT trades.

2. **Width modulation partially works**: Width 1.0-2.0pt is profitable (+$11.90), but this is drowned by the binary trend-match gate — you need trend match AND width to get high scores, but trend match itself is not predictive.

3. **Full score (30) means width >= 0.5pt + trend match**: This scores 635 setups at 36.1% WR, -$11.34 avg. Below the 0-score baseline (47.8% WR, -$3.27).

4. **Vegas=40 (TREND_DAY full) is catastrophic**: 16.1% WR. The higher the weight given to Vegas (TREND_DAY gives 40), the worse the outcome.

5. **The score is noisy, not informative**: The correlation between Vegas score and profitability is non-monotonic and dominated by the mid-range anomaly (Vegas=20 at 80% WR, N=50).

**Component Delta**: Avg Vegas in wins = 12.54, in losses = 15.36. **Delta = -2.82** (higher Vegas in losers).

---

## PART 2: FVG Score Audit

### 2A: Source Code Audit

#### Layer 1: DLL — `sc_study/MES_AI_DataExport.cpp:924-950`

**FVG Detection:**
```cpp
// Scan last 50 bars for gaps between bar[i] and bar[i-2]
// BULLISH FVG: Low[i] - High[i-2] >= 0.25pt and <= 5.0pt
float bull_gap = sc.Low[i] - sc.High[i-2];
if (bull_gap >= 0.25f && bull_gap <= 5.0f)
    addTrig("FVG", "bullish", sc.Low[i], sc.High[i-2], bull_gap, "", 0);

// BEARISH FVG: Low[i-2] - High[i] >= 0.25pt and <= 5.0pt
float bear_gap = sc.Low[i-2] - sc.High[i];
if (bear_gap >= 0.25f && bear_gap <= 5.0f)
    addTrig("FVG", "bearish", sc.Low[i-2], sc.High[i], bear_gap, "", 0);
```

**Output**: Trigger objects with type="FVG", direction, gap_size, price_high, price_low, detected_at, expires_at (5 minutes).

**Key constraint**: Triggers auto-expire after 300 seconds. Max 20 active triggers.

#### Layer 2: Bridge — `bridge/json_bridge.py`

Pass-through. Triggers array forwarded as-is to backend.

#### Layer 3: Backend — `backend/quality_score.py:115-147`

**The complete FVG scoring logic:**
```python
fvg_dir = "bullish" if direction == "LONG" else "bearish"
triggers = (market_data.get("triggers") or {}).get("active", [])
recency_sec = 30 * 60  # 30 minutes

# Filter: type=FVG, direction matches, detected within 30 minutes
matching_fvg = [t for t in triggers
                if t.get("type") == "FVG"
                and t.get("direction") == fvg_dir
                and (now_ts - fvg_ts) <= recency_sec]

max_fvg = weights["fvg"]  # 25 for NORMAL
if len(matching_fvg) >= 3:
    breakdown["fvg"] = max_fvg       # 25 (FULL)
elif len(matching_fvg) >= 1:
    pts = int(max_fvg * 0.6)
    breakdown["fvg"] = pts            # 15
else:
    breakdown["fvg"] = 0              # 0
```

#### Behavior Summary
- **Inputs**: Active trigger list, direction
- **Logic**: Count direction-matching FVG triggers within 30-minute window
- **Direction-aware**: YES — only counts FVGs matching trade direction
- **Max (25)**: 3+ recent matching FVGs exist
- **Min (0)**: No matching FVGs in last 30 minutes
- **Critical observation**: Does NOT consider FVG size, age, fill status, or proximity to price. Just counts them.

---

### 2B: Decision Tree (NORMAL day, max=25)

```
FVG Score Decision Tree:
│
├── How many direction-matching FVGs in last 30 min?
│   ├── 0 matches → 0
│   ├── 1-2 matches → 15
│   └── 3+ matches → 25 (PERFECT)
```

**Only 3 possible values**: 0, 15, 25.

---

### 2C: Empirical Validation (N=1,992)

#### Distribution — CRITICAL
| FVG Score | N | % of Total | Win Rate | Total PnL | Avg PnL |
|:----------|---:|---------:|--------:|---------:|-------:|
| 0 | 10 | 0.5% | 60.0% | +$5 | +$0.47 |
| 15 | 33 | 1.7% | 27.3% | -$644 | -$19.52 |
| **25** | **1,949** | **97.8%** | **40.4%** | **-$19,812** | **-$10.16** |

**97.8% of all setups score full marks on FVG.** This component has essentially zero discriminating power.

#### FVG Match Count (parsed from score_reasons)
| Matches | N | Win Rate | Avg PnL |
|--------:|---:|--------:|-------:|
| 3 | 58 | 27.6% | -$21.28 |
| 7 | 260 | 43.1% | -$11.20 |
| 8 | 241 | **47.3%** | -$3.44 |
| 11 | 154 | **46.1%** | **+$0.19** |
| 16 | 30 | 30.0% | -$33.38 |
| 17+ | 14 | 21.4% | -$36.75 |

The raw match count has some signal (8-11 is sweet spot, extremes are bad) but this is collapsed into a binary "3+ = full score" gate that destroys the information.

---

### 2D: KEY Test

**FVG Score = 25 in 97.8% of setups. This is not a scoring component — it's a data-availability flag.**

- In MES (a liquid, heavily traded instrument), there are almost always 3+ FVGs in any 30-minute window
- The DLL scans 50 bars and triggers auto-expire at 5 minutes (but scoring window is 30 minutes — much wider than trigger lifetime), so triggers accumulate easily
- FVG size is not considered (a 0.25pt gap scores same as a 4pt gap)
- FVG fill status is not considered (unfilled gap near price vs distant stale gap)
- FVG age within the 30-min window is not considered

**Component Delta**: Avg FVG in wins = 24.70, in losses = 24.71. **Delta = -0.01** (zero signal).

---

## PART 3: Footprint Score Audit

### 3A: Source Code Audit

#### Layer 1: DLL — `sc_study/MES_AI_DataExport.cpp:296-305, 444-584, 953-971`

**Delta Computation (line 296-305)**:
```cpp
float ask_vol = sc.AskVolume[idx];
float bid_vol = sc.BidVolume[idx];
float delta   = ask_vol - bid_vol;
```

**Imbalance Ratio (line 953-960)**:
```cpp
float fp_max = (float)((fp_buy > fp_sell) ? fp_buy : fp_sell);
float fp_min = (float)((fp_buy < fp_sell) ? fp_buy : fp_sell);
float fp_imb_ratio = (fp_min > 0) ? fp_max / fp_min : 0.0f;
```

**Footprint Booleans**: 8 boolean signals computed from VAP (Volume At Price) data:
- `absorption_detected`: Large opposing volume at extreme tick, price rejected
- `exhaustion_detected`: < 5 contracts at extreme tick (zero print)
- `trapped_buyers`: Broke above prior high then closed below open
- `stacked_imbalance_count/dir`: Consecutive 2.5x ratios at adjacent price levels
- `pullback_delta_declining`: Absolute delta declining over 3 bars
- `pullback_aggressive_buy/sell`: Price dipping but delta positive (or vice versa)

**JSON Export (lines 1116-1121)**:
```json
"footprint_last_bar": {
  "buy_vol": int, "sell_vol": int, "delta": int,
  "imbalance_ratio": float, "is_reversal": bool
}
```

#### Layer 2: Bridge

Pass-through for `footprint_bools` and `triggers.footprint_last_bar`. No computation.

#### Layer 3: Backend — `backend/quality_score.py:149-195`

**The complete Footprint scoring logic:**
```python
max_fp = weights["footprint"]       # 20 for NORMAL
fp_delta_pts = int(max_fp * 0.7)    # 14 pts for delta (70%)
fp_imb_pts = max_fp - fp_delta_pts  # 6 pts for imbalance (30%)

# COMPONENT 1: Delta direction match (0-14 pts)
delta = fp.get("delta", 0) or (buy - sell)
confirms = (direction == "LONG" and delta > 0) or \
           (direction == "SHORT" and delta < 0)
if confirms:
    if abs(delta) >= 200:  pts = fp_delta_pts      # 14 (strong)
    elif abs(delta) >= 50: pts = fp_delta_pts * 0.6 # 8 (moderate)
    else:                  pts = fp_delta_pts * 0.3 # 4 (weak)

# COMPONENT 2: Imbalance / Absorption (0-6 pts)
if imbalance_ratio > 1.5:
    breakdown["footprint"] += fp_imb_pts            # +6
elif absorption_detected:
    breakdown["footprint"] += fp_imb_pts            # +6
```

#### Behavior Summary
- **Inputs**: footprint_last_bar.delta, imbalance_ratio, footprint_bools.absorption_detected
- **Logic**: Delta direction match (scaled by magnitude) + imbalance/absorption bonus
- **Direction-aware**: YES — delta must confirm direction
- **Max (20)**: Delta >= 200 confirming direction AND (imbalance > 1.5 OR absorption)
- **Min (0)**: No delta data, OR delta opposes direction with no imbalance

---

### 3B: Decision Tree (NORMAL day, max=20)

```
Footprint Score Decision Tree:
│
├── Delta available?
│   ├── NO → 0 (delta component)
│   └── YES → Delta confirms direction?
│       ├── NO → 0 (delta component)
│       └── YES → How strong?
│           ├── |delta| >= 200 → +14 (strong)
│           ├── |delta| >= 50  → +8  (moderate)
│           └── |delta| > 0    → +4  (weak)
│
├── Imbalance ratio > 1.5?
│   ├── YES → +6
│   └── NO → Absorption detected?
│       ├── YES → +6
│       └── NO → +0
│
└── Total = delta_pts + imbalance_pts (0 to 20)
```

**Discrete values (NORMAL day)**: 0, 4, 6, 8, 10, 14, 20

---

### 3C: Empirical Validation (N=1,992)

#### By Footprint Score Bucket — All Directions
| FP Score | N | Win Rate | Total PnL | Avg PnL |
|:---------|---:|--------:|---------:|-------:|
| 0 | 265 | **47.2%** | -$452 | -$1.70 |
| 1-5 | 166 | 39.2% | -$2,514 | -$15.14 |
| 6-10 | 911 | **47.3%** | -$1,755 | -$1.93 |
| 11-15 | 279 | 31.5% | -$5,250 | -$18.82 |
| **16-20** | **371** | **25.3%** | **-$10,481** | **-$28.25** |

**The score is perfectly inverted**: Win rate decreases monotonically from 47% at score 0 to 25% at score 16-20.

#### By Direction — High Footprint (16-20)
| Direction | N | Win Rate | Avg PnL |
|:----------|---:|--------:|-------:|
| LONG | 202 | 30.2% | -$24.99 |
| SHORT | 169 | **19.5%** | **-$32.15** |

#### Delta Strength (from score_reasons)
| Strength | N | Win Rate | Avg PnL |
|:---------|---:|--------:|-------:|
| weak (|d| < 50) | 267 | 38.2% | -$12.52 |
| moderate (|d| 50-200) | 246 | 30.9% | -$20.48 |
| **strong (|d| >= 200)** | **468** | **25.9%** | **-$26.80** |

**Stronger delta = worse outcomes.** This is the exact opposite of what the score rewards.

#### Granular Standout Values
| FP Score | N | Win Rate | Avg PnL | Note |
|---------:|---:|--------:|-------:|:-----|
| 0 | 265 | 47.2% | -$1.70 | No footprint data = best |
| 6 | 710 | **50.6%** | **+$1.76** | Only profitable value |
| 14 | 245 | 32.2% | -$16.61 | Strong delta match |
| 20 | 371 | 25.3% | -$28.25 | "Perfect" = worst |

---

### 3D: KEY Test

**For setups with FP 16-20 (N=371):**

1. **Did delta confirm direction?** YES — by definition (you need delta confirmation to score 14+ on the delta component). All 371 had confirming delta >= 200.

2. **Was the confirming delta predictive?** NO. Strong confirming delta has 25.9% WR vs weak delta at 38.2%. A large delta in the trade's direction is a **contrarian signal** — it indicates the move may already be exhausted, not beginning.

3. **Imbalance contribution**: 74.4% had imbalance > 1.5 or absorption. This adds 6 pts but adds no edge — WR with/without imbalance bonus is similar.

4. **Why is the score inverted?** The footprint measures **what just happened** (last bar delta), not **what will happen next**. A large positive delta means aggressive buying already occurred. Scoring this as "confirming a LONG" is like entering a trade after the move is done. The footprint captures the **completion** of a move, not the **beginning**.

**Component Delta**: Avg FP in wins = 7.75, in losses = 10.07. **Delta = -2.32** (higher FP in losers).

---

## PART 4: Summary Verdict Table

| Component | Max Pts | Direction-Aware | High Score → Profitable | Component Delta | Verdict |
|:----------|--------:|:----------------|:-----------------------|:---------------|:--------|
| **Vegas (0-30/40)** | 30-40 | YES | NO (30=36.1% WR, 0=47.8%) | -2.82 | **BROKEN** |
| **FVG (0-25)** | 25 | YES | N/A (97.8% score 25) | -0.01 | **DATA_PROXY** |
| **Footprint (0-20)** | 20 | YES | NO (perfectly inverted: 0=47%, 20=25%) | -2.32 | **INVERTED** |
| **TPO (0-25/35)** | 25-35 | YES (Comp 1) | NO (0=60.9%, 25=33.2%) | -1.03 | **BROKEN** |

### Verdict Explanations

**Vegas = BROKEN**: The trend-match gate is not predictive — BEARISH_MATCH is the worst category (21.7% WR). Width modulation has signal (1-2pt sweet spot) but is dominated by the flawed trend-match binary. The flow-override logic (W35) adds complexity without improving outcomes. Full score (30) underperforms zero score.

**FVG = DATA_PROXY**: Measures "are there FVGs in MES in the last 30 minutes?" which is almost always YES in a liquid market. 97.8% of setups get full marks. Zero discriminating power. The underlying data (FVG count, size, freshness) has some signal that is completely wasted by the 3+ threshold.

**Footprint = INVERTED**: Higher scores predict WORSE outcomes with near-perfect monotonic inversion. The design flaw: the last-bar delta captures the **completion** of a directional move, not its **initiation**. Rewarding large confirming delta means entering after the smart money has already positioned. Strong delta (|d| >= 200) is a 25.9% WR signal being scored as the best possible confirmation.

**TPO = BROKEN** (from prior audit): Rewards mid-range Value Area membership (where 70% of price action occurs) instead of proximity to extremes (where actual edges exist). Full score describes the setup with least structural edge.

---

## PART 5: Total Score Implications

### Total Score = Vegas + TPO + FVG + Footprint = 0-100

With 1 BROKEN, 1 DATA_PROXY, 1 INVERTED, and 1 BROKEN component:

#### Performance by Total Score Bucket
| Total Score | N | Win Rate | Avg PnL | Avg Vegas | Avg TPO | Avg FVG | Avg FP |
|:------------|---:|--------:|-------:|----------:|--------:|--------:|-------:|
| **0-49** | **596** | **57.9%** | **+$1.95** | 1.2 | 8.8 | 24.4 | 5.1 |
| 50-69 | 620 | 29.4% | -$10.38 | 10.8 | 14.0 | 24.7 | 9.3 |
| 70-100 | 776 | 35.6% | -$19.56 | 26.9 | 19.4 | 25.0 | 12.1 |

**The total score is anti-predictive.** The only profitable bucket is 0-49 (the "reject" zone).

#### What Drives High Scores (70-100)?
1. **Vegas** contributes most additional signal: 26.9 avg (vs 1.2 in low bucket) — **+25.7 pts swing**
2. **Footprint** contributes second most: 12.1 avg (vs 5.1) — **+7.0 pts swing**
3. **TPO** contributes third: 19.4 avg (vs 8.8) — **+10.6 pts swing**
4. **FVG** is constant: ~25 in all buckets — **+0.6 pts swing** (noise)

The two most influential components driving execution decisions (Vegas and Footprint) are the two with the worst component deltas (-2.82 and -2.32 respectively).

#### Performance by Number of Non-Zero Components
| Non-Zero Components | N | Win Rate | Avg PnL |
|:-------------------|---:|--------:|-------:|
| 1 | 23 | **65.2%** | **+$4.48** |
| 2 | 216 | **55.1%** | **+$1.56** |
| 3 | 736 | 45.0% | -$2.91 |
| 4 | 1,017 | **33.2%** | **-$18.43** |

**Each additional non-zero component degrades performance by ~10% WR.** When all 4 components "confirm" a trade, it has the worst outcome. This is the signature of a system that rewards data availability rather than edge.

#### All 4 Component Deltas Are Negative
| Component | Avg in Wins | Avg in Losses | Delta |
|:----------|:----------:|:------------:|------:|
| Vegas | 12.54 | 15.36 | **-2.82** |
| Footprint | 7.75 | 10.07 | **-2.32** |
| TPO | 13.93 | 14.96 | **-1.03** |
| FVG | 24.70 | 24.71 | **-0.01** |

Every single component scores higher in losing trades than winning trades. The total score is a sum of four anti-signals.

#### Execution Threshold Impact
The system uses total score >= 70 for FULL_SIZE and >= 50 for HALF_SIZE (NORMAL day). Given:
- 70+ bucket: 35.6% WR, -$19.56 avg → **these are the worst trades**
- 50-69 bucket: 29.4% WR, -$10.38 avg → **also losing**
- 0-49 bucket: 57.9% WR, +$1.95 avg → **the only profitable trades are rejected**

The threshold-based execution system is structurally guaranteed to select the worst trades for the largest position sizes.

---

## Architecture Diagnosis

The scoring system has a fundamental architectural flaw: **it conflates data richness with trading edge.**

Every component rewards the same meta-signal:
- **Vegas**: "Is there a clear trend?" (data richness, not direction predictiveness)
- **TPO**: "Is there POC data and is price in the populated zone?" (data presence)
- **FVG**: "Are there triggers in the system?" (almost always yes)
- **Footprint**: "Is there strong delta?" (last-bar momentum, which is mean-reverting)

When all 4 say "yes," you have a well-populated data environment — but that doesn't mean there's a trading edge. In fact, the richest data environments (clear trend, inside value area, many FVGs, strong delta) often correspond to **crowded trades** where the easy money has already been made.

The result: the system spends 100% of its position sizing budget on the 70-100 score bucket (-$19.56 avg), while the 0-49 bucket (the only one making money) is systematically rejected.

---

```
Vegas:     Direction-aware: YES    High→Profit: NO (inverted)   Verdict: BROKEN
FVG:       Direction-aware: YES    High→Profit: N/A (no variance) Verdict: DATA_PROXY
Footprint: Direction-aware: YES    High→Profit: NO (inverted)   Verdict: INVERTED
TPO:       Direction-aware: YES(1) High→Profit: NO (inverted)   Verdict: BROKEN

Total Score architecture: FUNDAMENTALLY_BROKEN
```

---

*Generated 2026-05-07 by Component Score Audit, Day 5 inventory analysis.*  
*Prior audit: docs/TPO_SCORE_AUDIT_DAY5.md (commit d1d0a78)*
