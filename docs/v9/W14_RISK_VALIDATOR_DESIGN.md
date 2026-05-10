# W14 Risk Validator Design

## Purpose

Enforce LIVE mode risk caps per 3-Mode Trading Spec V3 Section 5.
SHADOW and DEMO modes bypass all checks entirely.

## LIVE Mode Caps

| Cap                  | Value         |
|----------------------|---------------|
| Daily loss           | $250          |
| Max trades/day       | 5             |
| Max position size    | 2 contracts   |
| Time cutoff          | 14:30 ET      |
| News block           | FOMC/CPI/NFP +/-10 min |
| Consecutive losses   | 2 -> STOP DAY |
| Manual override      | Required for size > 1 (standard) |

## Risk Gating Order (Section 5)

```
LIVE setup detected
    |
    v
1. Time filter check (>= 14:30 ET -> REJECT)
    |
    v
2. News window check (FOMC/CPI/NFP +/-10 min -> REJECT)
    |
    v
3. Daily loss cap check (>= $250 -> REJECT)
    |
    v
4. Max trades/day check (>= 5 -> REJECT)
    |
    v
5. Consecutive losses check (>= 2 -> STOP DAY)
    |
    v
6. Position size check (> 2 contracts -> REJECT)
    |
    v
7. Manual override check (size > 1 without override -> REJECT)
    |
    v
ALLOWED
```

## Files

| File | Purpose |
|------|---------|
| `backend/v9/services/risk_validator/__init__.py` | Package exports |
| `backend/v9/services/risk_validator/validator.py` | RiskValidator class |
| `backend/v9/services/risk_validator/news_calendar.py` | Hardcoded 2026 FOMC/CPI/NFP dates |
| `tests/v9/services/test_risk_validator.py` | Tests (>90% coverage) |

## API

### `RiskValidator.check_setup(setup, account_state, now_et=None)`

Returns `(allowed: bool, rejection_reason: str | None)`.

- SHADOW/DEMO: always `(True, None)`
- LIVE: runs all 7 checks in order, returns first failure

### `RiskValidator.record_trade_result(trade_id, pnl_usd)`

Updates daily state: trade count, loss accumulation, consecutive losses.

### `RiskValidator.daily_reset()`

Resets all counters. Called at midnight ET.

## News Calendar

Hardcoded 2026 dates for:
- 8 FOMC decision announcements (14:00 ET)
- 12 CPI releases (08:30 ET)
- 12 NFP first Fridays (08:30 ET)

Phase 3.5 will add live news feed integration to supplement/replace
the hardcoded calendar.

## State Tracked

- `daily_trades_count` — incremented by `record_trade_result`
- `daily_loss_usd` — accumulated from negative PnL
- `consecutive_losses` — reset on any win
- `_stopped_for_day` — set True when consecutive losses >= 2
- `in_news_window` — computed live from `news_calendar`
- `after_cutoff_time` — computed live from wall clock
