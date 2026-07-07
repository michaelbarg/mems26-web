# CC fix — DLL SendOrdersToTradeService must match Trade Simulation Mode (2026-07-07)

## ROOT CAUSE (SOLVED — from Sierra's official docs)
Every order fails `ORDER_FAILED error=-1 (GENERAL_ERROR_OR_NOT_ENABLED)` (now visible in
our log thanks to the error_text fix 64ab228). Per Sierra Chart documentation
(ACSILTrading + SupportBoard 82446):

> If global **Trade Simulation Mode is ON**, then `sc.SendOrdersToTradeService` **must be
> FALSE (0)** for any order action to work — otherwise the order is IGNORED and an error is
> given. If Trade Simulation Mode is OFF, `sc.SendOrdersToTradeService` must be TRUE (1).

CC set `sc.SendOrdersToTradeService = 1` (correct for LIVE) in SetDefaults. We are testing
in **Sim Mode ON** → **mismatch** → order ignored → GENERAL_ERROR_OR_NOT_ENABLED. This is
the entire reason no order has ever submitted (ORDER_SUBMITTED=0, no fill since 07-03).

## FIX (DLL — MES_AI_DataExport.cpp)
Make `sc.SendOrdersToTradeService` CONSISTENT with the sim/live state, and set it AFTER
the SetDefaults block (Sierra requires this — setting it inside SetDefaults when driven by
state has no effect):

```cpp
// OUTSIDE / after sc.SetDefaults — every call:
sc.SendOrdersToTradeService = sc.GlobalTradeSimulationModeIsOn ? 0 : 1;
```

- Sim Mode ON  → SendOrders = 0 → simulated fills work (SIM proof).
- Sim Mode OFF → SendOrders = 1 → real orders route to Teton/IronBeam.

This auto-matches whatever Michael has Sim Mode set to — no more mismatch, and it Just Works
for both the SIM proof and real live. Remove the hardcoded `=1` from SetDefaults.

## Verify (Rule 5)
1. Rebuild DLL + reload study.
2. Sim Mode ON → fire a 1-contract SIM test (trade_command.json) → expect `trade_fills.json`
   ENTRY fill + `ORDER_SUBMITTED` (NOT the GENERAL_ERROR). Paste raw. **That is the SIM proof.**
3. Then Sim Mode OFF → real order routes (supervised, 2c, −$400).

## Sources
- Sierra Chart — Automated Trading From an Advanced Custom Study:
  https://www.sierrachart.com/index.php?page=doc/ACSILTrading.html
- Sierra Chart Support Board — "SendOrdersToTradeService is not consistent with Trade
  Simulation Mode On": https://www.sierrachart.com/SupportBoard.php?ThreadID=82446
