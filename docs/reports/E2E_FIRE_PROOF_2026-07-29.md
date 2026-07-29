# E2E Fire Proof — 2026-07-29
**Generated:** 2026-07-29T19:53:40.326568+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | FAIL | 149 bars, 1 gaps > 10min |
| 2 | Bar Integrity | PASS | 149 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_REJECTION_REVERSE UP conf=0.5 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 12 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 0 trades recorded |
| 7 | Gateway Gates | PASS | 0 passed / 0 blocked / 0 shadow |
| 11 | Money | PASS | 0 closed, PnL=$0.00 |

## Detailed Results

### Link 1: Feed Freshness — FAIL

```
{
  "status": "FAIL",
  "pass": false,
  "bar_count": 149,
  "gaps_over_10min": [
    "2026-07-29 13:25:00+03:00 \u2192 2026-07-29 13:50:00+03:00 (1500s)"
  ],
  "detail": "149 bars, 1 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "149 bars, 0 seams > 15pt"
}
```

### Link 3: Opening Type — PASS

```
{
  "status": "PASS",
  "pass": true,
  "opening_type": "OPEN_REJECTION_REVERSE",
  "direction": "UP",
  "confidence": 0.5,
  "reasons": [
    "initial move then full reversal through open"
  ],
  "detail": "OPEN_REJECTION_REVERSE UP conf=0.5"
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
  "fire_count": 12,
  "fires": [
    {
      "bar": 12,
      "ts": "2026-07-29 11:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7476.75
    },
    {
      "bar": 19,
      "ts": "2026-07-29 11:45:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7465.0
    },
    {
      "bar": 31,
      "ts": "2026-07-29 12:45:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7473.5
    },
    {
      "bar": 40,
      "ts": "2026-07-29 13:50:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7492.5
    },
    {
      "bar": 49,
      "ts": "2026-07-29 14:35:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7488.75
    },
    {
      "bar": 55,
      "ts": "2026-07-29 15:05:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7486.75
    },
    {
      "bar": 67,
      "ts": "2026-07-29 16:05:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7471.0
    },
    {
      "bar": 97,
      "ts": "2026-07-29 18:35:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7416.5
    },
    {
      "bar": 112,
      "ts": "2026-07-29 19:50:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7380.25
    },
    {
      "bar": 126,
      "ts": "2026-07-29 21:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7394.0
    },
    {
      "bar": 133,
      "ts": "2026-07-29 21:35:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7410.75
    },
    {
      "bar": 142,
      "ts": "2026-07-29 22:20:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7486.5
    }
  ],
  "detail": "12 distinct pattern fires"
}
```

### Link 6: S2 Internal Checks — PASS

```
{
  "status": "PASS",
  "pass": true,
  "trade_count": 0,
  "trades": [],
  "detail": "0 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 0,
  "passed_demo_live": 0,
  "blocked": 0,
  "shadow": 0,
  "gate_breakdown": {},
  "detail": "0 passed / 0 blocked / 0 shadow"
}
```

### Link 11: Money — PASS

```
{
  "status": "PASS",
  "pass": true,
  "closed_trades": 0,
  "total_pnl": 0,
  "trades": [],
  "detail": "0 closed, PnL=$0.00"
}
```

