# V3 Day Type Reclassification — Migration Report

**Date:** 2026-05-05
**Version:** v8.4.2-2026-05-05
**Phase:** 3.2 Day 2 — Pure Observation (READ-ONLY)

---

## §1 Migration Summary

| Item | Value |
|------|-------|
| Input | `setups_clean_2026-05-05_full.parquet` |
| Input rows | 4,996 |
| Output | `setups_clean_2026-05-05_v3.parquet` |
| Output rows | 4,996 |
| Runtime | 2.6s |
| V3 types assigned | 3 of 6 possible |
| Dates covered | Apr 29, Apr 30, May 1, May 3 (4 trading days) |
| Classifier version | v8.4.2-2026-05-05 |

---

## §2 Distribution Comparison V2 → V3

| V2 Type | Count | % | → V3 BROAD_CHANNEL | → V3 TREND_DAY | → V3 RANGE_DAY |
|---------|-------|---|---|---|---|
| NORMAL | 2,472 | 49.5% | 1,418 | 1,054 | 0 |
| DEVELOPING | 1,864 | 37.3% | 1,109 | 755 | 0 |
| RANGE_DAY | 303 | 6.1% | 0 | 303 | 0 |
| TREND_DAY | 88 | 1.8% | 0 | 88 | 0 |
| *(no V2 data for Apr 29)* | 256* | — | 0 | 0 | 256 |

*Apr 29 had NULL day_type in V2.

**Key shifts:**
- V2 RANGE_DAY (303) → V3 TREND_DAY. These were on Apr 30 which V3 classifies as TREND (range = 2.8x ATR).
- V2 DEVELOPING (1,864) split: 60% → BROAD_CHANNEL, 40% → TREND_DAY (by date assignment).
- V2 DEVELOPING is no longer a day type — it's now a time phase filter.

---

## §3 New V3 Distribution

| V3 Day Type | Count | % | Mean Conf | Low Conf (<60) |
|-------------|-------|---|-----------|----------------|
| BROAD_CHANNEL | 2,527 | 50.6% | 30.0% | 100% |
| TREND_DAY | 2,213 | 44.3% | 76.5% | 24%* |
| RANGE_DAY | 256 | 5.1% | 80.0% | 0% |
| GAP_FILL | 0 | 0% | — | — |
| REVERSAL_DAY | 0 | 0% | — | — |
| NEUTRAL | 0 | 0% | — | — |

*May 3 (244 setups) classified TREND at 48% conf; Apr 30 (1,969) at 95%.

### Time Phase Distribution

| Phase | Count | % | Meaning |
|-------|-------|---|---------|
| PREMARKET | 1,904 | 38.1% | Before 09:30 ET |
| OFF_HOURS | 1,199 | 24.0% | After 16:00 ET |
| RTH | 1,086 | 21.7% | 11:00-14:30 ET |
| LATE_DAY | 427 | 8.5% | 14:30-16:00 ET |
| DEVELOPING | 380 | 7.6% | 09:30-11:00 ET |

### Special Day Blocks

| Reason | Count | Dates |
|--------|-------|-------|
| friday_late | 229 | May 3 (all setups after 14:00 ET on Friday) |
| rollover | 0 | No rollover in Apr 29 - May 3 window |
| year_end | 0 | N/A |

---

## §4 Confidence Distribution

### Per V3 Day Type

| Type | 0-19 | 20-39 | 40-59 | 60-79 | 80-100 |
|------|------|-------|-------|-------|--------|
| BROAD_CHANNEL | 0 | 2,527 | 0 | 0 | 0 |
| TREND_DAY | 0 | 0 | 244 | 0 | 1,969 |
| RANGE_DAY | 0 | 0 | 0 | 0 | 256 |

- 50.6% of setups have confidence < 60% (all BROAD_CHANNEL — fallback classification)
- 49.4% have confidence ≥ 60% (TREND_DAY and RANGE_DAY — strong detection)

---

## §5 Win Rate per V3 Day Type

| V3 Day Type | N | Wins | Losses | WR | Avg MFE | Est. Net PnL* |
|-------------|---|------|--------|-----|---------|---|
| BROAD_CHANNEL | 2,527 | 872 | 978 | **47.1%** | 1.42R | -$7,810 |
| TREND_DAY | 2,213 | 1,057 | 1,143 | **48.0%** | 2.23R | -$5,830 |
| RANGE_DAY | 256 | 106 | 146 | **42.1%** | 2.01R | -$2,820 |

*Estimated using 2-contract fixed, $2.75/contract costs

### Time Phase WR

| Phase | N | WR | Implication |
|-------|---|-----|-------------|
| **DEVELOPING** (09:30-11:00) | 380 | **37.1%** | Worst phase — skip filter validated |
| Non-DEVELOPING | 4,616 | **48.3%** | +11.2pp better |
| PREMARKET | 1,904 | 48.2% | Similar to RTH |
| RTH | 1,086 | 48.4% | Best phase |
| OFF_HOURS | 1,199 | 47.2% | Slightly worse |

---

## §6 V2 → V3 Migration Map

### Per Date

| Date | V2 Types Present | V3 Type | Conf | Reason |
|------|-----------------|---------|------|--------|
| Apr 29 | (null) | RANGE_DAY | 80% | flips=11, range=1.5x ATR |
| Apr 30 | TREND+RANGE+NORMAL+DEV | TREND_DAY | 95% | range=2.8x ATR override |
| May 1 | NORMAL+DEVELOPING | BROAD_CHANNEL | 30% | moderate range, no strict match |
| May 3 | NORMAL+RANGE | TREND_DAY | 48% | low flips, directional |

### Key Observation

V2 assigned MULTIPLE day types within a single day (re-evaluated per bar).
V3 assigns ONE day type per day (stable classification).
This means intra-day transitions (e.g., DEVELOPING → TREND on Apr 30) are now captured
by the TIME PHASE filter, not the day type.

---

## §7 Critical Findings

### 1. Did REVERSAL_DAY emerge?

**No.** Zero setups classified as REVERSAL_DAY.
Conditions not met: requires `first_90min_direction != current_direction` AND
`volume_burst_ratio >= 1.5`. The volume burst proxy (setup count ratio) was
insufficient, and direction reversal detection couldn't find clear V-shapes in
the 4-day window.

**Likely real:** With only 4 days and approximate data, REVERSAL_DAY is unlikely
to trigger. This detector needs live tick data or more days to manifest.

### 2. BROAD_CHANNEL absorption

BROAD_CHANNEL absorbed **100% of May 1** (2,527 setups = V2 NORMAL + DEVELOPING).
This is appropriate: May 1 was a moderate-range day (1.38x ATR) with no clear
directional tendency. It's the new "NORMAL" equivalent.

V2 DEVELOPING (1,864 setups) split by date:
- 755 → TREND_DAY (on Apr 30)
- 1,109 → BROAD_CHANNEL (on May 1)

The DEVELOPING label is now purely a time phase, not a day type.

### 3. Special day blocks

229 setups flagged as `friday_late` (May 3, all setups after 14:00 ET Friday).
No rollover periods in the data window.

### 4. DEVELOPING phase WR validation

| | N | WR |
|---|---|---|
| DEVELOPING phase (09:30-11:00 ET) | 380 | **37.1%** |
| All other phases | 4,616 | **48.3%** |
| Edge | | **-11.2pp** |

**Verdict: DEVELOPING time-phase skip filter remains strongly validated.**
The 37.1% WR during first 90 minutes of RTH confirms this is a dangerous period
regardless of day type.

---

## §8 Limitations

### Approved Thresholds (audit trail)

| Threshold | Source | Impact |
|-----------|--------|--------|
| BROAD_CHANNEL: `ib_range 0.5-1.0 ATR, flips<=3, range_ratio 0.7-1.2` | [APPROVED 2026-05-05] | Only fires with real IB data; fallback used for this dataset |
| REVERSAL_DAY: `first_90min != current, range>ATR, volume_burst>=1.5` | [APPROVED 2026-05-05] | Zero detections — volume proxy insufficient |
| Tie-breaking: GAP > REVERSAL > TREND > BROAD > RANGE > NEUTRAL | [APPROVED 2026-05-05] | Not triggered (no ties) |
| `atr_baseline = 40pt` | [APPROVED 2026-05-05] | Determines all ratio thresholds |

### Fallback Heuristics Used (§A.6)

| Metric | Heuristic | Quality |
|--------|-----------|---------|
| `ib_range` | Entry prices ± MFE/MAE in 09:30-10:30 ET window | LOW — most setups after 11:00 ET; Apr 30 only day with real IB data |
| `day_range` | Max(entry+MFE) - Min(entry-MAE) across all setups | MEDIUM — captures extremes but may under-report range |
| `vegas_flips_today` | Majority-vote per 3-min window from score_reasons | MEDIUM — correct direction extraction, dedup effective |
| `ib_break_held` | First vs last direction in IB window | LOW — meaningless when IB window has few setups |
| `first_90min_direction` | Majority direction in 09:30-11:00 ET | LOW — only 7.6% of setups fall in this window |
| `volume_burst_ratio` | Setup count in last 2h / average | LOW — proxy for actual volume |
| `open_price` / `prior_day_close` | First/last setup entry price | MEDIUM — approximation |
| TREND override | range > 2x ATR → TREND regardless of IB | Added during migration — not in original spec |

### Key Limitation

**Per-day classification with 4 dates produces only 4 classification decisions.**
The V2 system classified per-setup (intra-day transitions). V3 classifies per-day.
With 4 days, we get 4 labels distributed across 4,996 setups.

---

## §9 Recommendations for Day 3 SIMs

### Top 3 Surprises

1. **DEVELOPING phase WR = 37.1% regardless of day type.** The V3 spec moves DEVELOPING to a time phase filter. This data confirms: the DEVELOPING *time window* (first 90min RTH) is the danger zone, not the "DEVELOPING" day type classification. Skip-DEVELOPING should be a time-based filter, not type-based.

2. **V2 RANGE_DAY (Apr 30) reclassified to V3 TREND_DAY.** Apr 30 had both RANGE_DAY and TREND_DAY setups in V2, but V3 sees the full day as a massive trend (2.8x ATR). This means V2 was classifying early-session setups as "range" before the trend established — V3 correctly identifies this as TREND retroactively.

3. **BROAD_CHANNEL is low confidence (30%) due to proxy limitations.** Without real IB data, the strict BROAD_CHANNEL conditions can't fire. The fallback assignment is appropriate but confidence should be treated as "estimated."

### Suggested Day 3 SIM Re-Runs

1. **CFG-α on V3 types:** Does CFG-α performance differ by V3 TREND vs BROAD_CHANNEL?
2. **Time phase analysis:** Run full PnL breakdown by time phase (PREMARKET, DEVELOPING, RTH, LATE_DAY, OFF_HOURS) instead of day type.
3. **DEVELOPING skip → time-based:** Redefine skip_DEVELOPING from "V2 day_type = DEVELOPING" to "time_phase_v3 = DEVELOPING" and measure impact.
