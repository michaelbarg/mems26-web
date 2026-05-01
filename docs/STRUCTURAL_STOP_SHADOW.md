# Structural Stop — Shadow Mode (V8.2.7f)

## Status
- **Mode:** SHADOW only — does not affect actual trades
- **Purpose:** Collect data for Phase 3.5 implementation decision
- **Started:** 1/5/2026 (Day 2 evening)
- **File:** `backend/quality_score.py` function `compute_structural_stop_shadow()`

## Spec (per user, Day 2)

### LONG entry
- Stop = swing_low - 1.0pt (4 ticks below deepest wick)

### SHORT entry
- Stop = swing_high + 1.0pt (4 ticks above deepest wick)

### Buffer
- 1.0pt anti tick-out buffer (hardcoded, configurable later)

## Computation Source Priority

1. **Matching trigger** (preferred): use `trigger.price_low` (LONG) / `trigger.price_high` (SHORT) from DLL active triggers
   - Matches by direction: LONG seeks bullish triggers, SHORT seeks bearish
   - Takes first match (most recent active)
   - Source tag: `trigger_FVG`, `trigger_SWEEP`, `trigger_REVERSAL`

2. **Candle-scan fallback**: last 20 bars, find `min(low)` (LONG) / `max(high)` (SHORT)
   - Source tag: `candles_20bar`
   - Only used when no matching trigger found

3. **Unavailable**: if neither triggers nor candles available
   - Source tag: `unavailable`
   - `structural_stop_valid: false`

## Validation
- Risk must be in [3.0, 15.0] pt range
- If outside, `structural_stop_valid: false` (would be NO_TRADE in live)

## Storage
- In `setup_attempts.extra_json` field, key `shadow_structural_stop`
- Schema:
```json
{
  "structural_stop_price": 7245.50,
  "structural_stop_pts": 4.50,
  "structural_stop_source": "trigger_FVG",
  "structural_stop_valid": true,
  "structural_stop_anchor": 7246.50
}
```

## Phase 3.2 Analysis Plan (3-7/5)

For each closed setup, compare:
1. Did fixed-5pt stop hit? (existing `stop_hit` field)
2. Would structural stop have hit? (compare `structural_stop_price` to MAE)
3. Which would have produced better outcome?

### Hypotheses
- **H1:** Structural stop is tighter on quiet days -> faster T1 hit, less giveback
- **H2:** Structural stop is wider on volatile days -> fewer false stop-outs
- **H3:** Structural stop reduces overall stop-out rate by X%
- **H4:** Structural stop from triggers (FVG/SWEEP anchor) outperforms candle-scan

### SQL for Phase 3.2 analysis:
```sql
SELECT
  extra_json->'shadow_structural_stop'->>'structural_stop_source' as source,
  COUNT(*) as n,
  AVG((extra_json->'shadow_structural_stop'->>'structural_stop_pts')::float) as avg_struct_risk,
  AVG(ABS(entry_price_hypothetical - stop_hypothetical)) as avg_fixed_risk
FROM setup_attempts
WHERE extra_json->'shadow_structural_stop' IS NOT NULL
  AND extra_json->'shadow_structural_stop'->>'structural_stop_valid' = 'true'
GROUP BY source;
```

## Phase 3.5 Implementation Decision

After 5+ days of Phase 3.2 data:
- If structural stop produces >=10% improvement in net PnL -> implement as primary
- If similar performance -> keep fixed for simplicity
- Update this doc with decision + commit reference

## Dependencies for Full Implementation (Phase 3.5)
- Trigger cache available at setup creation (already wired)
- Frontend QualityScorePanel must send structural stop instead of fixed 5pt
- Backend validation (3-15pt) already handles variable stops
- Shadow simulator must use structural stop for new setups
