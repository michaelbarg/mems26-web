# CC Handoff — Pipeline 5 order placement: rewrite per the RESEARCH (supersedes the piecemeal fixes) 2026-06-26

_Author: Cowork. **Authority for this work = `docs/research/SIERRA_ORDER_ROUTING_RESEARCH_2026-05-24.md`** —
read it fully first. The piecemeal attempts tonight (OCO-groups, separate C1 limit, deferred-C1) were
guesses that ignored this research. Replace them with the research's documented Attached-Orders pattern.
DEMO/Sim only · `EnableOrderPlacement` default OFF · LIVE stays stub._

## What went wrong (so you don't repeat it)
- The 3-contract entry kept returning **ORDER_FAILED/-1**. Root cause was **`sc.MaximumPositionAllowed`
  defaulting to 1** (now set to 10) — NOT the OCO groups. The OCO-group / attached-order approach was
  abandoned for the wrong reason.
- The "separate C1 limit after the entry" (immediate, then deferred to the exit-monitor) **never placed** —
  because the research **explicitly says do NOT roll your own target/stop after the parent fills**
  (§1.4, verbatim): *"It definitely is not recommended for you to implement yourself … Target and Stop
  orders by sending both of them after the parent order fills … Sierra Chart internally will manage for
  you through the Attached Orders feature."*
- Earlier the back-test notice appeared after adding `MaintainTradeStatisticsAndTradesData=1`. The research
  recipe **keeps that flag** — the real fix is the `IsFullRecalculation/DownloadingHistoricalData` guard
  (below), which stops trading on historical bars so the flag is safe.

## REWRITE — implement exactly per the research (§1.2, §5.1, §5.3)

### 1. SetDefaults — the FULL recipe (research §1.2). Add the missing flags:
```cpp
sc.SupportAttachedOrdersForTrading                 = 1;   // already present
sc.MaximumPositionAllowed                          = 10;  // already present (was the -1 cause)
sc.AllowOnlyOneTradePerBar                         = 0;   // CRITICAL — default 1 → silent SCT_SKIPPED_ONLY_ONE_TRADE_PER_BAR
sc.MaintainTradeStatisticsAndTradesData            = 1;   // RE-ADD (safe once guarded, see #2) — needed for position/trade tracking
sc.AllowMultipleEntriesInSameDirection             = 1;
sc.SupportReversals                                = 0;
sc.AllowOppositeEntryWithOpposingPositionOrOrders  = 0;
sc.CancelAllOrdersOnEntriesAndReversals            = 0;
sc.AllowEntryWithWorkingOrders                     = 1;
sc.CancelAllWorkingOrdersOnExit                    = 0;
```
(A SetDefaults change → study REMOVE+RE-ADD to take effect; re-add resets EnableOrderPlacement→0, re-arm.)

### 2. Guard ALL trading on the real-time path (research §5.1 line 407) — this fixes the back-test trigger:
```cpp
if (sc.IsFullRecalculation || sc.DownloadingHistoricalData) return;  // before any sc.BuyEntry/Modify/Exit
```

### 3. The bracket = Attached Orders on ONE entry (research §5.1) — REMOVE the separate/deferred C1 entirely:
```cpp
s_SCNewOrder o;
o.OrderQuantity   = contracts;                 // 3
o.OrderType       = SCT_ORDERTYPE_MARKET;      // market entry
o.TimeInForce     = SCT_TIF_DAY;               // futures bracket legs: DAY, not GTC (research §6)
o.Stop1Price      = stop_price;                // protective stop (all contracts)
o.AttachedOrderStop1Type   = SCT_ORDERTYPE_STOP;
o.Target1Price    = t1_price;                  // C1 first target
o.AttachedOrderTarget1Type = SCT_ORDERTYPE_LIMIT;
// partial C1: the Target1 attached order on 1 contract (the runners carry no target).
//   Use the attached-order quantity mechanism per Sierra's Attached Orders feature (verify the exact
//   s_SCNewOrder field against sierrachart.h — e.g. the per-target quantity / OCOGroup quantities now
//   that MaximumPositionAllowed=10 no longer rejects multi-lot). If a clean 1-of-3 attached target
//   isn't expressible, fall back to Target1 on all 3 (all-out) and let the MANAGER do the partial via
//   MODIFY/EXIT — but try the attached partial first.
o.TextTag = client_order_id;                   // correlation (research §1.12)
int r = is_buy ? sc.BuyEntry(o) : sc.SellEntry(o);
if (r > 0) {
    sc.GetPersistentInt64(1) = o.InternalOrderID;        // parent
    sc.GetPersistentInt64(2) = o.Target1InternalOrderID; // C1 target child  (research §1.5)
    sc.GetPersistentInt64(3) = o.Stop1InternalOrderID;   // stop child
    // write ORDER_SUBMITTED + the 3 ids to trade_result.json
} else { /* ORDER_FAILED, write r (the SCT_SKIPPED_* / SCTRADING_ORDER_ERROR code) to trade_result for diagnosis */ }
```
Sierra manages the OCO server-side. Do NOT submit the target/stop separately.

### 4. DYNAMIC management = the manager MODIFIES the attached children (research §5.3) — this is "the manager drives Sierra":
- `MODIFY_STOP` (trail / stop→BE after C1): `sc.ModifyOrder` with `Mod.InternalOrderID = stopID; Mod.Price1 = new_stop;` (ABSOLUTE price; attached children use Price1, NOT Stop1Price). Check the child is still `SCT_OSC_OPEN` first.
- `MODIFY_TARGET` (re-anchor runner target): same via the target child id.
- `EXIT` (partial runner exit): `sc.SellExit`/`BuyExit` with OrderQuantity.
- `CANCEL`/flatten: `sc.CancelOrder(id)` / `sc.FlattenAndCancelAllOrders()`.
- The C1 first-target fills automatically (attached Target1) → backend sees the fill → manager moves stop→BE (MODIFY_STOP) → trails runners. **The bracket is the vehicle; the manager's MODIFY/EXIT commands are the dynamic management.**

## Verify (research §6 gotchas + Rule 5)
- grep EVERY field/method/const you use vs `sierrachart.h` (e.g. `BuyEntry, ModifyOrder, CancelOrder,
  Target1InternalOrderID, Stop1InternalOrderID, GetPersistentInt64, SCT_TIF_DAY, IsFullRecalculation,
  DownloadingHistoricalData`) — confirm each exists BEFORE saying done (the FlattenAndCancelOrders lesson).
- Build the monolith. Commit (do NOT leave uncommitted).
- Live Sim (Michael+Cowork on deploy): a 3-lot entry shows in Sierra as **entry + 1 attached stop (3 lots)
  + 1 attached target (C1)**; when C1's target fills → 1 out, stop auto-reduces to 2; a MODIFY_STOP command
  moves the stop. Confirm `trade_result.json` ids + `trade_fills.json` C1 fill.

## NOT-DONE / guardrails
Deploy/Remote-Build/re-add + arm = Michael, out of hours. DEMO/Sim only. Mode-ladder: SHADOW/DEMO(Sim) =
global Trade-Sim-Mode ON + SendOrdersToTradeService 0 (research §1.3). Do NOT enable LIVE.
