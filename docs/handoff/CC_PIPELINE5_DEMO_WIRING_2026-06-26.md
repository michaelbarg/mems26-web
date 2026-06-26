# CC Handoff — Pipeline 5 DEMO: complete the end-to-end wiring (Option C) — 2026-06-26

_Author: Cowork. Michael approved **Option C**: KEEP the monolithic gated gateway, ADAPT only the
DEMO **execution** so it creates a real `mode="demo"` TradeManager trade — so the manager's dynamic
MODIFY commands actually reach Sierra. **Do NOT swap the gateway** (`services/trading_gateway/` is a
392-line skeleton with **0** of the 18 gates; swapping drops kill_switch / feed_watchdog / risk-caps /
day-type / cluster / RR). DEMO/Sim only · `DEMO_EXECUTION_ENABLED` default OFF · LIVE stays stub._

## Why (tonight's audit — verified, with line numbers)
The demo path was never wired end-to-end. The DLL places orders and the manager has dynamic-management
methods, but they are disconnected. Verified gaps:

1. `backend/v9/gateway/trading_gateway.py::_execute_demo` (~650) creates a **legacy dict** via
   `_build_trade`/`_persist_trade` — NOT a TM trade in `mode="demo"`. The only TM trades are shadow
   (`_execute_shadow` → `accept_setup(..., "shadow")`, line 623). So `manager._is_demo_mode`
   (`trade.mode=="demo"`, manager.py:102-106) **never matches** → no Sierra emit, ever.
2. `quality["sierra_order_id"]` is **never written** (no writer exists anywhere) → `_get_sierra_order_id`
   (manager.py:108-112) always returns None → even `_emit_modify_stop` returns early.
3. `fill_poller.register_order` is **never called**; the ENTRY handler (fill_poller.py:124-130) reads only
   `order_id`+`price` and **drops** the `c1/c2/c3_target_id` + `c1/c2/c3_stop_id` the DLL writes
   (DLL lines 999-1012).
4. `manager.on_target_hit` (manager.py ~282) has **sequential-target** semantics: `T3 → CLOSED` closes the
   whole trade. But the DLL now writes `T1=C1`, `T2=C2`, `T3=C3` **per-contract** fills
   (DLL lines 1232 `tgt_kinds={"T1","T2","T3"}`, one contract each). Each `Tn` is ONE contract scaling out;
   the trade must close only when all 3 are out.
5. DLL bracket (lines 958/968) **synthesizes garbage** runner targets `t1*2` / `t1*3` when `t2/t3 <= 0`
   (trail setups: `t3=None` per `five_min_system.py:166`). Rule 1 violation (honest failure > synthetic).
6. DLL fill write **overwrites** `trade_fills.json` per fill (lines 1255, 1278) → concurrent fills
   (e.g. a STOP taking 2 runners at once) can be lost between 0.25s polls.
7. `manager.apply_dynamic_struct_trail` (line 664) emits `_emit_modify_target(trade, next_tgt)` with **no id**
   → DLL falls back to slot 2 = **C1's** target. Runners (C2/C3) are never re-anchored by their own ids.

## The fix — ordered. Phase 1 = foundation (A–C). Phase 2 = dynamic per-runner (D–E). Phase 3 = DLL (F).

### A. Demo TM trade (link 1) — `_execute_demo`
Replace the legacy-dict body with a TM demo trade. Mirror `_execute_shadow`'s `tm_setup` construction
(trading_gateway.py:601-622) but call `accept_setup(tm_setup, "demo")`. Keep the `command_from_setup`
call. Return a dict with `"trade_id"` = the TM trade id (so `demo_slot` / `result["demo"]` at
lines 437-438 keep working). Commit the TM session after accept_setup (as shadow does at 627).
Do NOT also create the legacy `_build_trade` dict for demo.

### B. Seed real initial runner targets (link 5, backend half) — in the demo path before `command_from_setup`
If `t3` is None/<=0 but `t1` and `t2` are real: `t3 = 2*t2 - t1` (one structural step beyond t2; works
both directions — LONG t1<t2 → t3>t2; SHORT t1>t2 → t3<t2). If `t2 <= 0`, leave it 0 (DLL will place that
group stop-only). Put the seeded `t3` on BOTH the `tm_setup` (so `trade.t3` is real for the manager) and the
command context. Comment it: "initial trail target; manager re-anchors to structure (earlier of {new place,
key level})."

### C. Store the Sierra ids on the trade (links 2,3) — fill_poller + new manager method
- New `manager.set_sierra_order_ids(trade_id, ids: dict)` — merge into `trade.quality`:
  `sierra_order_id` (= ENTRY `order_id`), `c1_target_id`, `c1_stop_id`, `c2_target_id`, `c2_stop_id`,
  `c3_target_id`, `c3_stop_id`; then flush. Skip keys whose value is 0/None.
- `fill_poller` ENTRY handler: after `on_fill`, call `tm.set_sierra_order_ids(trade_id, {...})` reading the
  6 ids from the fill dict. (No `register_order` needed — single-slot demo + the most-recent-active fallback
  already resolves the demo trade. Leave the fallback.)

### D. Per-contract re-anchor (link 7) — `apply_dynamic_struct_trail`
Leave **C1 (t1) FIXED** — never re-anchor it. Keep the existing front-runner advance (lines 637-641:
advance t2 while C2 unfilled, else t3). Route the emit to the FRONT runner's own id:
`_emit_modify_target(trade, next_tgt, target_order_id=q["c2_target_id"])` while C2 open, else
`...q["c3_target_id"]`. NEVER emit to C1. Only emit if that id exists in `trade.quality`.

### E. Per-contract lifecycle (link 4) — `on_target_hit`
Each `Tn` fill = ONE contract out (scale-out), not a sequential target of one position:
- `T1`→ PARTIAL + smart-BE (keep current).
- `T2`→ scale out 1; keep trailing the remaining runner(s); do **not** force the old `_apply_stop_after_t2`
  if it assumes a fixed remaining size — make it size-aware.
- `T3`→ scale out the last runner; CLOSE the trade only if it is the last open contract (use a
  remaining-contracts count from the fills, or the DLL STOP `group` field + an all-out check). PnL per
  contract.
Add a regression test that `on_target_hit("T3")` does NOT close while C2 is still open.

### F. DLL fixes (link 5 DLL half + link 6) — `sc_study/MES_AI_DataExport.cpp`
- (i) Remove the `t1*2` / `t1*3` synthesis (lines 958, 968): if `t2/t3 <= 0`, **do not attach** that group's
  target — that group becomes stop-only (no synthetic target). Honest failure (Rule 1).
- (ii) Concurrent-fill safety: **append** to `trade_fills.json` (or write one fill per line and have the
  poller read ALL lines) instead of overwriting — so a simultaneous STOP+target or 2-runner stop is not lost.
- Verify EVERY field/method vs `sierrachart.h` before "done". Build the monolith. Commit.
  Michael Remote-Builds + re-adds; **Cowork `--deploy`s after verifying the diff** (the lesson).

## Verify (Rule 5 — paste command + raw output, never "✅")
- Behavioral (offline): in demo mode, a fired setup → TM trade `mode="demo"`; on ENTRY fill
  `trade.quality` has all 6 ids; `apply_dynamic_struct_trail` emits `MODIFY_TARGET` for `c2_target_id`
  (assert the order_id in the command), NOT C1; `on_target_hit("T3")` keeps the trade open while C2 open.
- Regression green: `test_pipeline5_phase2`, `test_dll_exit_monitor`, `test_risk_caps`.
- Live (Michael + Cowork on deploy): demo fire → **3 contracts in Sierra at 3 different target prices**;
  a bar re-anchor **moves a runner target in Sierra** (Message Log); each contract exits at its own point;
  C1 first-target fill → stop→BE on the runners.

## NOT-DONE / guardrails
DEMO/Sim only · `DEMO_EXECUTION_ENABLED` default OFF · Michael arms `EnableOrderPlacement` (Input #21).
Do NOT touch the 18 gates. Do NOT swap the gateway. Local PG only. LIVE stays stub. Per CLAUDE.md
Change-Safety: snapshot before the `.env`/DLL deploy. Update `STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`
on completion (finding + fix + verification per Reporting Workflow).
