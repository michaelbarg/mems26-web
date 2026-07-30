# E2E Fire Proof — 2026-07-30
**Generated:** 2026-07-30T14:37:48.187381+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 200 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 200 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_DRIVE UP conf=0.85 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 18 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 2 trades recorded |
| 7 | Gateway Gates | PASS | 1 passed / 0 blocked / 1 shadow |
| 11 | Money | PASS | 1 closed, PnL=$-63.75 |

## Detailed Results

### Link 1: Feed Freshness — PASS

```
{
  "status": "PASS",
  "pass": true,
  "bar_count": 200,
  "gaps_over_10min": [],
  "detail": "200 bars, 0 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "200 bars, 0 seams > 15pt"
}
```

### Link 3: Opening Type — PASS

```
{
  "status": "PASS",
  "pass": true,
  "opening_type": "OPEN_DRIVE",
  "direction": "UP",
  "confidence": 0.85,
  "reasons": [
    "no return through opening print",
    "monotonic |price\u2212open|",
    "open_location=UNKNOWN"
  ],
  "detail": "OPEN_DRIVE UP conf=0.85"
}
```

### Link 4: Day Type — PASS

```
{
  "status": "PASS",
  "pass": true,
  "snapshots": {
    "api": {
      "day_type": "?",
      "confidence": 0,
      "stages": null
    }
  },
  "final_type": "?",
  "final_conf": 0,
  "detail": "final=? conf=0"
}
```

### Link 5: Pattern Detection — PASS

```
{
  "status": "PASS",
  "pass": true,
  "fire_count": 18,
  "fires": [
    {
      "bar": 13,
      "ts": "2026-07-30 02:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7363.25
    },
    {
      "bar": 25,
      "ts": "2026-07-30 03:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7368.25
    },
    {
      "bar": 30,
      "ts": "2026-07-30 03:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7392.0
    },
    {
      "bar": 37,
      "ts": "2026-07-30 04:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7363.75
    },
    {
      "bar": 42,
      "ts": "2026-07-30 04:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7394.75
    },
    {
      "bar": 62,
      "ts": "2026-07-30 06:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7382.5
    },
    {
      "bar": 68,
      "ts": "2026-07-30 06:40:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7383.25
    },
    {
      "bar": 80,
      "ts": "2026-07-30 07:40:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7383.25
    },
    {
      "bar": 93,
      "ts": "2026-07-30 08:45:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7361.75
    },
    {
      "bar": 98,
      "ts": "2026-07-30 09:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7381.5
    },
    {
      "bar": 120,
      "ts": "2026-07-30 11:00:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7372.25
    },
    {
      "bar": 124,
      "ts": "2026-07-30 11:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7347.75
    },
    {
      "bar": 134,
      "ts": "2026-07-30 12:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7364.5
    },
    {
      "bar": 144,
      "ts": "2026-07-30 13:00:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7392.0
    },
    {
      "bar": 148,
      "ts": "2026-07-30 13:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7367.25
    },
    {
      "bar": 157,
      "ts": "2026-07-30 14:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7379.5
    },
    {
      "bar": 176,
      "ts": "2026-07-30 15:40:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7412.5
    },
    {
      "bar": 181,
      "ts": "2026-07-30 16:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7388.75
    }
  ],
  "detail": "18 distinct pattern fires"
}
```

### Link 6: S2 Internal Checks — PASS

```
{
  "status": "PASS",
  "pass": true,
  "trade_count": 2,
  "trades": [
    {
      "id": 563,
      "pattern": "OPENING_DRIVE",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": -67.5,
      "blocked_by": null
    },
    {
      "id": 564,
      "pattern": "OPENING_DRIVE",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -63.75,
      "blocked_by": null
    }
  ],
  "detail": "2 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 2,
  "passed_demo_live": 1,
  "blocked": 0,
  "shadow": 1,
  "gate_breakdown": {},
  "detail": "1 passed / 0 blocked / 1 shadow"
}
```

### Link 11: Money — PASS

```
{
  "status": "PASS",
  "pass": true,
  "closed_trades": 1,
  "total_pnl": -63.75,
  "trades": [
    {
      "id": 564,
      "direction": "SHORT",
      "pattern": "OPENING_DRIVE",
      "pnl_usd": -63.75,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    }
  ],
  "detail": "1 closed, PnL=$-63.75"
}
```

