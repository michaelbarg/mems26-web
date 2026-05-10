# W15 Active Trade Manager — Design Document

## Purpose

Real-time monitoring of open (FILLED/PARTIAL) trades. Computes unrealized PnL,
detects proximity to targets and stop, triggers Smart Breakeven (Smart BE),
and emits time-based exit suggestions.

W15 is an **observer** — it does NOT make trading decisions or modify state
beyond the Smart BE stop adjustment.

## Relationship to W11

```
W11 (Trade Manager)          W15 (Active Trade Monitor)
├── Creates trades            ├── Reads open trades via W11.get_active_trades()
├── State transitions         ├── Computes unrealized PnL
├── Records target/stop hits  ├── Detects T1 hit → triggers Smart BE
└── Calculates realized PnL   ├── Emits proximity alerts
                              └── Emits time exit suggestions
```

W15 imports from W11 but never modifies W11 code. Stop adjustment (Smart BE)
is done by directly updating the trade record and flushing the DB session.

## Architecture

```
backend/v9/services/active_trade_manager/
├── __init__.py          # exports ActiveTradeMonitor, AlertEmitter
├── monitor.py           # ActiveTradeMonitor class
└── alerts.py            # AlertEmitter class
```

## ActiveTradeMonitor

### update(current_price, ts, et_hour?, et_minute?)

Called on every price tick. For each FILLED/PARTIAL trade:

1. **Smart BE check**: if state=PARTIAL and t1_hit_ts is set and Smart BE
   not yet applied, move stop to entry_price (breakeven)
2. **Target proximity**: for each unhit target (T1/T2/T3), compute
   `distance_pct = |target - price| / |target - entry|`. Alert if <= 0.25
3. **Stop proximity**: same formula for stop level
4. **Time exit**: if ET time >= 14:25, suggest closing before 14:30 cutoff

### get_open_trades(current_price)

Returns list of dicts with:
- trade_id, direction, state, entry_price, current_price
- stop, t1, t2, t3
- unrealized_pnl (USD)
- proximity (dict of target/stop distances)
- smart_be_applied (bool)

### Unrealized PnL Calculation

- **FILLED** (all 3 contracts open):
  `(current - entry) * direction_mult * $5/point * 3`
- **PARTIAL** (C1 exited at T1, C2+C3 open):
  `C1_realized + (current - entry) * direction_mult * $5/point * 2`

### Smart BE Logic

When T1 is hit (C1 partial fill), stop moves to entry_price:
- Protects C2 and C3 from loss
- Applied once per trade (tracked in _smart_be_applied dict)
- Bounded: dict entries removed via cleanup_trade() on close

## AlertEmitter

Publishes to Redis channel: `v9:trades:alerts`

Alert types:
- `approaching_target` — price within 25% of entry-to-target distance
- `approaching_stop` — price within 25% of entry-to-stop distance
- `smart_be_triggered` — stop moved to breakeven
- `time_exit_suggestion` — approaching 14:30 ET cutoff

Payload format:
```json
{
  "trade_id": 1,
  "alert_type": "approaching_target",
  "ts": "2026-05-10T14:25:00+00:00",
  "details": {"target_name": "T1", "distance_pct": 0.15}
}
```

## MES Constants

- Tick size: 0.25 points
- Point value: $5 per point per contract
- Tick value: $1.25 per tick per contract

## Proximity Threshold

Alert when price is within 25% of the entry-to-level distance:

```
distance_pct = |level - current_price| / |level - entry_price|

if distance_pct <= 0.25:
    emit alert
```

## Bounded Collections

- `_smart_be_applied` dict: entries added per open trade, removed via
  `cleanup_trade()` when trade closes. Never grows unbounded.
- Open trade iteration: only FILLED/PARTIAL trades from DB query.
