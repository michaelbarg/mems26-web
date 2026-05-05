# SIM-CONF-06: Multi-TF Confluence

**Date:** 2026-05-05 (Day 2 Evening)

---

## Method

`mtf_aligned` field not present in cached parquet. Used proxy:
parsed `score_reasons` for component agreement signals:
- Vegas match (not opposes) = 1 TF
- TPO favors direction = 1 TF
- FVG direction match = 1 TF
- Footprint confirms (not opposes) = 1 TF

Count of agreeing components → "TF agreement" (0-4).

---

## Results

### TF Agreement Distribution

| TF Count | Setups | % | WR | Edge vs Base |
|:--------:|:------:|:-:|:---:|:---:|
| 0 | 2,038 | 40.8% | 52.6% | +5.3pp |
| 1 | 1,621 | 32.4% | 44.4% | -2.9pp |
| 3 | 466 | 9.3% | 50.7% | +3.4pp |
| 4 | 871 | 17.4% | 38.6% | -8.7pp |

Base WR: 47.3%

### Key Comparison

| Group | Setups | WR |
|-------|--------|-----|
| 3+ TF agreement | 1,337 | **43.0%** |
| <2 TF agreement | 3,659 | **48.9%** |
| **Edge** | | **-5.9pp** |

---

## Analysis

### Counter-Intuitive Finding

More component agreement = **LOWER** WR. This is the opposite of what confluence theory predicts.

### Why This Happens

1. **All-agree = crowded signal:** When all 4 components align, the market has already moved significantly in that direction. Entry is late/overextended.

2. **Score inflation:** Score 80+ (all components agree) means price has already:
   - Passed through FVG zone (FVG confirms)
   - Is above/below Vegas tunnel (Vegas confirms)
   - TPO position aligns
   - Footprint delta confirms
   
   By the time all 4 fire, the move is EXHAUSTED.

3. **Zero-agreement = fresh:** When no components agree, the setup is contrarian. In MES (mean-reverting intraday), contrarian often works better.

4. **Parsing limitation:** The regex-based TF count from score_reasons is imprecise. Some "confirms" may be miscounted.

---

## VERDICT

| Criterion | Target | Result |
|-----------|--------|--------|
| 3+ TF > 5pp vs <2 | >+5pp | **-5.9pp (FAIL)** |

### Recommendation

1. **Do NOT use TF agreement count as entry filter** — it has negative edge
2. **Consider inverse:** Low confluence (0 TF) has +5.3pp edge — contrarian setups work
3. **Retest with proper mtf_aligned field** from production API (not score_reasons parse)
4. **Hypothesis:** In MES intraday, mean-reversion beats confluence. Validate with deduped data.
