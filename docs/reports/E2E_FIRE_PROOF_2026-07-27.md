# E2E Fire Proof — 2026-07-27
**Generated:** 2026-07-29T19:53:27.267658+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 183 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 183 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_AUCTION_IN NEUTRAL conf=0.4 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 12 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 17 trades recorded |
| 7 | Gateway Gates | PASS | 3 passed / 0 blocked / 14 shadow |
| 11 | Money | PASS | 2 closed, PnL=$-90.00 |

## Detailed Results

### Link 1: Feed Freshness — PASS

```
{
  "status": "PASS",
  "pass": true,
  "bar_count": 183,
  "gaps_over_10min": [],
  "detail": "183 bars, 0 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "183 bars, 0 seams > 15pt"
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
    "rotational; 1 crossings of open; open_location=UNKNOWN"
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
  "fire_count": 12,
  "fires": [
    {
      "bar": 9,
      "ts": "2026-07-27 09:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7514.0
    },
    {
      "bar": 21,
      "ts": "2026-07-27 10:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7521.5
    },
    {
      "bar": 32,
      "ts": "2026-07-27 11:25:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7501.5
    },
    {
      "bar": 46,
      "ts": "2026-07-27 12:35:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7512.25
    },
    {
      "bar": 63,
      "ts": "2026-07-27 14:00:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7528.5
    },
    {
      "bar": 77,
      "ts": "2026-07-27 15:10:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7519.25
    },
    {
      "bar": 93,
      "ts": "2026-07-27 16:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7519.25
    },
    {
      "bar": 118,
      "ts": "2026-07-27 18:35:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7462.0
    },
    {
      "bar": 134,
      "ts": "2026-07-27 19:55:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7415.5
    },
    {
      "bar": 146,
      "ts": "2026-07-27 20:55:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7415.5
    },
    {
      "bar": 157,
      "ts": "2026-07-27 21:50:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7420.0
    },
    {
      "bar": 178,
      "ts": "2026-07-27 23:35:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7440.75
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
  "trade_count": 17,
  "trades": [
    {
      "id": 529,
      "pattern": "REACTIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 531,
      "pattern": "REACTIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 23.75,
      "blocked_by": null
    },
    {
      "id": 533,
      "pattern": "REACTIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 535,
      "pattern": "INITIATIVE_LONG",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 536,
      "pattern": "INITIATIVE_LONG",
      "direction": "LONG",
      "state": "CANCELLED",
      "mode": "live",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 537,
      "pattern": "ZLR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 538,
      "pattern": "ZLR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 540,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 542,
      "pattern": "REACTIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 544,
      "pattern": "ZLR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 545,
      "pattern": "ZLR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -90.0,
      "blocked_by": null
    },
    {
      "id": 546,
      "pattern": "ZLR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": -86.25,
      "blocked_by": null
    },
    {
      "id": 547,
      "pattern": "GB100",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 548,
      "pattern": "GB100",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": 0.0,
      "blocked_by": null
    },
    {
      "id": 549,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 550,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 551,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    }
  ],
  "detail": "17 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 17,
  "passed_demo_live": 3,
  "blocked": 0,
  "shadow": 14,
  "gate_breakdown": {},
  "detail": "3 passed / 0 blocked / 14 shadow"
}
```

### Link 11: Money — PASS

```
{
  "status": "PASS",
  "pass": true,
  "closed_trades": 2,
  "total_pnl": -90.0,
  "trades": [
    {
      "id": 545,
      "direction": "SHORT",
      "pattern": "ZLR",
      "pnl_usd": -90.0,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    },
    {
      "id": 548,
      "direction": "LONG",
      "pattern": "GB100",
      "pnl_usd": 0.0,
      "outcome": "BE",
      "exit_reason": "SIERRA_FLAT"
    }
  ],
  "detail": "2 closed, PnL=$-90.00"
}
```

