# E2E Fire Proof — 2026-08-05
**Generated:** 2026-08-05T14:40:03.048384+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 84 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 84 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_AUCTION_IN NEUTRAL conf=0.4 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 7 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 1 trades recorded |
| 7 | Gateway Gates | PASS | 0 passed / 0 blocked / 1 shadow |
| 11 | Money | PASS | 0 closed, PnL=$0.00 |

## Detailed Results

### Link 1: Feed Freshness — PASS

```
{
  "status": "PASS",
  "pass": true,
  "bar_count": 84,
  "gaps_over_10min": [],
  "detail": "84 bars, 0 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "84 bars, 0 seams > 15pt"
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
  "fire_count": 7,
  "fires": [
    {
      "bar": 6,
      "ts": "2026-08-05 11:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7789.75
    },
    {
      "bar": 20,
      "ts": "2026-08-05 12:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7777.75
    },
    {
      "bar": 32,
      "ts": "2026-08-05 13:20:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7783.5
    },
    {
      "bar": 52,
      "ts": "2026-08-05 15:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7788.75
    },
    {
      "bar": 65,
      "ts": "2026-08-05 16:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7794.5
    },
    {
      "bar": 75,
      "ts": "2026-08-05 16:55:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7790.75
    },
    {
      "bar": 81,
      "ts": "2026-08-05 17:25:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7822.75
    }
  ],
  "detail": "7 distinct pattern fires"
}
```

### Link 6: S2 Internal Checks — PASS

```
{
  "status": "PASS",
  "pass": true,
  "trade_count": 1,
  "trades": [
    {
      "id": 626,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "FILLED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    }
  ],
  "detail": "1 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 1,
  "passed_demo_live": 0,
  "blocked": 0,
  "shadow": 1,
  "gate_breakdown": {},
  "detail": "0 passed / 0 blocked / 1 shadow"
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

