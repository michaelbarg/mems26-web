# E2E Fire Proof — 2026-08-03
**Generated:** 2026-08-03T14:39:09.596776+00:00
**Mode:** Level A (replay, no code changes)

## Chain Summary

| # | Link | Status | Detail |
|---|------|--------|--------|
| 1 | Feed Freshness | PASS | 105 bars, 0 gaps > 10min |
| 2 | Bar Integrity | PASS | 105 bars, 0 seams > 15pt |
| 3 | Opening Type | PASS | OPEN_AUCTION_IN NEUTRAL conf=0.4 |
| 4 | Day Type | PASS | final=? conf=0 |
| 5 | Pattern Detection | PASS | 7 distinct pattern fires |
| 6 | S2 Internal Checks | PASS | 9 trades recorded |
| 7 | Gateway Gates | PASS | 4 passed / 0 blocked / 5 shadow |
| 11 | Money | PASS | 3 closed, PnL=$127.50 |

## Detailed Results

### Link 1: Feed Freshness — PASS

```
{
  "status": "PASS",
  "pass": true,
  "bar_count": 105,
  "gaps_over_10min": [],
  "detail": "105 bars, 0 gaps > 10min"
}
```

### Link 2: Bar Integrity — PASS

```
{
  "status": "PASS",
  "pass": true,
  "seam_count": 0,
  "seams": [],
  "detail": "105 bars, 0 seams > 15pt"
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
      "ts": "2026-08-03 09:25:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7561.75
    },
    {
      "bar": 21,
      "ts": "2026-08-03 10:40:00",
      "pattern": "GB100",
      "direction": "SHORT",
      "stop": 7566.0
    },
    {
      "bar": 36,
      "ts": "2026-08-03 11:55:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7543.75
    },
    {
      "bar": 50,
      "ts": "2026-08-03 13:05:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7549.5
    },
    {
      "bar": 67,
      "ts": "2026-08-03 14:30:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7553.25
    },
    {
      "bar": 81,
      "ts": "2026-08-03 15:40:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7549.75
    },
    {
      "bar": 94,
      "ts": "2026-08-03 16:45:00",
      "pattern": "GB100",
      "direction": "LONG",
      "stop": 7538.75
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
  "trade_count": 9,
  "trades": [
    {
      "id": 587,
      "pattern": "HTLB",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 28.75,
      "blocked_by": null
    },
    {
      "id": 588,
      "pattern": "HTLB",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": 71.25,
      "blocked_by": null
    },
    {
      "id": 589,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 16.25,
      "blocked_by": null
    },
    {
      "id": 590,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 15.0,
      "blocked_by": null
    },
    {
      "id": 591,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": -20.0,
      "blocked_by": null
    },
    {
      "id": 592,
      "pattern": "REACTIVE_LONG",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "shadow",
      "pnl_usd": 75.0,
      "blocked_by": null
    },
    {
      "id": 593,
      "pattern": "REACTIVE_LONG",
      "direction": "LONG",
      "state": "CLOSED",
      "mode": "live",
      "pnl_usd": 76.25,
      "blocked_by": null
    },
    {
      "id": 594,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "FILLED",
      "mode": "shadow",
      "pnl_usd": null,
      "blocked_by": null
    },
    {
      "id": 595,
      "pattern": "ZLR",
      "direction": "LONG",
      "state": "FILLED",
      "mode": "live",
      "pnl_usd": null,
      "blocked_by": null
    }
  ],
  "detail": "9 trades recorded"
}
```

### Link 7: Gateway Gates — PASS

```
{
  "status": "PASS",
  "pass": true,
  "total": 9,
  "passed_demo_live": 4,
  "blocked": 0,
  "shadow": 5,
  "gate_breakdown": {},
  "detail": "4 passed / 0 blocked / 5 shadow"
}
```

### Link 11: Money — PASS

```
{
  "status": "PASS",
  "pass": true,
  "closed_trades": 3,
  "total_pnl": 127.5,
  "trades": [
    {
      "id": 588,
      "direction": "LONG",
      "pattern": "HTLB",
      "pnl_usd": 71.25,
      "outcome": "WIN",
      "exit_reason": "T2_HIT"
    },
    {
      "id": 591,
      "direction": "LONG",
      "pattern": "ZLR",
      "pnl_usd": -20.0,
      "outcome": "LOSS",
      "exit_reason": "STOP_HIT"
    },
    {
      "id": 593,
      "direction": "LONG",
      "pattern": "REACTIVE_LONG",
      "pnl_usd": 76.25,
      "outcome": "WIN",
      "exit_reason": "T2_HIT"
    }
  ],
  "detail": "3 closed, PnL=$127.50"
}
```

