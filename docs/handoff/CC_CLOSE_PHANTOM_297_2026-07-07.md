# CC → cleanly remove phantom trade 297 before live (2026-07-07)

Michael saw the frontend showing an active LONG 7583.75 (the SIM_TEST proof trade 297) while
there is NO real position. It is a phantom: the DB believes a demo LONG is open. It MUST be fully
cleaned before flipping to live — a leftover active trade would make the I-58 fallback attribute
the REAL trade's fill to 297 instead of the new trade.

Clean it PROPERLY (not a bare SQL flip) — close the trade AND release the gateway slot AND flatten
any lingering Sierra sim position, or you trade one phantom (DB) for another (stuck slot →
MISMATCH_PHANTOM_SLOT). Use the running app (you already have the debug gateway hook).

## Steps
1. **Flatten any Sierra sim position for 297** (Sim Mode ON):
   `sierra_command.write_cancel(trade_id="297", mode="demo")` → Sierra flat + CANCEL_OK.
2. **Close the trade the app way** (releases the slot + marks state correctly — do NOT just
   `UPDATE ... state='CLOSED'`, that strands the gateway demo_slot):
   `app.state.trading_gateway._trade_manager.close_trade(297, reason="CLEANUP_SIM_TEST")`
   then release the slot the same way a normal close does
   (`_notify_gateway_close(297, "CLEANUP")` / the gateway's slot-release path).
3. **Restart** backend (`launchctl kickstart -k gui/$UID/com.mems26.backend`) — this also loads
   `65dff60` (the reconcile→System 6 connection) so a future phantom auto-alerts.

## Verify (paste ALL — this is the go/no-go for a clean DB)
```
PSQL=/Applications/Postgres.app/Contents/Versions/latest/bin/psql
# a) zero active trades
$PSQL postgresql://localhost/mems26 -c "SELECT id,mode,state FROM v9_trades WHERE state NOT IN ('CLOSED','closed');"
#    → expect 0 rows
# b) 297 is CLOSED
$PSQL postgresql://localhost/mems26 -c "SELECT id,state FROM v9_trades WHERE id=297;"
#    → state=CLOSED
# c) gateway slots free — via the status endpoint or a debug print
curl -s localhost:8000/api/v9/system6/diagnose 2>/dev/null | head   # or the gateway status
#    → demo_slot=None, live_slot=None
# d) one reconcile pass → AGREED_FLAT (not a mismatch)
```
Also confirm the frontend active-trade card is GONE after refresh.

## Result
0 active trades + both slots free + Sierra flat + AGREED_FLAT → the DB is clean and the I-58
fallback will attribute the next fill to the REAL trade. THEN it's safe to flip Sierra to live.
Paste the four outputs; Cowork confirms clean before the live flip.
