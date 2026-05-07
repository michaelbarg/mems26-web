# MEMS26 Hypothesis Validation — Day 5

**Generated:** 2026-05-07
**Branch:** feature/inventory-day5
**Data source:** Production API (`https://mems26-web.onrender.com`)
**Endpoints:** `/analytics/attempts/with_outcomes` (N=10,563 attempts, 8,633 resolved)
**PnL method:** Estimated from outcome + R value (HIT_C1 = +1R, HIT_C2 = +2R, HIT_STOP = -1R, $5/pt MES)

---

## Query 1 — DEVELOPING day_type true performance

### Context

Contradiction between two sources:
- **Day 4 SIM-DEEP-ANALYSIS:** DEVELOPING anti-pattern, 37% WR, -$4.58/trade
- **Inventory §9 Q7:** "DEVELOPING is profitable (56.4% WR, +$100)"

The Inventory figure came from the earlier `analysis/V8.2.2_day_type_breakdown.md` which used a smaller, earlier dataset. This query uses the full production attempt history.

### Raw DEVELOPING (all resolved)

| Metric | Value |
|--------|-------|
| Count | 3,835 |
| Wins | 1,827 |
| Losses | 2,008 |
| WR | **47.6%** |
| Total PnL | **-$4,305** |
| Avg PnL/trade | **-$1.12** |

### DEVELOPING after light filter (kz ∈ {NY_Open, OFF_HOURS}, score >= 70)

| Metric | Value |
|--------|-------|
| Count | 1,072 |
| WR | **49.0%** |
| Total PnL | **-$444** |
| Avg PnL/trade | **-$0.41** |

Filtering improves WR from 47.6% to 49.0% and avg PnL from -$1.12 to -$0.41, but DEVELOPING remains net negative even after filtering.

### Direction split

| Direction | N | WR | Total PnL | Avg PnL |
|-----------|---|----|-----------|---------|
| LONG | 1,955 | **48.4%** | -$1,300 | -$0.66 |
| SHORT | 1,880 | **46.9%** | -$3,005 | -$1.60 |

SHORT on DEVELOPING is significantly worse (-$1.60/trade vs -$0.66).

### Killzone split

| Killzone | N | WR | Total PnL | Avg PnL |
|----------|---|----|-----------|---------|
| London | 638 | **49.2%** | -$124 | -$0.19 |
| NY_Open | 478 | **41.6%** | -$1,868 | **-$3.91** |
| OFF_HOURS | 2,240 | **47.6%** | -$2,739 | -$1.22 |
| UNKNOWN | 479 | **51.8%** | +$425 | +$0.89 |

**DEVELOPING + NY_Open is catastrophic:** 41.6% WR, -$3.91/trade. This is the worst combination in the data.

### Score bucket split (DEVELOPING only)

| Score Bucket | N | WR | Total PnL | Avg PnL |
|-------------|---|----|-----------|---------|
| 0-49 | 1,174 | **60.1%** | **+$6,260** | **+$5.33** |
| 50-69 | 1,364 | **38.1%** | -$8,196 | -$6.01 |
| 70+ | 1,297 | **46.3%** | -$2,369 | -$1.83 |

**Inverted score-WR correlation confirmed on DEVELOPING too.** Low-score DEVELOPING setups (0-49) have 60% WR and are massively profitable (+$6,260). High-score (70+) setups lose money. This mirrors the NORMAL day anti-correlation found in Day 2 analysis.

### VERDICT

**Hypothesis: "DEVELOPING is universally bad" — CONDITIONAL**

DEVELOPING is net negative overall (-$4,305) but this is driven by the **score anti-correlation** (same as NORMAL days). Low-score DEVELOPING setups are highly profitable. The problem is not DEVELOPING itself — it's the Quality Score V1 direction bias (Vegas 30pts dominates, making high scores = Vegas-aligned = stale momentum signal).

**Key insight:** Blocking DEVELOPING entirely would sacrifice $6,260 in profit from the 0-49 score bucket. The correct fix is Score V2 (direction-agnostic), not a day-type blanket block.

---

## Query 2 — Score 70 hardcoded vs day-adaptive thresholds

### Context

`backend/main.py:658` uses hardcoded `score < 70` as execution threshold for ALL day types. But `day_config.py` defines:
- TREND_DAY: full_size = 60
- GAP_FILL: full_size = 65
- RANGE_DAY / NORMAL / DEVELOPING: full_size = 70

Hypothesis: The hardcoded 70 drops TREND_DAY setups with scores 60-69 that the day-adaptive module considers executable.

### TREND_DAY trades with score 60-69 (rejected by hardcode)

| Metric | Value |
|--------|-------|
| Count | **11** |
| WR | **45.5%** |
| Total PnL | **-$67.50** |
| Avg PnL | **-$6.14** |

### GAP_FILL trades with score 65-69 (rejected by hardcode)

| Metric | Value |
|--------|-------|
| Count | **0** |

No GAP_FILL attempts exist in the 65-69 score range.

### Combined "lost opportunity" pool

| Metric | Value |
|--------|-------|
| Count | **11** |
| Total PnL if executed | **-$67.50** |

### TREND_DAY score distribution (full context)

| Score Bucket | N | WR | Total PnL | Avg PnL |
|-------------|---|----|-----------|---------|
| 0-49 | 230 | **71.3%** | **+$2,785** | **+$12.11** |
| 50-59 | 22 | **54.5%** | +$66 | +$3.01 |
| 60-69 | 11 | **45.5%** | -$68 | -$6.14 |
| 70+ | 275 | **38.2%** | -$224 | -$0.81 |

**TREND_DAY shows the SAME inverted score pattern.** 0-49 bucket = 71% WR (+$2,785), 70+ bucket = 38% WR (-$224). The "dropped" 60-69 trades are also losers.

### VERDICT

**Hypothesis: "Score 70 hardcode loses TREND money" — FALSE**

The 11 dropped TREND_DAY trades in the 60-69 range are net losers (-$67.50, 45.5% WR). The hardcoded 70 threshold is accidentally conservative in the right direction for TREND_DAY.

**However:** The broader finding is more important — TREND_DAY has the **same score anti-correlation** as NORMAL and DEVELOPING. Low-score TREND_DAY setups (0-49) are the best in the entire dataset ($12.11/trade, 71% WR). This means:

1. The hardcoded 70 is correct to reject 60-69, but for the **wrong reason** (it's supposed to be the "full size" threshold, not a quality filter)
2. The day-adaptive threshold of 60 for TREND_DAY would INCREASE losses by admitting the 60-69 losers
3. The real fix is still Score V2 — the anti-correlation renders all V1 thresholds unreliable

**Cleanup priority: LOW.** Fix for code hygiene (use `get_config(day_type)` instead of hardcoded 70) but don't expect it to change PnL outcomes.

---

## Query 3 — Vegas execution gate: SHORT asymmetry

### Context

`validate_setup_against_vegas()` at `main.py:808-835` requires LONG→BULLISH and SHORT→BEARISH. Vegas score 30pts only awards when trend matches direction. Hypothesis: this creates asymmetric blocking of SHORT setups since Vegas BULLISH periods dominate (mean-reversion SHORT setups get 0 Vegas points and are blocked at execution).

### Direction distribution (all attempts)

| Direction | Total | With Scores | Avg Score | Above 70 | % Above 70 |
|-----------|-------|-------------|-----------|----------|------------|
| LONG | 5,522 | 5,306 | **72.4** | 3,169 | **59.7%** |
| SHORT | 5,041 | 4,881 | **50.5** | 630 | **12.9%** |

**Massive asymmetry confirmed.** LONG average score = 72.4, SHORT = 50.5. Only **12.9%** of SHORT attempts score >= 70 vs **59.7%** of LONG.

### Vegas score = 0 by direction

| Direction | Vegas = 0 | Total | % with Vegas = 0 |
|-----------|-----------|-------|-------------------|
| LONG | 1,175 | 5,522 | **21.3%** |
| SHORT | 3,276 | 5,041 | **65.0%** |

**65% of SHORT attempts get Vegas = 0.** This is the structural cause: Vegas BULLISH market (which has been dominant) gives SHORT setups 0 out of 30 points, making it nearly impossible to reach 70.

### Filtered reason distribution

| Reason | LONG count | SHORT count | SHORT excess |
|--------|-----------|-------------|--------------|
| NORMAL_DAY_SKIP | 396 | 395 | 0 (symmetric) |
| FOOTPRINT_OPPOSES | 284 | 460 | **+176 (62% more)** |

FOOTPRINT_OPPOSES hits SHORT 62% more often than LONG. This makes sense: in a BULLISH-trending market, footprint delta is typically positive, which "opposes" SHORT direction.

**Note:** No `VEGAS_FILTER_REJECT` skip reason appears in the data. The Vegas execution gate (`validate_setup_against_vegas`) runs at `/trade/execute` time, not during attempt logging. Its blocking is invisible in the attempt data — it would only show as a 400 error when a user clicks EXECUTE.

### Outcomes by direction (resolved attempts)

| Group | N | WR | Total PnL | Avg PnL |
|-------|---|----|-----------|---------|
| ALL SHORT | 4,102 | **47.0%** | -$5,344 | -$1.30 |
| ALL LONG | 4,531 | **47.9%** | -$3,643 | -$0.80 |
| SHORT score 70+ | 554 | **38.8%** | **-$3,154** | **-$5.69** |
| LONG score 70+ | 2,678 | **42.2%** | -$9,249 | -$3.45 |

**Score 70+ SHORT attempts that DO pass are the worst performers** (38.8% WR, -$5.69/trade). The few SHORT setups that score >= 70 are forced LONG-biased by design (they need BEARISH Vegas to get 30pts — but if Vegas is BEARISH, the market is in a SHORT-friendly regime where LONG is likely wrong too).

### VERDICT

**Hypothesis: "Vegas gate blocks SHORT asymmetrically" — TRUE (🟢 High confidence)**

Evidence chain:
1. **65% of SHORT attempts get Vegas = 0** (vs 21% of LONG) — the scoring system structurally suppresses SHORT scores
2. **Only 12.9% of SHORT reach score >= 70** (vs 59.7% of LONG) — a 4.6x asymmetry in "executable" classification
3. **FOOTPRINT_OPPOSES hits SHORT 62% more** — the confluence filter compounds the direction bias
4. **The Vegas execution gate further blocks** any SHORT that somehow reaches the EXECUTE button without BEARISH Vegas, but this blocking is invisible in attempt data (happens at HTTP level)

**The irony:** SHORT setups with score 0-49 (Vegas opposing = 0pts) likely include the best reversal setups — sweeps at key levels where everyone is long and the market reverses. The scoring system gives them 0 for Vegas precisely because they are contrarian, but that's what makes them work.

---

## Summary — Hypothesis Verdicts

| # | Hypothesis | Verdict | Confidence |
|---|------------|---------|------------|
| 1 | DEVELOPING universally bad | **CONDITIONAL** — net negative overall, but low-score DEVELOPING is highly profitable (+$6,260). Problem is score anti-correlation, not day type. | 🟢 High (n=3,835) |
| 2 | Score 70 hardcode loses TREND money | **FALSE** — only 11 trades dropped, net -$68. TREND_DAY also shows inverted score pattern (low scores win). | 🟡 Medium (n=11 is small) |
| 3 | Vegas gate blocks SHORT asymmetrically | **TRUE** — 65% SHORT get Vegas=0, only 12.9% pass 70 threshold. 4.6x asymmetry vs LONG. | 🟢 High (n=10,563) |

## Implications for Sprint 3.3

1. **Quality Score V2 is the #1 priority.** All 3 queries confirm the same root cause: V1's direction-matching Vegas component (30pts) creates a direction proxy, not a quality measure. The anti-correlation appears on DEVELOPING, NORMAL, and TREND_DAY. V2's direction-agnostic design (tunnel width, not trend match) directly addresses this.

2. **Do NOT block DEVELOPING day type.** The Day 4 recommendation to add DEVELOPING as anti-pattern would destroy $6,260 in profitable low-score setups. Wait for V2 scoring.

3. **SHORT needs its own score threshold** (from D-038) — but implementing it under V1 scoring is pointless because only 12.9% of SHORT setups pass 70. The V2 score (direction-agnostic) must be deployed first to give SHORT setups a fair score distribution.

4. **The hardcoded 70 cleanup** (§3.4 in Inventory) is low priority. Replace for code hygiene but don't expect PnL impact — the score anti-correlation makes all V1 thresholds unreliable.

5. **Consider temporary reversal**: Until V2 is ready, a "score inversion" experiment (execute setups with score 30-49, block 70+) would be the highest-impact change — it captures the profitable contrarian setups that V1 is explicitly filtering out. This is provocative but the data supports it across all day types.
