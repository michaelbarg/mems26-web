# E2E Fire Proof — 2026-07-31
**Generated:** 2026-07-31T14:37:34.057950+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 200 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 200 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_AUCTION_IN NEUTRAL conf=0.4 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 14 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 11 trades recorded |
| 7 | Gateway Gates | PASS | 4 passed / 0 blocked / 7 shadow |
| 11 | Money | PASS | 4 closed, PnL=$-153.75 |

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
  "fire_count": 14,
  "fires": [
    {
      "bar": 8,
      "ts": "2026-07-31 01:40:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7480.5
    },
    {
      "bar": 20,
      "ts": "2026-07-31 02:40:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7476.25
    },
    {
      "bar": 36,
      "ts": "2026-07-31 04:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7487.25
    },
    {
      "bar": 51,
      "ts": "2026-07-31 05:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7504.75
    },
    {
      "bar": 75,
      "ts": "2026-07-31 07:15:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7488.25
    },
    {
      "bar": 97,
      "ts": "2026-07-31 09:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7502.0
    },
    {
      "bar": 102,
      "ts": "2026-07-31 09:30:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7515.5
    },
    {
      "bar": 122,
      "ts": "2026-07-31 11:10:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7498.75
    },
    {
      "bar": 139,
      "ts": "2026-07-31 12:35:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7521.75
    },
    {
      "bar": 156,
      "ts": "2026-07-31 14:00:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7500.25
    },
    {
      "bar": 159,
      "ts": "2026-07-31 14:15:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7515.5
    },
    {
      "bar": 169,
      "ts": "2026-07-31 15:05:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7504.75
    },
    {
      "bar": 183,
      "ts": "2026-07-31 16:15:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7476.25
    },
    {
      "bar": 189,
      "ts": "2026-07-31 16:45:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7519.25
    }
  ],
  "detail": "14 distinct pattern fires"
}
```

### Link 6: S2 Internal Checks — PASS

```
{
  "status": "PASS",
  "pass": true,
  "trade_count": 11,
  "trades": [
    {
      "id": 574,
      "pattern": "OPENING_DRIVE",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": -198.75,
      "blocked_by": null
    },
    {
      "id": 575,
      "pattern": "OPENING_DRIVE",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -198.75,
      "blocked_by": null
    },
    {
      "id": 576,
      "pattern": "OPENING_PULLBACK_CONT",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": -216.25,
      "blocked_by": null
    },
    {
      "id": 577,
      "pattern": "OPENING_ORR",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 80.0,
      "blocked_by": null
    },
    {
      "id": 578,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 36.25,
      "blocked_by": null
    },
    {
      "id": 579,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -45.0,
      "blocked_by": null
    },
    {
      "id": 580,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 143.75,
      "blocked_by": null
    },
    {
      "id": 581,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": 143.75,
      "blocked_by": null
    },
    {
      "id": 582,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 58.75,
      "blocked_by": null
    },
    {
      "id": 583,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": -55.0,
      "blocked_by": null
    },
    {
      "id": 584,
      "pattern": "INITIATIVE_SHORT",
      "direction": "SHORT",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -53.75,
      "blocked_by": null
    }
  ],
  "detail": "11 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 11,
  "passed_demo_live": 4,
  "blocked": 0,
  "shadow": 7,
  "gate_breakdown": {},
  "detail": "4 passed / 0 blocked / 7 shadow"
}
```

### Link 11: Money — PASS

```
{
  "status": "PASS",
  "pass": true,
  "closed_trades": 4,
  "total_pnl": -153.75,
  "trades": [
    {
      "id": 575,
      "direction": "LONG",
      "pattern": "OPENING_DRIVE",
      "pnl_usd": -198.75,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    },
    {
      "id": 579,
      "direction": "SHORT",
      "pattern": "INITIATIVE_SHORT",
      "pnl_usd": -45.0,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    },
    {
      "id": 581,
      "direction": "SHORT",
      "pattern": "INITIATIVE_SHORT",
      "pnl_usd": 143.75,
      "outcome": "WIN",
      "exit_reason": "T2_HIT"
    },
    {
      "id": 584,
      "direction": "SHORT",
      "pattern": "INITIATIVE_SHORT",
      "pnl_usd": -53.75,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    }
  ],
  "detail": "4 closed, PnL=$-153.75"
}
```

