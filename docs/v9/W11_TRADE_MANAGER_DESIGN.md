# W11 Trade Manager Design

## Overview

Trade lifecycle manager: entry -> bracket -> exit.
NOT a decision maker. Receives setup objects from firing systems,
manages state transitions, emits events. Each firing system (1, 2, 4)
makes its own entry decision independently.

## State Machine

```
                  +─────────+
                  | PENDING |
                  +────┬────+
                  fill │    │ cancel
                       v    v
                  +────────+    +────────+
                  | FILLED |───>| CLOSED |
                  +────┬───+    +────────+
              T1 hit   │           ^
                       v           │
                  +─────────+      │
                  | PARTIAL |──────+
                  +─────────+  stop/T3/manual
```

Valid transitions:
- PENDING -> FILLED (on_fill)
- PENDING -> CLOSED (cancel before fill)
- FILLED  -> PARTIAL (T1 hit)
- FILLED  -> CLOSED (stop hit / manual close)
- PARTIAL -> CLOSED (stop hit / T3 hit / manual close)

Invalid transitions raise `InvalidTransition`.

## PnL Calculation

Per-contract, NOT 3x multiplier:
- c1 exits at T1 (if hit)
- c2 exits at T2 (if hit)
- c3 exits at T3 (if hit)
- On stop: all 3 exit at stop price
- MES = $5.00 per point per contract

## Events (Redis pub/sub)

Channel: `v9:trades:events`

Events emitted:
- `trade_created` — on accept_setup
- `trade_filled` — on fill
- `target_t1_hit` / `target_t2_hit` / `target_t3_hit` — on target hits
- `stop_hit` — on stop hit
- `trade_closed` — on manual close

## API

```python
manager = TradeManager(db=session, event_emitter=emitter)

trade_id = manager.accept_setup(setup_dict, mode="shadow")
manager.on_fill(trade_id, fill_price=5245.0)
manager.on_target_hit(trade_id, "T1", fill_ts=datetime_utc)
manager.on_stop_hit(trade_id, fill_ts=datetime_utc)
manager.close_trade(trade_id, reason="eod_flat")
active = manager.get_active_trades(mode="shadow")
```

## Files

| File | Purpose |
|------|---------|
| `backend/v9/services/trade_manager/__init__.py` | Package exports |
| `backend/v9/services/trade_manager/manager.py` | Core TradeManager class |
| `backend/v9/services/trade_manager/state_machine.py` | State transitions |
| `backend/v9/services/trade_manager/events.py` | Redis pub/sub emitter |
| `backend/v9/db/models/trades.py` | V9Trade DB model (updated) |
| `tests/v9/services/test_trade_manager.py` | Tests (>90% coverage) |

## DB Model (v9_trades)

Per Section 6 of 3-Mode Trading Spec:
mode, firing_system, direction, state, entry_ts, entry_price,
stop, t1, t2, t3, t1_hit_ts, t2_hit_ts, t3_hit_ts, stop_hit_ts,
exit_ts, exit_price, exit_reason, pnl_usd, pnl_r, outcome,
quality (nullable, W12 EOD), cross_context (JSON), created_at, updated_at
