# CC handoff — execute SIM test BUY + find the exact ORDER_FAILED reason + fix (2026-07-06 night)

Owner: Claude Code (on the Sierra machine — can read the Sierra Message Log + files
Cowork can't). SIM MODE ONLY — no real money. Do NOT flip to live until the SIM
proof is green + Michael signs off.

## State (all verified by Cowork today)
- OUR side fixed: DLL 90567fb (parses+applies `account`, `sc.SendOrdersToTradeService=1`,
  captures `sc.GetTradingErrorText`), backend ORDER_FAILED handling (fill_poller `_check_result`),
  A7 fire_setup stop fallback (woodies). DLL rebuilt v9.4.3 (`MES_AI_DataExport_64.dll` Jul 6 21:11).
  Backend restarted (fixes loaded). Live armed (LIVE_TRADING_V1=1, LIVE_EXECUTION_V1=1),
  FIXED_CONTRACTS_2=1, RISK_HALT_V1=1/CAP=400, account `SIERRA_LIVE_ACCOUNT=37138283`.
- Sierra: Sim Mode ON, Auto-Trading-Global ON, account 37138283 on the DOM (per Michael).
- BLOCKER: a SIM test BUY still fails. Message Log (21:22): `MEMS26: ORDER_FAILED error=-1
  (GENERAL_ERROR_OR_NOT_ENABLED) BUY`. So `sc.BuyEntry` is rejected — order placement not
  fully enabled at the Sierra level, even with Auto-Trading-Global on. No ENTRY fill written.
- Note: our FillPoller clears `trade_result.json` (fill_poller.py:166), and it logged
  `error=-1 (unknown)` — i.e. the DLL's `error_text` reached the Message Log but NOT
  `trade_result.json`. Verify + fix that too (the error_text should land in trade_result).

## Task
1. Confirm Sierra **Trade Simulation Mode = ON** + 0 open positions (safety).
2. Fire a 1-contract SIM test BUY — write the command:
   ```bash
   python3 - <<'PY'
   import json,time
   d=json.load(open('/Users/michael/SierraChart_Data/v9_export/live_price.json'))
   p=float(d['price'])
   cmd={"op":"PLACE","action":"BUY","trade_id":"CCTEST-"+str(int(time.time())),
        "direction":"LONG","price":p,"contracts":1,"stop_price":round(p-8,2),
        "target_price":round(p+8,2),"account":"37138283","mode":"live",
        "context":{"test":True,"sim":True},"ts_submitted":time.time()}
   open('/Users/michael/SierraChart_Data/v9_export/trade_command.json','w').write(json.dumps(cmd,indent=2))
   print("wrote",cmd["trade_id"])
   PY
   ```
3. **Read the REAL reason** — the DLL logs to Sierra's Message Log (you can read the Sierra
   log file; Cowork can't). Get the exact `GetTradingErrorText`. Also check whether the DLL
   writes `error_text` into `trade_result.json` (fix if it only goes to the Message Log).
4. **Diagnose GENERAL_ERROR_OR_NOT_ENABLED with Auto-Trading-Global already ON.** Likely the
   study's per-instance **"Allow Support for Sending Orders to Trade Service" = Yes**, OR the
   chart trading-enable, OR the account connection/authorization (IronBeam/Teton logged in for
   trading), OR a Sim-Mode requirement. Tell Michael the EXACT Sierra setting to flip; fix code
   if it's ours.
5. **Verify (Rule 5):** re-fire → `trade_fills.json` ENTRY fill → P&L, in Sim. Paste raw
   command + output. That is the SIM proof (OPEN_ITEMS A1). + NOT-DONE section.

## Guardrails
SIM only. 1 contract. Do NOT flip to real until SIM proof green + Michael sign-off. Snapshot
before any .env/DLL change. Flatten any accidental position immediately.
