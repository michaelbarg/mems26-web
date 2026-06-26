# CC Handoff — Pipeline 5 Phase 2: the DYNAMIC manager drives Sierra (DEMO)

_Author: Cowork. Contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC builds the DLL order-ops +
command protocol; Cowork verifies (and may take the backend wiring). **DEMO/Sim only. LIVE stays
a stub.** Highest-risk surface → smallest correct steps, Michael signs off before the first
autonomous DEMO arming. Michael chose this (full dynamic) over a static-bracket DEMO so that
DEMO == the validated SHADOW strategy._

## STATUS — Phase 1 DONE + PROVEN LIVE (2026-06-26)
Entry placement works end-to-end in Sierra Trade Simulation Mode:
`trade_command.json (BUY bracket)` → DLL places an OCO (entry+stop+T1) → `trade_result.json:
ORDER_SUBMITTED` → `trade_fills.json: {kind:ENTRY, order_id:1, price:7417.25, contracts:1}`.
Feed stayed live throughout (MoveFileEx in the DLL + the promoter sidecar). The hard part — a
real Sim order round-tripping — is proven. Phase 2 adds the dynamic MANAGEMENT on top.

## DLL OPERATIONAL FACTS LEARNED TODAY — do NOT re-hit these (each cost a rebuild cycle)
1. **`sc.SupportAttachedOrdersForTrading = 1`** in `sc.SetDefaults` is REQUIRED for an entry with
   attached stop/target. Without it `sc.BuyEntry/SellEntry` return **-1 (ORDER_FAILED)**.
2. **Do NOT set `sc.MaintainTradeStatisticsAndTradesData`.** It engages Sierra's trade-stats /
   back-test machinery; with `sc.AutoLoop=1` + a live feed it triggers the Message-Log notice
   *"disconnect from the data feed before you can perform a Bar Based Back Test"* and BLOCKS
   real-time order placement. (We added it, hit exactly this, removed it.)
3. **SetDefaults changes only take effect on a fresh study ADD** — a Remote-Build *reload* is NOT
   enough. After deploying any SetDefaults change: **REMOVE the study from the chart + RE-ADD it.**
   (This was the actual fix for the persistent -1 — the flag was in the DLL but never applied to
   the existing study instance.)
4. **Re-adding resets Input #21 `Enable Order Placement` to 0** (the default) → must RE-ARM (=1).
5. Sierra side also needs: **Trade → Auto Trading Enabled - Global = ON** and **Trade Simulation
   Mode = ON**; chart trade account = the Sim account.
6. Deploy = `scripts/mems26_snapshot.sh` (or `build_monolithic_cpp.sh --deploy` auto-snapshots) →
   Remote Build → **re-add study** → re-arm. The promoter keeps the feed safe through the reload.

## TARGET MODEL (the trade rule — 3 contracts · C1→BE · dynamic runners)
- Entry = pattern fire. **3 contracts.** ONE trade at a time (gateway is already single-slot).
- Attach ONE **protective (catastrophic) stop** on all 3.
- **C1** (1 contract) takes the first profit target → then **stop → BE** on the remaining 2.
- **Runners:** on each NEW consolidation, **MODIFY_STOP** (trail) and **MODIFY_TARGET**
  (re-anchor: next target = the earlier of {new structural place, next key level —
  POC/VAH/VAL/IB/PDH/PDL}); repeat through T3+. Exits are structure-driven, not fixed numbers.
- This is exactly what `manager.apply_dynamic_struct_trail` + `consolidation.detect_consolidation`
  already do for SHADOW — Phase 2 makes those same decisions reach Sierra.

## BUILD
### A. Command protocol — extend `backend/v9/services/sierra_command.py` / `trade_command.json`
Beyond the existing `PLACE`, add (each carries the Sierra order_id(s) the DLL reported back):
- `MODIFY_STOP { order_id, new_stop }`
- `MODIFY_TARGET { order_id, new_target }`
- `EXIT { order_id, contracts }`  (market exit, partial or full — runner exits / C1 scale-out)
- `CANCEL { order_id }`  (kill-switch / feed-loss flatten)
Keep the clear-after-read contract. Version the schema (add an `op` field) so the DLL dispatches.

### B. DLL order-ops (`sc_study/MES_AI_DataExport.cpp`, all behind `EnableOrderPlacement>=1`)
- **PLACE (adapt):** 3-contract entry + protective stop on all 3 + T1 as a **partial** target on
  1 contract (C1). (Today's bracket is all-out — make the target partial; ACSIL attached-order
  quantity, verify against headers.)
- **MODIFY_STOP / MODIFY_TARGET:** modify the tracked attached stop/target (cancel-replace or
  `sc.ModifyOrder`) using the persistent OCO ids (100-103) already stored.
- **EXIT:** market-exit N contracts of the open position.
- **CANCEL:** cancel working orders / flatten.
- Report EVERY resulting fill (`C1`/`T1`, runner exits, `BE-STOP`, final `STOP`) to
  `trade_fills.json` (extend the existing exit-monitor; it already detects `SCT_OSC_FILLED`).
- Keep order placement/modify on the **real-time** path only (the on-demand command already
  arrives real-time; ensure modify/exit do too — never act during historical recalc).

### C. Backend — wire the dynamic manager to EMIT commands when `MEMS26_MODE=demo`
- The manager's existing SHADOW actions (C1 scale-out, stop→BE, trail, re-anchor) currently only
  mutate in-memory state. In demo, each must also emit the matching command (A) for the DLL.
- **Fill priority / no double-manage:** keep `bar_level_detector` bar-fills to `mode=="shadow"`
  only; DEMO/LIVE trade state is driven by the **fill_poller** reading real Sierra fills (the
  poller exists + is `DEMO_EXECUTION_ENABLED`-gated). Verify this gate end-to-end.
- Store the Sierra `order_id` on the trade when `PLACE` is ACKed so MODIFY/EXIT can reference it.

### D. Reconcile + safety
- One-trade-at-a-time (gateway single-slot — confirm it blocks a 2nd setup while one is live).
- RiskValidator gates the DEMO branch.
- Reconcile manager state ↔ Sierra position: handle partial fills, order rejects, and a
  feed-loss/kill-switch **flatten** (CANCEL + market-exit). Never let manager state and the
  Sierra book diverge silently.

## VERIFY (Rule 5 — paste raw; Sierra Sim, out of trading hours)
One crafted setup → 3-contract entry + protective stop → C1 scale-out + stop→BE → at least one
consolidation re-anchor (MODIFY_STOP/MODIFY_TARGET visible in the Sierra order log + a fill line
in `trade_fills.json`) → final runner exit → realized PnL in `v9_trades` that **matches the
manager's intended exits on the same setup in SHADOW**. Paste the Sierra order log + fills JSON +
the backend manager log. Plus: a backend unit test that a manager trail-action emits the right
command (mock the writer), and that `bar_level_detector` does NOT bar-fill a demo trade.

## NOT-DONE / guardrails
LIVE path (stays stub) · real-account wiring · the autonomous arming itself (Michael signs off +
we run supervised) · retiring the promoter sidecar. DEMO/Sim ONLY · `EnableOrderPlacement` +
`DEMO_EXECUTION_ENABLED` default OFF · snapshot before every DLL deploy · no DLL reload during RTH.
