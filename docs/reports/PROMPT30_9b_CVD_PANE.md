# P30.9b — Cumulative Delta Pane

**Date:** 2026-05-19
**Status:** GREEN — GET endpoint live, CVD pane shipped, 4-axis UAT pass
**No SHADOW/DEMO/LIVE enabled. No trade_command writes.**

---

## What Was Built

### Backend: `/api/v9/cumulative_delta/current`

New route in `backend/v9/api/v9/cumulative_delta_routes.py`. Reads Sierra
`cumulative_delta.json` directly (same pattern as `price_routes.py` and
`tpo_routes.py`). No bridge dependency.

Returns:
```json
{
  "source": "sierra_cumulative_delta_json",
  "version": "v9.4.0-p30.9",
  "stale": false,
  "age_s": 1.0,
  "current_delta": 101.0,
  "session_delta": 101.0,
  "peak": 411.0,
  "trough": -1259.0,
  "point_count": 9,
  "points": [
    {"i": 6419, "d": -88.0, "cum": -88.0, "p": 7406.5},
    ...
  ]
}
```

### Frontend: `CumulativeDeltaPane.tsx`

Canvas-based CVD pane below the price chart in `ChartV5b.tsx`:
- Green/red bars for positive/negative delta
- Cyan cumulative line overlay
- CVD value + peak/trough labels
- Polls `/api/v9/cumulative_delta/current` every 5s with in-flight guard
- Fixed 100px height, dark background matching chart

## Files Changed

| File | Change |
|------|--------|
| `backend/v9/api/v9/cumulative_delta_routes.py` | **NEW** — GET endpoint |
| `backend/v9/app.py` | Router registration |
| `tests/v9/api/test_cumulative_delta_routes.py` | **NEW** — 4 tests |
| `frontend/v9/.../CumulativeDeltaPane.tsx` | **NEW** — CVD pane component |
| `frontend/v9/.../ChartV5b.tsx` | Import + render CVD pane |

## Tests

```
pytest tests/v9/api/test_cumulative_delta_routes.py -q → 4 passed
pytest tests/v9/api/test_cumulative_delta_routes.py \
       tests/v9/api/test_tpo_routes_sierra_contract.py \
       tests/v9/api/test_cockpit_heartbeat.py -q → 10 passed
```

Frontend lint: `CumulativeDeltaPane.tsx` → 0 errors.

## Live UAT (2026-05-19)

### /api/v9/cumulative_delta/current

| Axis | Check | Result |
|------|-------|--------|
| Quality | source=sierra_cumulative_delta_json, points non-empty, cum values plausible | **PASS** — 9 points, cum range -1259 to +411 |
| Recency | Sierra file age < 30s | **PASS** — 1.0s |
| Cardinality | point_count documented | **PASS** — 9 points (matches Sierra file) |
| Latency | < 500ms | **PASS** — 1.3ms |

## Safety

- No SHADOW/DEMO/LIVE enabled
- No trade_command.json written
- Bridge: not involved (direct file read)
- Backend restarted to load new route
