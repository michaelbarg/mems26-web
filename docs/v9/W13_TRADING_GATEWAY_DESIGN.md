# W13 Trading Gateway Design

## Purpose

Routes setups from firing systems (1, 2, 4) to three independent trading layers:
SHADOW, DEMO, and LIVE. Implements spec Section 8 pseudo-code.

## Architecture

```
Firing System (1, 2, 4)
        |
        v
  TradingGateway.route_setup(setup, system_id)
        |
        +-----> ShadowExecutor.execute(setup)   [ALWAYS, parallel]
        |           -> W11.accept_setup(mode='shadow')
        |
        +-----> DemoExecutor.execute(setup)     [if slot empty]
        |           -> W11.accept_setup(mode='demo')
        |           -> slot LOCKED until release_slot()
        |
        +-----> LiveExecutor.execute(setup)     [if slot empty + W14 allows]
                    -> W14.check_setup(setup)
                    -> W11.accept_setup(mode='live')
                    -> slot LOCKED until release_slot()
```

## Mode Rules

| Mode   | Slot   | Caps       | Sierra Account     |
|--------|--------|------------|--------------------|
| SHADOW | none   | none       | N/A (paper)        |
| DEMO   | 1 slot | none       | PA-APEX-125218-01  |
| LIVE   | 1 slot | W14 strict | APEX-125218-13     |

## LIVE Caps (W14)

- Daily loss: $250
- Max trades/day: 5
- Max contracts: 2
- Time cutoff: 14:30 ET
- News block: FOMC/CPI/NFP +/-10min
- Consecutive losses: 2 -> STOP DAY

## Slot Lifecycle

```
Setup fires -> slot empty? -> YES -> create trade -> LOCK slot
                           -> NO  -> reject (log reason)

Trade closes -> release_slot(mode, trade_id) -> UNLOCK slot -> next setup wins
```

## Files

- `backend/v9/services/trading_gateway/gateway.py` — TradingGateway class
- `backend/v9/services/trading_gateway/executors/shadow.py` — ShadowExecutor
- `backend/v9/services/trading_gateway/executors/demo.py` — DemoExecutor
- `backend/v9/services/trading_gateway/executors/live.py` — LiveExecutor
- `tests/v9/services/test_trading_gateway.py` — 20+ tests

## Dependencies (import only)

- W11 TradeManager (`backend.v9.services.trade_manager.manager`)
- W14 RiskValidator (`backend.v9.services.risk_validator.validator`)
