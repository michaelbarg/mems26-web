# E2E Fire Proof — 2026-08-11
**Generated:** 2026-08-11T14:38:12.446685+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 200 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 200 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_REJECTION_REVERSE DOWN conf=0.5 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 19 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 0 trades recorded |
| 7 | Gateway Gates | PASS | 0 passed / 0 blocked / 0 shadow |
| 11 | Money | PASS | 0 closed, PnL=$0.00 |

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
  "opening_type": "OPEN_REJECTION_REVERSE",
  "direction": "DOWN",
  "confidence": 0.5,
  "reasons": [
    "initial move then full reversal through open"
  ],
  "detail": "OPEN_REJECTION_REVERSE DOWN conf=0.5"
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
  "fire_count": 19,
  "fires": [
    {
      "bar": 5,
      "ts": "2026-08-11 01:25:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7776.5
    },
    {
      "bar": 16,
      "ts": "2026-08-11 02:20:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7778.0
    },
    {
      "bar": 23,
      "ts": "2026-08-11 02:55:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7777.0
    },
    {
      "bar": 26,
      "ts": "2026-08-11 03:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7762.75
    },
    {
      "bar": 38,
      "ts": "2026-08-11 04:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7774.0
    },
    {
      "bar": 54,
      "ts": "2026-08-11 05:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7778.5
    },
    {
      "bar": 64,
      "ts": "2026-08-11 06:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7780.0
    },
    {
      "bar": 78,
      "ts": "2026-08-11 07:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7782.5
    },
    {
      "bar": 86,
      "ts": "2026-08-11 08:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7782.0
    },
    {
      "bar": 88,
      "ts": "2026-08-11 08:20:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7793.0
    },
    {
      "bar": 99,
      "ts": "2026-08-11 09:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7788.5
    },
    {
      "bar": 112,
      "ts": "2026-08-11 10:20:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7781.25
    },
    {
      "bar": 120,
      "ts": "2026-08-11 11:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7769.5
    },
    {
      "bar": 135,
      "ts": "2026-08-11 12:15:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7767.25
    },
    {
      "bar": 148,
      "ts": "2026-08-11 13:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7771.25
    },
    {
      "bar": 156,
      "ts": "2026-08-11 14:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7778.25
    },
    {
      "bar": 170,
      "ts": "2026-08-11 15:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7783.0
    },
    {
      "bar": 184,
      "ts": "2026-08-11 16:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7782.25
    },
    {
      "bar": 186,
      "ts": "2026-08-11 16:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7797.75
    }
  ],
  "detail": "19 distinct pattern fires"
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

