# CC — Close the backend↔Sierra loop: DLL must report fills (trade_fills.json is never written)

**Date:** 2026-07-01 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — command + raw output (Rule 5), tests, NOT-DONE.
**Priority:** HIGH — the demo→Sierra link is **one-way**. Orders go OUT and submit, but no fill/position comes BACK, so the backend never knows a trade actually filled/closed. Michael: "I don't see an active trade in Sierra — I need them to talk and be connected."

## What works (verified)
- Backend fires → writes `trade_command.json` (op=PLACE) → **the DLL reads it + places a real order** (`sc.BuyEntry`/`sc.SellEntry` with Stop1+Target1, `MES_AI_DataExport.cpp:982`) → writes `trade_result.json` = **`{"status":"ORDER_SUBMITTED","error":0}`**. So the send-channel is connected and Sierra accepted order 267.

## The gap (root)
1. **The DLL never writes fills back.** `TradeFillsPath` is defined (input 22, `MES_AI_DataExport.cpp:49,148 → trade_fills.json`) but **there is NO code that writes to it** — the file stays 0 bytes. The DLL DOES read `OrderStatusCode == SCT_OSC_FILLED` internally (L1085/1252/1275) to manage stops/targets, but never EXPORTS those fills.
2. Consequence: `fill_poller.py` (runs at `MEMS26_MODE=demo`, reads `trade_fills.json`, `_process_fill` at L135) is **starved** → the backend can't confirm entry fills, target/stop fills, or the close → it "guesses" trade state from price bars → the demo slot sticks (see `CC_DEMO_SLOT_RECONCILE_2026-07-01.md`) and the monitor can't show real Sierra state.

## Do
1. **DLL fill export (PRIMARY):** in `MES_AI_DataExport.cpp`, whenever an order (entry / C1 target / C2 target / C3 / stop) transitions to `SCT_OSC_FILLED`, append a fill event to `trade_fills.json`: `{order_id, internal_trade_id, side, fill_price, filled_qty, ts, kind: ENTRY|TARGET|STOP}`. Use the order IDs already written to `trade_result.json` for correlation (`register_order` exists in `fill_poller.py:53`). Atomic write (tmp+rename, matching the export promoter pattern) so the poller reads whole events.
2. **Verify the poller consumes them:** `fill_poller._process_fill` → drives `TradeManager` → updates `v9_trades` (t1/t2/t3/stop hit + exit) from **Sierra truth**, and calls `on_trade_close` → frees the demo slot. (Fixes the stuck slot at the source.)
3. **Sierra-platform check (Michael):** confirm the chart has **Auto-Trading enabled + Trade Simulation ON** so `sc.BuyEntry` creates a **visible** position (not just ORDER_SUBMITTED). Confirm `ORDER_SUBMITTED` actually becomes a FILLED position in Trade Activity (else it's submitted-but-not-filled — a Trade-Sim config issue, not code).
4. **Deploy:** `sc_study/` → `./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload study (per CLAUDE.md §Sierra DLL; snapshot first).

## Tests / verify (Rule 5)
- Place one demo order → `trade_fills.json` gets an ENTRY fill event → `fill_poller` logs `_process_fill` → `v9_trades` entry confirmed from Sierra. When a target/stop fills → the matching contract closes; when all close → `on_trade_close` frees `demo_slot`.
- Sierra Trade Activity shows the position for the life of the trade (Michael visual).

## NOT-DONE
- ❌ Do NOT mark fills in the backend without a real Sierra fill event — reconcile against Sierra truth, never a guess.
- ❌ Do NOT change entry gates / sizing here.
- ❌ Do NOT place/modify/cancel orders from Cowork — DLL + Sierra own execution.

## Related (same session)
`CC_DEMO_SLOT_RECONCILE_2026-07-01.md` (slot stuck — this fill-loop is its root cause). Committed same session: FIXED_CONTRACTS_3, DAYTYPE_CONFIRM_BARS, /active-prefers-demo, DAYTYPE_POSITION_GATE=0 (validation), 'c'-crash fix — all pending the next (safe) restart.
