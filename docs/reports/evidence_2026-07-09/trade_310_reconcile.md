# Trade 310 P&L Reconciliation — Sierra TradeActivityLog vs DB

**Date:** 2026-07-09  
**Source:** `TradeActivityLog_2026-07-08_UTC.37138283.data`  
**Account:** 37138283 (LIVE)

## Sierra evidence (Rule 5)

### Entry fills
- Order **8464** (c1): Market fill, parent base price **7515.50**, position 0→1
- Order **8467** (c2): Market fill, parent base price **7515.50**, position 1→2
- Brackets: c1 target=8465 stop=8466, c2 target=8468 stop=8469

### Exit
- Order **8470**: position 2→0 (manual flatten by Michael, NOT bracket fill)
- Brackets for parents 8464 and 8467 were **Canceled** after flatten

### Sierra P&L (definitive)
```
Cash Balance update | Closed Trade Profit/Loss: 11.25. Symbol: MESU26_FUT_CME. Currency: USD  [balance seq 4084]
Cash Balance update | Closed Trade Profit/Loss: 11.25. Symbol: MESU26_FUT_CME. Currency: USD  [balance seq 4085]
```
**Total: $11.25 × 2 contracts = $22.50**

## Divergence

| Field       | DB (before) | Sierra (truth) | Delta          |
|-------------|-------------|----------------|----------------|
| entry_price | 7514.00     | 7515.50        | +1.50 pts      |
| exit_price  | 7518.50     | 7517.75        | −0.75 pts      |
| pnl_usd     | $45.00      | $22.50         | **−$22.50 (2×)**|
| pnl_r       | 0.41        | 0.18           | −0.23          |

## Root cause
DB entry_price came from the **setup/signal price** (what S4 computed), not the
actual Sierra fill price. This is class **L4** — the fill_poller was not wired to
write the Sierra fill price back to the trade record. The fix from 2026-07-08
(fill_poller → `registered order → trade`) should capture fill prices on live
trades going forward; verify on the first live trade today.

## Corrective action
```sql
UPDATE v9_trades SET entry_price=7515.50, exit_price=7517.75, pnl_usd=22.50,
  pnl_r=0.18, quality = quality || '{"reconciled_from":"TradeActivityLog...",
  "pre_reconcile":{"entry_price":7514,"exit_price":7518.5,"pnl_usd":45,"pnl_r":0.41}}'
WHERE id=310;
-- Verified: UPDATE 1
```

## Verification
```
psql> SELECT quality->>'reconciled_from', quality->'pre_reconcile' FROM v9_trades WHERE id=310;
 TradeActivityLog_2026-07-08_UTC.37138283 | {"pnl_r": 0.41, "pnl_usd": 45, "exit_price": 7518.5, "entry_price": 7514}
```
