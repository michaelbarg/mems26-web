# CC Handoff — Pipeline 5 re-deploy (bundled with the permanent rename fix) 2026-06-26

_Author: Cowork. Contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC builds the DLL (CC
maintenance per CLAUDE.md); Cowork verifies. **DEMO/Sim only. LIVE stays a stub.** Highest-risk
surface in the system → maximum care, smallest correct steps, Michael signs off before arming._

## Context (what changed since the last Pipeline-5 handoff)
- The 2026-06-25 freeze was **NOT** the order code — it was **Wine `rename()` can't replace an
  existing file** (clean v9.4.5 froze the same way). A native promoter sidecar
  (`scripts/v9_export_promoter.py` + LaunchAgent `com.mems26.export_promoter`) now keeps the
  bar feed live 24/7 by promoting `.tmp→.json` natively. Root cause + proof:
  `project_export_tmp_promotion_freeze_2026-06-25` (memory) + STATUS_BOARD 2026-06-26.
- **Therefore a DLL reload no longer freezes the feed** (the sidecar covers promotion). This
  unblocks re-deploying the Pipeline-5 DLL — but we still deploy **out of trading hours**.
- Backend half is **DONE + green** (poller ENTRY→`on_fill`, startup `DEMO_EXECUTION_ENABLED`-
  gated, `bar_level_detector` skips demo/live, 538 suite). Guardrails intact: `.env`
  `DEMO_EXECUTION_ENABLED` commented (OFF), LIVE stub.
- Order code is preserved at **`d784c3f`** (= clean v9.4.5 `816dd1a` **+198 lines order code
  only**, `git diff --stat 816dd1a d784c3f`). It is an **all-out** bracket: N contracts, one
  attached stop, one attached T1 (`s_SCNewOrder` `Stop1Price`/`Target1Price`), gated behind
  `EnableOrderPlacement` Input #21 **default 0 (OFF)**; exit-monitor (persistent ints 100-103,
  `SCT_OSC_FILLED` → writes `{kind:STOP|T1}` to `trade_fills.json`) also gated OFF.

## PHASE 1 — re-deploy order code + fix the rename at the source (THIS deploy, out of hours)
Smallest correct step to the milestone "a real Sim order round-trips end-to-end."

**A. Restore the order code (no rewrite — it's in git):**
```
git checkout d784c3f -- sc_study/MES_AI_DataExport.cpp
```
Confirm: `grep -c 'EnableOrderPlacement' sc_study/MES_AI_DataExport.cpp` ≥ 1 and
`EnableOrderPlacement.SetInt(0)` is present (default OFF). Re-verify the compile-fix from
`d784c3f` is in (no `sc.GetOrderCountForBar`).

**B. Fix `v9_write_json` so the DLL's own promotion works under Wine** (per
`docs/handoff/CC_EXPORT_RENAME_FIX_2026-06-26.md`): replace `std::rename(tmp,path)` with
`MoveFileExA(tmp, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)` (+ the
`std::remove`+`std::rename` fallback for native test builds). This makes the DLL self-sufficient;
the sidecar stays running as belt-and-suspenders through verification.

**Build + deploy (out of trading hours — weekend, or a CME break):**
`./scripts/build_monolithic_cpp.sh --deploy` → Sierra Remote Build → reload study
(`docs/runbooks/SIERRA_DLL_OPS.md`). Confirm Inputs: #21 `Enable Order Placement` = **0**,
#22 `TradeFillsPath` = `~/SierraChart_Data/v9_export/trade_fills.json`.

**Verify Phase 1 (Rule 5 — paste raw), study armed-OFF first:**
1. **Feed unaffected:** after reload, all study `.json` (woodies/5min/cvd/tpo) stay ≤2s for
   ≥10 min across ≥1 new bar — now via the DLL's OWN MoveFileEx rename (temporarily
   `launchctl unload` the sidecar to prove the DLL fix alone, then reload the sidecar). Paste a
   sampled mtime+last-ts table. Dir mtime advances (renames landing).
2. **No order placed while OFF:** with `EnableOrderPlacement=0`, write a manual
   `trade_command.json` (BUY bracket) → confirm `trade_result.json` ACK but **zero** Sim orders
   in Sierra and **no** ENTRY line in `trade_fills.json`. (Guardrail proof.)
3. **Then arm + ONE controlled Sim trade, Michael present** (Sierra Trade Simulation Mode):
   `EnableOrderPlacement=1` → one crafted setup → Sim OCO appears → ENTRY in `trade_fills.json`
   → backend `on_fill` (FILLED) → let it hit T1 or STOP → exit-monitor writes `{kind:T1|STOP}`
   → backend `on_target_hit`/`on_stop_hit` → realized PnL in `v9_trades`. Paste the Sierra order
   log + `trade_fills.json` + the backend log lines. Disarm (`=0`) after.

## PHASE 2 — runner management to Sierra (SEPARATE deploy, after Phase 1 proves out)
**Design decision for Michael before CC builds this.** Phase-1's bracket is **all-out** (all
contracts exit at one T1/stop). Michael's trade rule is **3 contracts · C1 takes the first
target → stop to BE · runners managed dynamically** (re-anchor on each new consolidation, exit
at the earlier of {new structure, key level}) — i.e. **not** a static T1/T2/T3 ladder. So Phase 2
is the *dynamic manager reaching Sierra*, not a fixed ladder:
- Partial target: T1 on C1 (1 of 3); stop on all 3.
- After C1 fills → backend sends a **modify-stop→BE** command; DLL modifies the Sierra stop.
- Runners → backend dynamic structure-trail (`apply_dynamic_struct_trail`) emits **modify-stop**
  / **market-exit** commands at structural points; DLL executes them; each exit fill round-trips
  to `trade_fills.json`.
- Needs: DLL support for **modify/cancel-replace** + market-exit-on-command; backend command
  schema for modify/exit; the fill round-trip already exists. All behind `EnableOrderPlacement`.
- (If Michael instead wants fixed R-based T2/T3 for specific day-types, that's a static-ladder
  variant — but default to the dynamic path since that's the manager he built.)

## Guardrails (unchanged, hard)
DEMO + Sim account ONLY · `EnableOrderPlacement` Input default 0 · `DEMO_EXECUTION_ENABLED`
default OFF · LIVE stays a stub · local-only · **no DLL reload during RTH** · keep the promoter
sidecar running until the MoveFileEx fix is proven over a full session · strategic stop +
Michael sign-off before the first arm.

## NOT-DONE (explicit)
LIVE path · real-account wiring · partial-fill/slippage edges · Phase-2 modify/exit path (design
pending) · retiring the sidecar (only after MoveFileEx proven ≥1 full session).
