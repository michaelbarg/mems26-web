# Phase 3.2 Day 1 Review — 2026-05-04 (Pure Observation)

**Version:** V8.1.11  
**Session:** Phase 3.2 Day 1 — Pure Observation  
**Generated:** 2026-05-05 ~01:00 IDT  

---

## Executive Summary

Day 1 of Phase 3.2 ran the full NY session with zero bridge errors and continuous uptime (26+ hours). The system detected **408 total setups**, of which **336 closed** and **72 remain open** at EOD.

**Key numbers (all setups, no filters):**
- Win rate: **28.6%** (96W / 207L / 33BE)
- Net PnL: **-$7,904** (gross -$5,853, costs -$2,052)
- Avg PnL per trade: **-$17.42**
- Best trade: SHORT `802aeafc` → +$183.75 (T2_PARTIAL_STOP)
- Worst trade: LONG `48d7fd3a` → -$213.75 (STOP)

**Sequential V2 simulation (with filters applied):**
- Executed: **101** of 408 (skipped 307)
- Sequential PnL: **-$2,511** (still negative but ~68% less drawdown than unfiltered)
- Sequential WR: **25.0%**

**Verdict: The system ran flawlessly from an infrastructure standpoint. Trade quality remains poor — the unfiltered fire-everything mode confirms why V2 filters exist.**

---

## 1. System Health

| Metric | Value |
|--------|-------|
| Bridge uptime | **26h 10m 36s** (01-02:10:36) |
| Bridge errors | **0** |
| Bridge INFO entries | **364,877** |
| CRITICAL/crash events | **0** |
| daily_check.sh | Script not found (not critical) |
| TRIGGERS gap analysis | Insufficient data in log format |

**Assessment:** Infrastructure health is **excellent**. Zero errors across 364K+ log entries. Bridge has been running continuously for over 26 hours with no restarts, disconnects, or crashes.

---

## 2. Activity Overview

### 2.1 Full Day Summary (Unfiltered)

| Metric | Value |
|--------|-------|
| Total setups detected | 408 |
| Closed | 336 |
| Still open | 72 |
| Wins | 96 |
| Losses | 207 |
| Breakeven | 33 |
| Win rate | 28.6% |
| Net PnL | -$7,904.00 |
| Gross PnL | -$5,852.50 |
| Total costs | -$2,051.50 |
| Avg PnL/trade | -$17.42 |

### 2.2 Sequential Simulation (V2 Logic)

| Metric | Value |
|--------|-------|
| Executed (sim) | 101 |
| Skipped | 307 |
| — LOW_SCORE | 126 |
| — COOLDOWN | 119 |
| — FOOTPRINT_OPPOSES | 54 |
| — OTHER_TRADE_OPEN | 8 |
| Sequential PnL | -$2,511.25 |
| Sequential WR | 25.0% |
| Executed closed | 92 |
| Executed still open | 9 |

### 2.3 By Killzone (All-Time Cumulative)

| Killzone | Count | WR | Avg MFE | Avg MAE |
|----------|------:|---:|--------:|--------:|
| NY_Close | 225 | 48.4% | 10.46 | 10.52 |
| UNKNOWN | 810 | 48.0% | 10.25 | 10.74 |
| OFF_HOURS | 3,363 | 39.4% | 8.76 | 8.39 |
| NY_Open | 244 | 39.3% | 16.68 | 16.73 |
| London | 250 | 26.4% | 35.61 | 5.65 |

**Note:** London has worst WR (26.4%) — V2 correctly skips it.

### 2.4 By Day Type (All-Time Cumulative)

| Day Type | Count | WR | Avg MFE | Avg MAE |
|----------|------:|---:|--------:|--------:|
| TREND_DAY | 92 | 52.2% | 11.44 | 10.10 |
| NORMAL | 2,408 | 42.0% | 8.35 | 8.11 |
| UNKNOWN | 327 | 41.9% | 9.65 | 12.30 |
| RANGE_DAY | 179 | 40.8% | 12.68 | 12.66 |
| DEVELOPING | 1,884 | 38.0% | 13.73 | 9.56 |

**Note:** DEVELOPING has lowest WR (38%) — V2 correctly skips it.

### 2.5 By Score Bucket (All-Time Cumulative)

| Bucket | Count | WR | Avg MFE | Avg MAE |
|--------|------:|---:|--------:|--------:|
| 30-49 | 2,317 | 32.4% | 12.25 | 8.82 |
| 70+ | 2,853 | 21.1% | 9.45 | 8.58 |
| 50-69 | 3,238 | 18.6% | 11.51 | 9.48 |
| <30 | 729 | 4.3% | 4.44 | 17.22 |

**Concern:** Score buckets show an **inverted relationship** — lower scores (30-49) have *higher* WR than 70+. This suggests the scoring model needs recalibration. The <30 bucket correctly identifies trash (4.3% WR), but 50-69 and 70+ don't differentiate well.

---

## 3. Trade-by-Trade Analysis

*Note: API returned 200 of 336 closed setups. Analysis below covers the 200 most recent.*

### 3.1 Session Breakdown (200 sampled trades)

**Pre-NY / OFF_HOURS / DEVELOPING (13:34–17:24 IDT):** ~93 setups
- Dominated by DEVELOPING + OFF_HOURS — the worst combination
- Pattern: system fires LONG+SHORT simultaneously every 5 minutes
- Heavy losses on LONGs getting stopped, some SHORT T2 partial wins

**Post-Classification Switch to NORMAL (~17:30+ IDT):** ~107 setups
- Day type switched from DEVELOPING to NORMAL
- Slightly more SHORT winners via T2_PARTIAL_STOP
- Still very high STOP rate on one side of each pair

**NY_Close (21:59–22:54 IDT):** ~11 setups
- All 11 hit STOP — **0% win rate in NY Close today**
- Most were high-score (85-100) setups that still lost

### 3.2 Key Observations

1. **Dual-direction firing:** System fires LONG+SHORT simultaneously at same price every 5 min. One will always lose. This is by design for observation, but inflates loss count.
2. **T2_PARTIAL_STOP is the best exit:** Most wins come from this exit type.
3. **STOP is dominant loss reason:** Nearly all losses are full stops.
4. **Price range was tight:** NQ ranged ~7208–7269 (61 pts). Choppy session.

### 3.3 Open Setups at EOD

**37 setups** still LIVE or BUILDING at EOD, clustered around 7223-7228.
- Mix of LONG and SHORT, scores ranging 33-100
- Most have 4-5 observations (recently opened)

---

## 4. V2 Filter Analysis

*Based on 200 sampled closed setups:*

| Filter | Setups Removed | PnL Saved |
|--------|---------------|-----------|
| Skip DEVELOPING | 93 | Would remove bulk of OFF_HOURS losses |
| Skip London | 0 | No London setups in today's sample |
| **V2 would trade** | **107** | |
| V2 net PnL | | **-$2,898.75** |
| V2 W/L | | 29W / 78L (27.1% WR) |

**Full-day sequential simulation (all 408 setups):**
- V2 sequential execution: 101 trades, PnL: **-$2,511.25**, WR: **25.0%**
- Skip reasons: LOW_SCORE (126), COOLDOWN (119), FOOTPRINT_OPPOSES (54), OTHER_TRADE_OPEN (8)

**Analysis:** V2 filters reduce drawdown by ~68% vs unfiltered, but **still negative**. The COOLDOWN filter (119 skips) is working hard to prevent rapid-fire entries. FOOTPRINT_OPPOSES (54 skips) adds meaningful protection. However, the remaining trades still have poor edge.

---

## 5. Component Scoring Insights

### 5.1 Component Correlation (Win vs Loss avg scores)

| Component | Avg When Win | Avg When Loss | Delta | Assessment |
|-----------|:-----------:|:------------:|:-----:|------------|
| FVG | 23.4 | 23.7 | -0.3 | No signal (near-zero delta) |
| Vegas | 13.6 | 14.3 | -0.7 | Minimal signal |
| TPO | 12.3 | 13.6 | -1.3 | Slight inverse signal |
| Footprint | 9.0 | 11.2 | -2.2 | Best discriminator (still weak) |

**Ranking by predictive value:** FVG > Vegas > TPO > Footprint

**Critical finding:** All components show **negative deltas** — higher scores actually correlate with *losses* more than wins. This confirms the inverted score-bucket WR pattern from Section 2.5. The scoring system as currently calibrated does not predict winners.

### 5.2 Pattern Analysis

Top pattern: LIQUIDITY_SWEEP (no killzone) — 12 trades, 83% WR, +4.08 avg pts
- This is the only high-confidence pattern in the dataset
- SWEEP_VAH_MANUAL (OUTSIDE) — 2 trades, 100% WR but tiny sample

---

## 6. Issues for Phase 3.3

### Critical
1. **Scoring model is inverted** — Higher scores correlate with losses. All 4 component deltas are negative. Score buckets 70+ have lower WR (21.1%) than 30-49 (32.4%). This is the #1 issue to address.

### Important
2. **Dual-direction firing** inflates metrics — firing LONG+SHORT simultaneously guarantees ~50% loss rate before any edge. Need to decide: is this intentional for observation or a design issue?
3. **NY_Close was 0% WR today** — 11 setups, all stopped out. Consider whether NY_Close should be filtered.
4. **V2 still negative** — Even with all filters active, sequential sim shows -$2,511. Filters reduce damage but don't create edge.

### Monitor
5. **OFF_HOURS dominance** — 3,363 of 4,892 cumulative setups (69%) are OFF_HOURS. System is most active when it shouldn't be trading.
6. **COOLDOWN doing heavy lifting** — 119 of 307 skips are cooldown. This prevents rapid-fire but masks the root cause (too many signals).

---

## 7. Tomorrow's Plan (Phase 3.2 Day 2)

- Continue pure observation — **DO NOT** change bridge, config, or code
- Monitor for same patterns (dual-direction, score inversion, OFF_HOURS dominance)
- Compare Day 2 distribution vs Day 1 for consistency
- Begin documenting scoring recalibration plan for Phase 3.3
- Note: Bridge has been running 26+ hours — monitor for memory/stability issues as it ages

---

*Report generated automatically. All data is read-only observation — no trades were executed, no configuration was changed.*
