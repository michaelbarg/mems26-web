# E2E Fire Proof — 2026-08-07
**Generated:** 2026-08-07T14:40:25.126158+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 201 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 201 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_REJECTION_REVERSE UP conf=0.5 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 15 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 0 trades recorded |
| 7 | Gateway Gates | PASS | 0 passed / 0 blocked / 0 shadow |
| 11 | Money | PASS | 0 closed, PnL=$0.00 |

## Detailed Results

### Link 1: Feed Freshness — PASS

```
{
  "status": "PASS",
  "pass": true,
  "bar_count": 201,
  "gaps_over_10min": [],
  "detail": "201 bars, 0 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "201 bars, 0 seams > 15pt"
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
  "fire_count": 15,
  "fires": [
    {
      "bar": 16,
      "ts": "2026-08-07 02:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7732.25
    },
    {
      "bar": 27,
      "ts": "2026-08-07 03:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7746.5
    },
    {
      "bar": 39,
      "ts": "2026-08-07 04:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7742.0
    },
    {
      "bar": 54,
      "ts": "2026-08-07 05:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7738.75
    },
    {
      "bar": 78,
      "ts": "2026-08-07 07:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7721.25
    },
    {
      "bar": 97,
      "ts": "2026-08-07 09:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7727.5
    },
    {
      "bar": 109,
      "ts": "2026-08-07 10:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7730.0
    },
    {
      "bar": 120,
      "ts": "2026-08-07 11:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7734.25
    },
    {
      "bar": 126,
      "ts": "2026-08-07 11:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7738.0
    },
    {
      "bar": 132,
      "ts": "2026-08-07 12:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7738.0
    },
    {
      "bar": 147,
      "ts": "2026-08-07 13:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7752.25
    },
    {
      "bar": 151,
      "ts": "2026-08-07 13:35:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7740.0
    },
    {
      "bar": 174,
      "ts": "2026-08-07 15:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7743.5
    },
    {
      "bar": 192,
      "ts": "2026-08-07 17:00:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7774.75
    },
    {
      "bar": 196,
      "ts": "2026-08-07 17:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7739.25
    }
  ],
  "detail": "15 distinct pattern fires"
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

