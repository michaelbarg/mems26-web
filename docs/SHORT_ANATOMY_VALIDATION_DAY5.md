# MEMS26 Q-Impl-1 SHORT Anatomy Empirical Validation — Day 5

**Generated:** 2026-05-07
**Branch:** feature/inventory-day5
**Data source:** Production API `/analytics/setups/closed` (N=1,973 closed setups, D-033 PnL)
**SHORT population:** 991 setups (48.0% WR, -$14,355 total, -$14.49/trade)
**Veto rule:** WR < 50% OR negative PnL (n > 30) → RE-DESIGN

---

## Data Limitations (CRITICAL — read first)

The following V2 SPEC fields are **NOT AVAILABLE** in the production data:

| Required Field | Status | Proxy Used |
|----------------|--------|------------|
| vegas_minutes_stable | ❌ MISSING | None — cannot filter. vegas_flips also unavailable. |
| tunnel_width_pts | ⚠️ PARTIAL | Parsed from score_reasons text where present (~60% populated) |
| poc_migration | ❌ MISSING | None — not stored in setups or attempts |
| time_in_session_min | ❌ MISSING | `minutes_into_session` is NULL for all setups. Killzone used as rough proxy. |
| price_distance_to_ema | ❌ MISSING | Not computed in production |
| level_name / level_price | ❌ EMPTY | `level_name` is empty string for ALL 991 SHORT setups |
| multi_day_high / PDH / ONH | ❌ MISSING | Cannot identify "near extreme" price location |
| bar history (multi-bar) | ❌ MISSING | No candle data in setups/attempts — can't detect breakout/return patterns |
| ib_high (Initial Balance) | ❌ MISSING | Not stored on setups |

**Impact:** Anatomies 2 and 3 cannot be precisely filtered. All verdicts for Anatomies 2-4 are flagged 🟡 minimum due to proxy imprecision.

---

## Anatomy 1: SHORT_TREND_CONTINUATION

### Filter conditions applied
1. `direction == 'SHORT'` ✅
2. `day_type == 'TREND_DAY'` ✅
3. `vegas_trend == 'BEARISH'` ✅ (parsed from score_reasons)
4. `vegas_minutes_stable >= 45` ❌ NOT AVAILABLE — no proxy
5. `tunnel_width <= 10` — not needed (all BEARISH have tunnel width)
6. `price near EMA(13/34/89)` ❌ NOT AVAILABLE — no proxy
7. `poc_migration == 'FALLING'` ❌ NOT AVAILABLE — no proxy
8. `killzone NOT IN ('London', 'NY_Close')` ✅

### Substitutions
- Conditions 4, 6, 7 cannot be applied. Result is LOOSER than spec.

### Results

**Strict filter (BEARISH + not London/NY_Close):**

| Metric | Value |
|--------|-------|
| N | **6** |
| WR | **0.0%** |
| Total PnL | **-$305.25** |
| Avg PnL | -$50.88 |
| Median PnL | -$55.50 |

**All 6 lost.** Zero wins.

**Context: ALL TREND_DAY SHORT (any Vegas):**

| Filter | N | WR | Total PnL | Avg PnL |
|--------|---|----|-----------|---------|
| TREND SHORT all | 56 | 53.6% | -$278 | -$4.97 |
| TREND SHORT BEARISH | 6 | 0.0% | -$305 | -$50.88 |
| TREND SHORT BULLISH (counter-trend) | 50 | **60.0%** | **+$27** | +$0.54 |

### Verdict: 🔴 RE-DESIGN

**Reasoning:** Only 6 BEARISH TREND_DAY SHORT setups exist in the data, and all 6 lost. The sample is too small for statistical significance BUT the direction is unambiguously negative. Meanwhile, the COUNTER-TREND group (BULLISH Vegas, n=50) has 60% WR and is the only profitable TREND SHORT pool.

**Root cause:** During a BEARISH TREND_DAY, the market is moving down strongly. A SHORT "trend continuation" means shorting into an already-extended move. The 6 samples suggest this catches the exhaustion point, not the continuation. The counter-trend SHORT (shorting during BULLISH TREND_DAY) performs better because it catches reversals at overextended highs.

**This anatomy's premise is empirically inverted.** TREND SHORT works AGAINST the Vegas trend, not with it.

---

## Anatomy 2: SHORT_REVERSAL_AT_EXTREME

### Filter conditions applied
1. `direction == 'SHORT'` ✅
2. `price near PDH/ONH/multi_day_high` ❌ **EMPTY** — `level_name` is blank for all 991 SHORT setups
3. `time_in_session >= 60` — proxy: `killzone NOT IN ('London')` ⚠️
4. `vegas_trend != 'BEARISH'` ✅ (counter-trend reversal)

### Substitutions
- Condition 2 (price near extreme): **CANNOT PROXY** — level_name empty. Used alternative filters instead:
  - `tpo_favors_direction` (price below POC = SHORT favorable position)
  - `footprint_delta < 0` (selling pressure)
  - `cvd_direction == 'BEARISH'` (cumulative selling)
- Condition 3: Killzone proxy (exclude London)

### Results

| Filter | N | WR | Total PnL | Avg PnL |
|--------|---|----|-----------|---------|
| Base (not BEARISH, not London) | 715 | 48.7% | -$7,621 | -$10.66 |
| + TPO favors direction | 211 | 45.5% | -$4,418 | -$20.94 |
| + Footprint delta negative | 304 | 39.8% | -$6,775 | -$22.29 |
| + TPO AND FP negative | 119 | 39.5% | -$3,252 | -$27.33 |
| + CVD bearish | 256 | 47.3% | -$3,693 | -$14.42 |
| + TPO AND FP AND CVD (triple) | 65 | 41.5% | -$1,761 | -$27.10 |

**Adding confluence filters makes SHORT WORSE, not better.** Each additional condition REDUCES WR and increases losses per trade. TPO+FP+CVD triple = worst at 41.5% WR, -$27/trade.

**However — the TREND_DAY BULLISH counter-trend group** (Anatomy 2's purest expression) shows:

| TREND_DAY SHORT + BULLISH Vegas | N | WR | Total PnL | Avg PnL |
|---------------------------------|---|----|-----------|---------|
| Score 0-49 | 45 | **60.0%** | **+$165** | +$3.67 |
| Score 50-69 | 3 | 100% | +$29 | +$9.50 |
| Score 70+ | 2 | 0% | -$167 | -$83.25 |

The reversal anatomy works **ONLY in TREND_DAY context** and **ONLY at low V1 scores** (which means Vegas opposes direction = exactly the contrarian signal). In NORMAL/DEVELOPING context, the same counter-trend SHORT pattern is noise.

### Verdict: 🔴 RE-DESIGN

**Reasoning:** The general "SHORT reversal at extreme" pattern fails across all confluence filters (39-49% WR, all negative PnL). The SPEC's preferred conditions (TPO+FP+CVD) produce the WORST results (41.5%, -$27/trade). However, the narrow TREND_DAY BULLISH SHORT with low score IS profitable (60% WR, n=45). The anatomy needs to be scoped to TREND_DAY only, not as a general reversal pattern.

---

## Anatomy 3: SHORT_FAILED_BREAKOUT_FADE

### Filter conditions applied
1. `direction == 'SHORT'` ✅
2. `day_type IN ('RANGE_DAY', 'BROAD_CHANNEL')` ✅ (only RANGE_DAY in data — 0 BROAD_CHANNEL)
3. `recent breakout above resistance` ❌ **CANNOT PROXY** — no bar history
4. `price returned below resistance` ❌ **CANNOT PROXY**
5. `volume at breakout < 1.2× avg` — proxy: `rel_vol_at_entry < 1.2` ⚠️
6. `vegas_trend != 'BULLISH' OR unstable` — all RANGE SHORT have BULLISH Vegas (0 non-BULLISH)

### Substitutions
- Conditions 3-4 (breakout/return pattern): **CANNOT PROXY** — no bar history in setups data. Using RANGE_DAY SHORT with low rel_vol as extremely loose proxy.
- Condition 6: All 88 RANGE SHORT have BULLISH Vegas, making this filter useless.

### Results

| Filter | N | WR | Total PnL | Avg PnL |
|--------|---|----|-----------|---------|
| RANGE SHORT all | 88 | 52.3% | -$1,082 | -$12.30 |
| RANGE SHORT + rel_vol < 1.2 | 87 | 51.7% | -$1,104 | -$12.69 |
| RANGE SHORT + not strong BULL | 0 | — | — | — |

### Verdict: 🟡 INSUFFICIENT DATA (proxy too imprecise)

**Reasoning:** Cannot test this anatomy. The core pattern (breakout → failure → fade) requires multi-bar history that the production data doesn't store. The RANGE_DAY SHORT population (n=88) is above VETO threshold but the proxy is too loose — we're testing "any SHORT in RANGE_DAY" not "breakout fade specifically." WR of 52.3% with negative PnL (-$12.30/trade) suggests the general pattern is marginal before specific breakout-failure filtering.

**Note:** RANGE SHORT above VWAP (n=26, 65.4% WR, +$89.50) is the one profitable sub-group — this overlaps with Anatomy 4 and should be considered there.

---

## Anatomy 4: SHORT_RANGE_FADE_HIGH

### Filter conditions applied
1. `direction == 'SHORT'` ✅
2. `day_type == 'RANGE_DAY'` ✅
3. `price near VAH/IBH` — proxy: `vwap_side == 'above'` ⚠️ (above VWAP = upper half of range)
4. `poc_migration IN ('STUCK', 'OSCILLATING')` ❌ NOT AVAILABLE
5. `no recent breakout` ❌ NOT AVAILABLE

### Substitutions
- Condition 3: `vwap_side == 'above'` as proxy for "near top of range." Above VWAP approximates upper half of value area.
- Conditions 4-5: Cannot filter. Results are looser than spec.

### Results

| Filter | N | WR | Total PnL | Avg PnL | Median PnL |
|--------|---|----|-----------|---------|------------|
| RANGE SHORT all | 88 | 52.3% | -$1,082 | -$12.30 | +$14.50 |
| RANGE SHORT above VWAP | **26** | **65.4%** | **+$89.50** | **+$3.44** | +$19.50 |
| RANGE SHORT below VWAP | 62 | 46.8% | -$1,172 | -$18.89 | -$27.75 |
| Above VWAP + FP not opposing | 8 | 75.0% | +$52.75 | +$6.59 | +$19.50 |

**Sharp split:** RANGE SHORT above VWAP = 65% WR, +$90. Below VWAP = 47%, -$1,172. The VWAP side is a powerful discriminator.

### Verdict: 🟡 INSUFFICIENT DATA (n=26 < 30 threshold)

**Reasoning:** The signal is strong — 65.4% WR with positive PnL is the only profitable SHORT anatomy found. But n=26 is below the 30-trade minimum for a 🟢 verdict. The pattern is directionally convincing (above VWAP = +$3.44, below = -$18.89 — a $22 swing per trade) but needs more data to confirm.

With FP-not-opposing added (n=8, 75% WR), the quality improves but sample is even smaller. Flag for Phase A shadow validation.

---

## Q-Impl-1 Validation Summary

| Anatomy | N | WR | Total PnL | Verdict | Notes |
|---------|---|----|-----------|---------|-------|
| 1. SHORT_TREND_CONTINUATION | 6 | 0.0% | -$305 | 🔴 RE-DESIGN | BEARISH TREND SHORT = 0 wins. Counter-trend (BULLISH) SHORT at low score = 60% WR. Anatomy premise is inverted. |
| 2. SHORT_REVERSAL_AT_EXTREME | 119 | 39.5% | -$3,252 | 🔴 RE-DESIGN | Confluence filters make it worse. Only works in narrow TREND_DAY + BULLISH + low-score context (n=45, 60% WR). |
| 3. SHORT_FAILED_BREAKOUT_FADE | 87 | 51.7% | -$1,104 | 🟡 INSUFFICIENT (proxy too imprecise) | Cannot test core pattern without bar history. General RANGE SHORT is marginal. |
| 4. SHORT_RANGE_FADE_HIGH | 26 | 65.4% | +$90 | 🟡 INSUFFICIENT (n=26 < 30) | Strong signal but below n threshold. VWAP-above is a powerful filter. |

---

## Sprint 3.3 Decision Gate

**BLOCKED on Anatomies 1 and 2.** Both require re-design before Day 9 (12/5).

---

## Key Discovery: The One Profitable SHORT Pattern

Across all filters tested, only TWO SHORT sub-populations are profitable:

1. **TREND_DAY + BULLISH Vegas + Score 0-49** (n=45, 60% WR, +$165)
   - This is a counter-trend reversal SHORT during a BULLISH uptrend
   - Low score because Vegas BULLISH gives 0pts to SHORT direction
   - This is EXACTLY the pattern V2 was designed to capture

2. **RANGE_DAY + above VWAP** (n=26, 65.4% WR, +$90)
   - Fading the top of a range day
   - VWAP position is the discriminator, not confluence filters

Both share a key trait: **they are contrarian.** They SHORT when the environment appears bullish (uptrend day, above VWAP). The V1 score penalizes them for this, but it's precisely what makes them work.

---

## Recommendations for V2 SPEC Re-design

### Anatomy 1 (SHORT_TREND_CONTINUATION) → REPLACE or INVERT

The spec assumes SHORT works with BEARISH trends. The data says the opposite: SHORT only works AGAINST BULLISH trends (on TREND_DAY). Options:
- **Option A:** Remove Anatomy 1 entirely — SHORT has no trend-continuation edge
- **Option B:** Redefine as SHORT_TREND_REVERSAL: SHORT during BULLISH TREND_DAY at extreme high, low V1 score (which V2 would score higher via direction-agnostic Vegas)
- **Recommended:** Option B — this IS the V2 insight in action

### Anatomy 2 (SHORT_REVERSAL_AT_EXTREME) → NARROW SCOPE

The general pattern fails but the narrow version works. Re-scope to:
- TREND_DAY only (not NORMAL/DEVELOPING)
- No confluence stacking (TPO+FP+CVD makes it worse)
- Rely on context (TREND_DAY at extremes) not indicator confirmation
- Consider merging with revised Anatomy 1 into a single "SHORT_TREND_REVERSAL" anatomy

### Anatomy 3 (SHORT_FAILED_BREAKOUT_FADE) → DEFER

Cannot validate without bar history. Don't implement blind. Either:
- Add bar history to setup logging (Sprint 3.3 infrastructure)
- Defer to Phase B when more data accumulates

### Anatomy 4 (SHORT_RANGE_FADE_HIGH) → PROCEED with monitoring

Promising signal (65% WR). Implementation should:
- Use VWAP side as primary discriminator (not POC migration which isn't available)
- Set n < 30 flag for Phase A shadow monitoring
- Consider single-contract sizing until n > 50 validates

---

## Data Limitations Summary

| Gap | Impact | Mitigation |
|-----|--------|------------|
| `level_name` empty for all SHORT | Cannot filter by proximity to PDH/ONH/VAH etc. Anatomies 2-3 severely impacted. | Bridge needs to write `level_name` to setups table. Currently only populated for some setup_types. |
| `minutes_into_session` NULL | Cannot filter by session time | Compute from `first_detected_ts` using ET timezone |
| `poc_migration` not stored | Cannot filter for STUCK/OSCILLATING POC | Need new field: compare POC values across last N observations |
| No bar history on setups | Cannot detect breakout/return patterns | Store last-5-bar summary at setup detection time |
| `vegas_minutes_stable` not stored | Cannot filter for trend stability | Count vegas_flips_today or compute from bridge data |
| Only 2.5 days of TREND_DAY data | n=100 total, n=56 SHORT | More data needed before LIVE. Flag for extended shadow period. |
