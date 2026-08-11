# E2E Fire Proof — 2026-08-10
**Generated:** 2026-08-10T14:37:52.506359+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 200 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 200 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_AUCTION_IN NEUTRAL conf=0.4 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 16 distinct pattern fires |
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
  "opening_type": "OPEN_AUCTION_IN",
  "direction": "NEUTRAL",
  "confidence": 0.4,
  "reasons": [
    "rotational; 0 crossings of open; open_location=UNKNOWN"
  ],
  "detail": "OPEN_AUCTION_IN NEUTRAL conf=0.4"
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
  "fire_count": 16,
  "fires": [
    {
      "bar": 14,
      "ts": "2026-08-10 02:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7763.25
    },
    {
      "bar": 23,
      "ts": "2026-08-10 02:55:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7776.5
    },
    {
      "bar": 25,
      "ts": "2026-08-10 03:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7761.25
    },
    {
      "bar": 38,
      "ts": "2026-08-10 04:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7765.0
    },
    {
      "bar": 56,
      "ts": "2026-08-10 05:40:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7773.5
    },
    {
      "bar": 66,
      "ts": "2026-08-10 06:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7776.75
    },
    {
      "bar": 74,
      "ts": "2026-08-10 07:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7778.0
    },
    {
      "bar": 82,
      "ts": "2026-08-10 07:50:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7779.25
    },
    {
      "bar": 95,
      "ts": "2026-08-10 08:55:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7784.25
    },
    {
      "bar": 130,
      "ts": "2026-08-10 11:50:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7797.25
    },
    {
      "bar": 136,
      "ts": "2026-08-10 12:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7786.25
    },
    {
      "bar": 140,
      "ts": "2026-08-10 12:40:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7797.5
    },
    {
      "bar": 146,
      "ts": "2026-08-10 13:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7795.0
    },
    {
      "bar": 171,
      "ts": "2026-08-10 15:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7789.75
    },
    {
      "bar": 185,
      "ts": "2026-08-10 16:25:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7781.75
    },
    {
      "bar": 189,
      "ts": "2026-08-10 16:45:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7765.25
    }
  ],
  "detail": "16 distinct pattern fires"
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

