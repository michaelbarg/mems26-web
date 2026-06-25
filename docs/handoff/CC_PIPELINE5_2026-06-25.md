# CC Handoff — Pipeline 5: DEMO execution to Sierra (the last LIVE blocker) 2026-06-25

_Author: Cowork (after a full execution-surface audit) · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops (incl. the Sierra DLL — CC maintenance per CLAUDE.md); Cowork verifies. **Scope: DEMO only. Keep LIVE OFF.** Real orders → maximum care; this is the highest-risk surface in the system._

## Goal
Close the SHADOW→DEMO gap: an approved setup → a real **simulated** bracket order in Sierra (Trade Simulation Mode) → the fill comes back → the trade is managed by the existing manager → exits round-trip back. Then soak ≥7 DEMO days (SHADOW≈DEMO, 0 crashes) → the DEMO gate.

## What EXISTS — KEEP / ADAPT (from the 2026-06-25 audit — do NOT rebuild)
- **Order command schema + writer:** `backend/v9/services/sierra_command.py` (`write_trade_command`, `command_from_setup`) → writes `trade_command.json` (action/direction/price/contracts/stop/t1-t3/account/mode). KEEP.
- **Gateway DEMO branch:** `backend/v9/gateway/trading_gateway.py` `_execute_demo()` (~L633-646) already calls `command_from_setup(..., mode="demo")`. KEEP/ADAPT.
- **Sierra DLL command read + ACK:** `sc_study/MES_AI_DataExport.cpp` L851-920 — already **reads** `trade_command.json`, parses the action, writes `trade_result.json` ACK, clears the command file. KEEP — extend it (don't rewrite).
- **RiskValidator (W14):** `backend/v9/services/risk_validator/validator.py` — daily-loss/news/time/max-trades/consecutive-loss/size caps (DEMO returns allow; gate hardens at LIVE). KEEP.
- **Trade lifecycle + management:** `TradeManager` + `bar_level_detector.py` + DYNAMIC_STRUCT_TRAIL. KEEP — but see fill-priority below.

## BUILD — the gap (phased; DEMO only, flag-gated)

### Phase A — Sierra DLL: actually PLACE the order (the critical missing piece)
`sc_study/MES_AI_DataExport.cpp` L877-879 has the TODO ("implement sc.SubmitOrder/SubmitOCOOrder"). Implement, **gated so it only places when the study is in a DEMO-arming Input** (add a Sierra Input e.g. `Enable Order Placement` default OFF — never place unless explicitly armed):
1. Parse the FULL bracket from `trade_command.json` (action BUY/SELL, entry, stop, T1/T2/T3 from `context`, contracts).
2. Place an **OCO bracket** via `sc.SubmitOCOOrder()` (or `sc.BuyEntry`/`sc.SellEntry` + attached stop + scale-out targets) — entry + protective stop + T1/T2/T3 ladder, on the **simulated** trade account.
3. Write the submission result (Sierra order IDs, status, error) to `trade_result.json`.
4. On fill/partial/exit, write fill events to a NEW `trade_fills.json` (ts, order_id, trade_id, price, contracts, kind=ENTRY/T1/T2/T3/STOP). Clear-after-write like the command file.
- Deploy via `./scripts/build_monolithic_cpp.sh --deploy` → Remote Build → reload study (per `docs/runbooks/SIERRA_DLL_OPS.md`). Verify Input 11/12 paths + the new fills path under `~/SierraChart_Data/v9_export/`.

### Phase B — Backend: the fill/exit round-trip (no fill is read back today)
1. A fill-poller (async task, ~100-250ms, started only when `MEMS26_MODE=demo`) reads `trade_fills.json`.
2. On ENTRY fill → `TradeManager.on_fill(trade_id, sierra_fill_price)` (use the **Sierra** price, not a synthetic/bar price).
3. On T1/T2/T3/STOP fill → `TradeManager.on_target_hit/on_stop_hit(trade_id, ..., fill_ts, fill_price)` with the Sierra price → realized PnL from real fills.
4. Map Sierra order_id ↔ trade_id (store the order_id in `trade.quality` when the command is written).

### Phase C — Fill priority (don't double-manage)
`bar_level_detector.py` currently fills/exits SHADOW trades from **bar** prices. For DEMO trades it must **NOT** bar-fill — only the Phase-B poller (Sierra fills) drives DEMO trade state. Gate the bar-level fill path to `mode=="shadow"` only; DEMO/LIVE are Sierra-driven.

### Phase D — Mode wiring + end-to-end DEMO test
- `MEMS26_MODE=demo` + a `DEMO_EXECUTION_ENABLED` flag (default OFF) to arm the gateway DEMO branch at runtime (today it's hardcoded at startup — `backend/main.py:714-716`).
- Reconcile the inline `_execute_demo/_execute_live` vs the `services/trading_gateway/executors/*.py` modules (the roadmap's "Gateway canonical + RiskValidator merge") — ONE path, RiskValidator injected. Document which is canonical; delete/mark the orphan.
- **End-to-end DEMO round-trip test** (the proof): a crafted setup → command file written → DLL places a Sim order → fill in `trade_fills.json` → backend `on_fill` → manage → exit → realized PnL in `v9_trades`. Assert each hop.

## Verify (Rule 5 — paste raw) + NOT-DONE
1. Backend unit tests: fill-poller maps a `trade_fills.json` ENTRY/T1/STOP → the right `TradeManager` calls (mock the file). Bar-level path is mode-gated (DEMO not bar-filled).
2. DLL: a manual `trade_command.json` (BUY bracket) with the study armed in **Sierra Trade Simulation Mode** → a Sim order appears in Sierra → `trade_result.json` + `trade_fills.json` written. Paste the Sierra order log + the result/fills JSON.
3. Full backend suite green with `MEMS26_MODE=demo` + `DEMO_EXECUTION_ENABLED=1`.
4. **NOT-DONE:** LIVE path (keep stub/OFF), real-account wiring, any partial-fill/slippage edge cases, the Sierra Input arming UX.

**Hard guardrails:** DEMO + Sim account ONLY. `Enable Order Placement` Sierra Input default OFF. LIVE stays a stub. Local-only (no cloud). Strategic stop + Michael sign-off before the first DEMO arming. Do NOT enable LIVE.
