# W12 Daily Quality Agent — Design Document

## Overview

EOD batch job that tags completed V9 trades with quality grades.
ANALYTICAL only — does NOT gate trades. Sets `V9Trade.quality` JSON field.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           DailyQualityAgent                     │
│                                                 │
│  run_eod_batch(date)                            │
│    │                                            │
│    ├─ Query V9Trade WHERE outcome IS NOT NULL    │
│    │   AND entry_ts on target_date              │
│    │                                            │
│    ├─ For each trade:                           │
│    │   ├─ timing_quality(entry_ts in ET)         │
│    │   ├─ execution_quality(slippage)            │
│    │   ├─ outcome_quality(WIN/LOSS/BE)           │
│    │   ├─ context_quality(cross_context)         │
│    │   └─ compute_grade(weighted avg)            │
│    │                                            │
│    └─ Write quality JSON to V9Trade.quality      │
└─────────────────────────────────────────────────┘
```

## Quality Dimensions (0.0-1.0 each)

| Dimension | What it measures | Score range |
|-----------|-----------------|-------------|
| timing | Entry during HIGH killzone? | 1.0=HIGH, 0.5=MEDIUM, 0.2=LOW, 0.0=OFF |
| execution | Slippage vs expected entry | 1.0=zero slippage, 0.0=slippage >= risk |
| outcome | Trade result | 1.0=WIN+T3, 0.75=WIN partial, 0.5=BE, 0.0=LOSS |
| context | Cross-system agreement | 1.0=agree, 0.5=neutral, 0.0=disagree |

## Grade Computation

Weighted average with weights:
- timing: 0.20
- execution: 0.25
- outcome: 0.35
- context: 0.20

| Grade | Threshold |
|-------|-----------|
| A | >= 0.8 |
| B | >= 0.6 |
| C | >= 0.4 |
| D | < 0.4 |

## V9Trade.quality JSON Schema

```json
{
  "grade": "A",
  "dimensions": {
    "timing": 1.0,
    "execution": 0.95,
    "outcome": 1.0,
    "context": 0.75
  }
}
```

## Idempotency

Rerunning `run_eod_batch(date)` for the same date overwrites
`V9Trade.quality` with identical results because all scoring
is deterministic from trade fields (no external state).

## Files

| File | Purpose |
|------|---------|
| `backend/v9/services/daily_quality_agent/__init__.py` | Package exports |
| `backend/v9/services/daily_quality_agent/agent.py` | DailyQualityAgent class |
| `backend/v9/services/daily_quality_agent/scoring.py` | Quality dimension functions |
| `tests/v9/services/test_daily_quality_agent.py` | Tests (>85% coverage) |

## Dependencies

- V9Trade model (`backend/v9/db/models/trades.py`)
- Killzone zones (`backend/v9/systems/killzone/zones.py`) — referenced for timing tiers
- SQLAlchemy session

## Integration

Called by EOD scheduler (future W15 or cron job):
```python
from backend.v9.services.daily_quality_agent import DailyQualityAgent

agent = DailyQualityAgent(db=session)
results = agent.run_eod_batch(date.today())
```
