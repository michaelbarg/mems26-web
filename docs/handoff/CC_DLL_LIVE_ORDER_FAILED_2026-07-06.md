# CC handoff — LIVE ORDER_FAILED (-1) root cause + DLL fixes (2026-07-06)

Owner: Claude Code (DLL maintenance — needs Sierra-machine rebuild + deploy per
`docs/runbooks/SIERRA_DLL_OPS.md`). Verified live 2026-07-06 during Michael's real-money session.

## Symptom
Every LIVE fire → `trade_result.json = {"status":"ORDER_FAILED","error":-1}`. No
position (real money safe), but each failed fire leaves a phantom PENDING live trade +
occupies the gateway live_slot (system doesn't handle ORDER_FAILED).

## Root cause (verified by reading the DLL)
`sc.BuyEntry(o)` / `sc.SellEntry(o)` (`sc_study/MES_AI_DataExport.cpp:981-983`) returned
**-1** (runtime rejection). The trading recipe is correct (`:62` SupportAttachedOrdersForTrading=1,
`:63` MaximumPositionAllowed=10, `:64` AllowOnlyOneTradePerBar=0). But:

1. **The DLL IGNORES the `account` field.** It parses price/stop_price/target_price/
   contracts/direction (`:927-930`) but NOT `account`. grep for
   `account|SelectedTradeAccount|SendOrdersToTradeService|GetTradingErrorText` in the DLL = 0 hits.
   → `SIERRA_LIVE_ACCOUNT` in `.env` does NOTHING; the order uses the CHART's selected
   trade account. (Cowork's .env account "fix" was useless — corrected.)
2. **`sc.SendOrdersToTradeService` is never set** → routing to the real broker is not
   explicitly enabled (may simulate or defer to chart config).
3. **The DLL captures no error detail** — writes only `error=%d` (=-1). We are blind to
   the real Sierra reason (`sc.GetTradingErrorText(r)` / the trade service message).

The -1 itself is most likely: Auto Trading not armed on the chart, OR the trade account
not selected/authorized on the chart, OR SendOrdersToTradeService. Michael's immediate
Sierra-side unblock: select account 37138283 on the trade DOM + arm order placement.

## DLL fixes (rebuild + deploy on the Sierra machine)
1. **Capture the real error** (highest value — stops us being blind): on `r <= 0`, write
   `sc.GetTradingErrorText(r)` (or the trade-service message) into `trade_result.json`
   alongside `error`. So the next failure tells us WHY.
2. **Apply the account**: parse `"account"` from `trade_command.json` and set the order's
   trade account (`sc.SelectedTradeAccount = <account>` or the order field). So our
   command controls the account, not just the chart.
3. **`sc.SendOrdersToTradeService = 1`** (in the trading recipe) so orders route to the
   real broker (Teton/IronBeam), not internal sim — gate this so DEMO still simulates.

## Backend fix (Mac side, CC or Cowork)
4. **Handle ORDER_FAILED**: on `trade_result.json` status=ORDER_FAILED, the FillPoller/
   gateway must mark the trade CANCELLED and RELEASE the live_slot — currently it leaves
   a phantom PENDING trade + a stuck slot (Cowork cleared 293/296 manually today).

## Verify (Rule 5)
Rebuild DLL → deploy → SIM/live fire → `trade_result.json` shows either ORDER_SUBMITTED
(with order IDs) OR ORDER_FAILED **with the real error text**. Paste raw. Then the account
+ SendOrders fixes proven by a Sierra-SIM order that fills. NOT-DONE section.

## Related
The Sierra config side (account selected on chart + Auto Trading armed) is Michael's, not
code. This is also the long-missing SIM proof (OPEN_ITEMS A1) — do it in Sierra Sim Mode first.
