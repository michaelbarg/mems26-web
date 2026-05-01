# Quality Score V2 — Design Specification

**Version:** V8.2.3  
**Date:** 2026-05-01  
**Status:** DRAFT — awaiting 5-day observation data (3-7/5) before implementation  
**Implementation target:** 2026-05-11 (after spec update on 10/5 with live data)

---

## 1. Executive Summary

Quality Score V2 fundamentally changes what each component measures, shifting from directional agreement to structural quality. V1 showed Anti-Correlation: setups scoring 70+ had approximately 30% win rate across 96 trades — the highest-confidence bucket performed worst. Root cause analysis (30/4) identified that three of four components (Vegas, TPO, Footprint) reward directional alignment with lagging indicators, effectively penalizing counter-trend setups that represent the system's best entries (sweeps and rejections are inherently counter-move patterns). V2 redefines each component to measure market structure quality — tunnel width, value area position, FVG recency, and absorption detection — while removing direction from the score entirely. Direction decisions remain with triggers (Sweep/FVG/Rejection) and Day Type adapters. The expected outcome is that Score 70+ bucket achieves >50% WR by selecting structurally sound environments rather than filtering for directional consensus with lagging data.

---

## 2. Current State (V1) Recap

### Component Summary

| Component | Weight (NORMAL) | What it measures (V1) | Known issue |
|-----------|----------------|-----------------------|-------------|
| Vegas | 30 | Direction match: EMA 144 vs EMA 169 trend | LAGGING — EMAs on 3-min bars = 7-8h effective lookback. Punishes valid counter-trend sweeps. |
| TPO | 25 | Direction reward: price above/below POC + Value Area membership | VAH/VAL frequently unavailable; awards points for being on the "right side" of POC, which is static and stale by afternoon. |
| FVG | 25 | Count of matching FVG triggers in 30-min window | 30-min window too wide — captures noise. High FVG counts (>5) typically indicate chop, not clean setups. No penalty for excessive counts. |
| Footprint | 20 | Delta sign match: positive delta = bullish, negative = bearish | Treats delta as directional confirmation. Misses that large opposing delta at a key level = absorption = reversal signal. The most predictive footprint pattern (absorption) scores 0. |

### Weight Distribution by Day Type (V1)

| Day Type | Vegas | TPO | FVG | Footprint | Full Size Threshold | Half Size Threshold |
|----------|-------|-----|-----|-----------|--------------------|--------------------|
| TREND_DAY | 40 | 20 | 25 | 15 | 60 | 45 |
| RANGE_DAY | 20 | 35 | 25 | 20 | 70 | 55 |
| GAP_FILL | 25 | 30 | 25 | 20 | 65 | 50 |
| NORMAL | 30 | 25 | 25 | 20 | 70 | 50 |
| DEVELOPING | 30 | 25 | 25 | 20 | 70 | 50 |

### Core Problem

V1 conflates two questions: "Is the environment good for trading?" and "Does everything agree on direction?" The second question is counterproductive for a system whose best setups (sweeps, rejections) are inherently against the immediate flow. A sweep at PDL with Vegas BEARISH, delta negative, and price below POC scores 85+ in V1 — and loses, because the sweep IS the reversal that makes those indicators stale.

---

## 3. V2 Component Specifications

### 3.1 Vegas — Tunnel Structure (not direction)

**V1:** Awards max points when Vegas trend matches trade direction (LONG + BULLISH = full score).

**V2:** Measures tunnel width as a proxy for market regime clarity. Wide tunnel = established trend (structure exists). Narrow tunnel = transition/chop (uncertain structure). Direction of the tunnel is **ignored** — it does not contribute to score.

**Formula:**

```
vegas_width = abs(ema_144 - ema_169)  // in points

if vegas_width >= 3.0:
    vegas_score = max_vegas          // Wide: clear structure
elif vegas_width >= 1.5:
    vegas_score = max_vegas * 0.70   // Medium: usable structure
elif vegas_width >= 0.5:
    vegas_score = max_vegas * 0.40   // Narrow: weak structure
else:
    vegas_score = 0                  // Flat: no structure, skip

// Thresholds: [TBD after observation — 3.0/1.5/0.5 are initial estimates]
```

**Worked example:** Vegas BULLISH, width = 4.07pt, trade direction = SHORT (counter-trend sweep).
- V1: direction mismatch → 0 points
- V2: width 4.07 >= 3.0 → full 30 points (clear structure exists, good environment regardless of direction)

**Why less lagging / more predictive:** Width changes slowly and indicates regime stability — it tells you whether the market has established structure to trade around, not which way it went 7 hours ago. A 4pt-wide tunnel means levels are meaningful whether you trade with or against the trend.

### 3.2 FVG — Recency + Noise Penalty

**V1:** Counts matching-direction FVG triggers in a 30-minute window. More matches = higher score.

**V2:** Tightens the recency window to 10 minutes and adds a noise penalty. A moderate count (1-3) of recent FVGs signals a clean gap to fill. A high count (>5) signals choppy price action creating many small gaps — this is noise, not opportunity.

**Formula:**

```
fvg_dir = "bullish" if direction == "LONG" else "bearish"
recent_matches = count FVG triggers matching fvg_dir within last 10 minutes
total_all_dir = count ALL FVG triggers matching fvg_dir (any age)

if recent_matches >= 1 AND recent_matches <= 3:
    fvg_score = max_fvg                         // Clean, recent gap(s)
elif recent_matches >= 4 AND recent_matches <= 5:
    fvg_score = max_fvg * 0.50                  // Getting noisy
elif recent_matches > 5:
    fvg_score = max_fvg * 0.20                  // Chop — many gaps = bad
    // Noise penalty: [TBD — may become 0 after observation]
elif recent_matches == 0 AND total_all_dir >= 1:
    fvg_score = max_fvg * 0.25                  // Stale gaps only
else:
    fvg_score = 0                               // No FVGs at all

// Window: 10 min [TBD after observation — may adjust to 15 min]
// Noise threshold: 5 [TBD after observation]
```

**Worked example:** FVG bullish: 11, bearish: 5. Trade direction = LONG.
- 11 bullish FVGs total. Suppose 6 are within the last 10 minutes.
- V1: 11 total, many recent → full 25 points (more = better)
- V2: 6 recent matches > 5 → noise penalty → 25 * 0.20 = 5 points. The high FVG count signals chop, not a clean setup.

**Why less lagging / more predictive:** The 10-minute window captures only the freshest gaps. The noise penalty inverts the "more is better" assumption — empirically, clean setups have 1-3 FVGs, not 11. This aligns scoring with the pattern the system is designed to trade: a single, significant gap at a key level.

### 3.3 Footprint — Contrarian Absorption Detection

**V1:** Awards points when footprint delta sign matches trade direction (LONG + positive delta = score).

**V2:** Flips the interpretation. For sweep/rejection setups, the most predictive footprint signal is **absorption** — large delta OPPOSING the trade direction, combined with price holding a level. This means aggressive sellers (negative delta) are being absorbed at support, or aggressive buyers at resistance. The setup triggers precisely because someone is absorbing the flow.

**Formula:**

```
delta = footprint_last_bar.delta
abs_delta = abs(delta)
absorption = footprint_bools.absorption_detected
imbalance = footprint_last_bar.imbalance_ratio

// Contrarian signal: delta OPPOSES direction = absorption at level
opposing = (direction == "LONG" and delta < 0) or
           (direction == "SHORT" and delta > 0)

if opposing AND abs_delta >= 200:
    fp_score = max_footprint                    // Strong absorption
elif opposing AND abs_delta >= 50:
    fp_score = max_footprint * 0.70             // Moderate absorption
elif absorption:
    fp_score = max_footprint * 0.60             // Boolean flag backup
elif abs_delta < 50:
    fp_score = max_footprint * 0.30             // Low delta = quiet, neutral
else:
    fp_score = 0                                // Confirming delta = not absorption

// Imbalance bonus (additive, capped at max_footprint)
if imbalance > 1.5:
    fp_score = min(fp_score + max_footprint * 0.20, max_footprint)

// abs_delta thresholds: 200/50 [TBD after observation]
```

**Worked example:** Footprint delta = -367, trade direction = LONG (sweep at support).
- V1: delta -367, direction LONG → opposing → 0 points
- V2: delta -367 opposes LONG, abs_delta 367 >= 200 → full 20 points. Heavy selling absorbed at the level = bullish absorption signal.

**Why less lagging / more predictive:** V1 treats opposing delta as disconfirmation. V2 recognizes that at key levels (where sweeps/rejections trigger), opposing delta IS the signal — it represents the aggressive flow being absorbed, which is the precondition for reversal. This directly addresses the Anti-Correlation: the setups that V1 scored lowest (opposing delta) are the ones most likely to work.

### 3.4 TPO — Structure Position (not direction)

**V1:** Awards points when price is on the "correct side" of POC relative to trade direction, plus bonus for being inside Value Area.

**V2:** Measures structural position only — where price sits relative to the day's developing profile, without directional bias. Being inside the Value Area is the strongest signal (efficient price = mean reversion probable). Being outside but near VAH/VAL is moderate. Being far from value = extended, less reliable.

**Formula:**

```
poc = tpo_current_day.poc_price
vah = tpo_current_day.vah or 0
val = tpo_current_day.val or 0

if vah > 0 AND val > 0:
    // Full TPO data available
    if val <= price <= vah:
        tpo_score = max_tpo                     // Inside Value Area
    elif abs(price - vah) <= 2.0 OR abs(price - val) <= 2.0:
        tpo_score = max_tpo * 0.60              // Near VA boundary
        // Proximity threshold: 2.0pt [TBD after observation]
    else:
        tpo_score = max_tpo * 0.25              // Extended from value
elif poc > 0:
    // POC only (VAH/VAL unavailable)
    dist_from_poc = abs(price - poc)
    if dist_from_poc <= 3.0:
        tpo_score = max_tpo * 0.50              // Near POC
    elif dist_from_poc <= 8.0:
        tpo_score = max_tpo * 0.30              // Moderate distance
    else:
        tpo_score = max_tpo * 0.10              // Far from POC
    // Distance thresholds: 3.0/8.0pt [TBD after observation]
else:
    tpo_score = 0                               // No TPO data
```

**Worked example:** TPO POC = 7259, price = 7261, VAH/VAL unavailable. Trade direction = SHORT.
- V1: price (7261) > POC (7259) → price above POC → SHORT direction = mismatch → 0 position points, plus partial VA points (VAH/VAL unavailable) → ~6 points
- V2: dist_from_poc = |7261 - 7259| = 2pt <= 3.0 → near POC → 25 * 0.50 = 12 points. Direction irrelevant — price is near fair value, which means the level is meaningful.

**Why less lagging / more predictive:** POC represents fair value for the day. Being near fair value means the market hasn't extended far in either direction — setups near POC have natural mean-reversion support regardless of trade direction. V1's directional bias penalized shorts near POC despite POC being exactly where reversals cluster.

---

## 4. Score Role Change

### V1 Role: Direction Filter
- Score >= 70 → trade (3 contracts)
- Score 50-69 → trade (2 contracts)
- Score < 50 → reject
- **Problem:** Score encodes directional agreement. High score = "everything agrees" = usually lagging confirmation of a move that already happened.

### V2 Role: Position Sizing Only
Direction is determined by triggers (Sweep, Rejection, FVG detection) and Day Type adapter. Score answers only: "How structurally sound is this environment?"

**New sizing tiers:**

| Score Range | Contracts | Action | Rationale |
|-------------|-----------|--------|-----------|
| 80-100 | 3 | FULL_SIZE | All structural components confirm: clear regime, clean FVGs, absorption present, near value |
| 60-79 | 2 | STANDARD | Most structural components favorable |
| 40-59 | 1 | MINIMUM | Mixed structure — trade with minimum risk |
| 0-39 | 0 | SKIP | Poor structure — no trade regardless of trigger quality |

**Threshold note:** These tiers are [TBD after observation]. The 40-point skip floor may move to 30 or 50 depending on data. The key design choice is that sizing tiers are wider than V1 (which had a hard cliff at 50/70), allowing more setups to execute at smaller size.

### Weight Distribution (V2 — unchanged totals, same day-type variation)

V2 keeps the same per-day-type weight distribution as V1. The weights determine how much each structural component matters — the change is WHAT each component measures, not how much it's weighted. Day-type variation is preserved because structure matters differently in trend vs range:

- TREND_DAY: Vegas 40 (wide tunnel = strong trend structure is the dominant signal)
- RANGE_DAY: TPO 35 (value area position matters most in range-bound markets)
- All types still sum to 100.

---

## 5. A/B Test Design

### Parallel Computation

Both V1 and V2 scores are computed for every setup, simultaneously. Neither score controls execution during the logging phase.

- **V1 score:** Written to existing `setup_quality_score` column (no change)
- **V2 score:** Written to NEW column `setup_quality_score_v2` (requires DB migration)

**DB migration sketch (NOT to be executed now):**

```
ALTER TABLE setups ADD COLUMN IF NOT EXISTS setup_quality_score_v2 INTEGER;
ALTER TABLE setups ADD COLUMN IF NOT EXISTS score_v2_breakdown JSONB;
ALTER TABLE setup_attempts ADD COLUMN IF NOT EXISTS setup_quality_score_v2 INTEGER;
```

### Data Collection Period

Minimum 5 trading days (target: 100+ setups with both scores).

### Metrics Tracked Per Bucket

For each score version, group setups into buckets: 0-39, 40-59, 60-79, 80-100.

Per bucket, track:
- Win rate (WR) — pnl_pts > 0
- Average PnL (gross and net)
- Average MAE (max adverse excursion)
- Trade count
- Correlation: does higher bucket = higher WR?

### Decision Rule

**V2 wins if ALL of the following are true:**

1. Score 70+ bucket WR > 50% across at least 100 setups scored by V2
2. V2 70+ bucket WR exceeds V1 70+ bucket WR by > 10 percentage points
3. V2 shows positive monotonic correlation: WR increases as score bucket increases (0-39 < 40-59 < 60-79 < 80-100 in WR)
4. V2 does not degrade the 40-59 bucket — WR in this bucket must not drop below V1's equivalent

**If conditions 1-2 pass but 3-4 fail:** investigate which component is causing non-monotonicity before proceeding.

### Rollback Rule

If after 200+ setups scored with both V1 and V2:
- V2 70+ bucket WR < V1 70+ bucket WR → revert to V1
- V2 shows no monotonic improvement → revert to V1 and re-examine component formulas
- Any single component shows zero variance (always awards same score) → that component's formula needs rework

---

## 6. Migration Plan

### Phase A — V2 Logger Only (5 trading days: 3-7/5 for observation, 11-15/5 for A/B)

- V2 score computed alongside V1 for every setup
- V2 score written to `setup_quality_score_v2` column
- V1 score continues to control sizing and execution decisions
- No behavior change for the user — purely additive logging

### Phase B — A/B Routing (5 trading days after Phase A passes)

- 50% of setups use V1 score for sizing, 50% use V2
- Assignment: alternating by setup_id hash (deterministic, reproducible)
- Both scores still logged for every setup (full data for comparison)
- Sizing tiers use whichever version is assigned

### Phase C — Full V2 Rollout

- If A/B decision rule passes → V2 becomes the sole scoring method
- `setup_quality_score` column populated by V2 logic
- `setup_quality_score_v2` column deprecated (kept for historical reference)
- V1 code retained behind feature flag for emergency rollback

### Feature Flag

```
ENV: QUALITY_SCORE_VERSION=v1|v2|ab

v1  — current behavior (default)
v2  — V2 only (Phase C)
ab  — both computed, 50/50 routing (Phase B)
```

### Rollback Procedure

1. Set `QUALITY_SCORE_VERSION=v1`
2. Restart backend
3. No data migration needed — V1 column was never modified

---

## 7. Open Questions

These require empirical answers from the 5-day observation period (3-7/5). The spec should be updated on 10/5 with findings before implementation on 11/5.

### Q1: Is the inverse-Vegas pattern stable?

The 30/4 data showed Score 70+ (where Vegas direction matched) had ~30% WR. Is this consistent across 5 days, or was it a single-day anomaly driven by a specific market condition (e.g., trend reversal day)?

**How to answer:** Track V1 Score 70+ WR per day for 5 days. If WR > 45% on 3+ days, the anti-correlation may be noise.

### Q2: Do contrarian Footprint signals work in trend days?

Absorption (opposing delta) is a reversal signal. On strong trend days, reversals fail. Does the contrarian footprint component degrade V2 scores on TREND_DAY?

**How to answer:** Bucket footprint-opposing-delta setups by day_type. If TREND_DAY + opposing delta WR < 30%, consider zeroing footprint weight on TREND_DAY.

### Q3: Does the FVG noise penalty hold cross-killzone?

High FVG counts may be normal during London open (high activity) but pathological during US afternoon. Is the penalty threshold (>5) killzone-dependent?

**How to answer:** Compare FVG count distribution and WR per killzone. If London regularly sees 8+ FVGs with good WR, the threshold needs killzone adjustment.

### Q4: What is the right TPO proximity threshold?

V2 uses 2.0pt for "near VA boundary" and 3.0/8.0pt for POC distance. These are guesses. MES ticks are 0.25pt — is 2.0pt (8 ticks) the right boundary for "near VAH/VAL"?

**How to answer:** Plot setup WR vs distance-from-VA-boundary. Find the natural breakpoint where WR drops.

### Q5: Should score have a time-decay component?

If a setup has been BUILDING for 30+ minutes without triggering, is it still valid? The current score is static — computed once at detection and never updated. A time-decay multiplier (e.g., score * 0.95^(minutes/10)) would reduce confidence in stale setups.

**How to answer:** Track time-from-detection-to-trigger for winning vs losing setups. If winners trigger within 15 minutes and losers linger for 30+, time-decay is justified.

### Q6: Should Vegas width thresholds be day-type adaptive?

A 3pt tunnel width means different things on TREND_DAY (normal) vs RANGE_DAY (unusually wide — possible breakout). Should the width thresholds in Section 3.1 vary by day type?

**How to answer:** Plot tunnel width distribution by day_type. If RANGE_DAY widths cluster below 2pt, the 3.0pt threshold should drop to 1.5pt for range days.

### Q7: Is the imbalance_ratio signal independent of absorption?

V2 awards an additive bonus for imbalance_ratio > 1.5 on top of absorption scoring. Are these redundant? If absorption_detected is always accompanied by high imbalance, the bonus is double-counting.

**How to answer:** Cross-tabulate absorption_detected vs imbalance_ratio > 1.5. If correlation > 0.8, merge into a single signal.

### Q8: What is the minimum setup count per bucket for statistical significance?

The A/B decision rule requires 100 setups in Score 70+. At current detection rate (~20 setups/day, ~30% scoring 70+), this takes ~17 trading days. Is 100 sufficient, or do we need 200 for confidence?

**How to answer:** Compute confidence intervals at N=100 and N=200. If the 95% CI for WR at N=100 spans more than 20 percentage points, we need more data.

---

## Appendix A — V1 vs V2 Side-by-Side (Morning State Example)

Market state from 30/4 morning debug:
- Vegas: BULLISH, width = 4.07pt
- TPO: POC = 7259, VAH/VAL unavailable
- FVG: bullish = 11, bearish = 5
- Footprint: delta = -367
- Price: ~7261
- Trade direction: LONG (sweep at support)

| Component | V1 Score (LONG) | V1 Reasoning | V2 Score (LONG) | V2 Reasoning |
|-----------|----------------|--------------|-----------------|--------------|
| Vegas (max 30) | 30 | BULLISH matches LONG, width 4.07 >= 0.5 | 30 | Width 4.07 >= 3.0 = clear structure |
| TPO (max 25) | ~18 | Above POC (7261>7259) + partial VA | 12 | POC dist 2pt <= 3.0 = near POC |
| FVG (max 25) | 25 | 11 bullish, many recent | 5 | 6+ recent = noise penalty |
| Footprint (max 20) | 0 | Delta -367 opposes LONG | 20 | Delta -367 opposing LONG = absorption |
| **Total** | **73** | | **67** | |

In this example, V1 scores 73 (FULL SIZE) largely because Vegas direction matches. V2 scores 67 (STANDARD size) — lower because FVG noise is penalized, but footprint is correctly rewarded. The score difference is modest here, but the _composition_ is radically different: V1's 73 depends entirely on directional agreement, while V2's 67 reflects structural quality.

For a **SHORT** in the same conditions:

| Component | V1 Score (SHORT) | V2 Score (SHORT) |
|-----------|-----------------|-----------------|
| Vegas | 0 (BULLISH opposes SHORT) | 30 (width 4.07, direction irrelevant) |
| TPO | ~6 (below POC mismatch + partial) | 12 (same — structure-only) |
| FVG | 0-15 (bearish FVGs: 5 total) | 5-25 (depends on recency of bearish FVGs) |
| Footprint | 14 (delta -367 confirms SHORT) | 0 (delta confirming = not absorption) |
| **Total** | **~20-35** | **~47-67** |

This is where V2 shines: a valid SHORT sweep in a bullish Vegas environment scores 20-35 in V1 (rejected) but 47-67 in V2 (1-2 contracts). V1 would have skipped this trade entirely. If the sweep was valid, V2 catches it.
