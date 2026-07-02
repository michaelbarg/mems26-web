# CC — 06-30 End-to-End Fire Simulation: what SHOULD have fired (with-trend) & the EXACT blocker per signal

**Date:** 2026-06-30 · **Owner:** Michael · **Prepared by:** Cowork
**Contract:** `docs/handoff/CC_HANDOFF_CONTRACT.md` — paste command + raw output (Rule 5), anti-tautological tests, mandatory NOT-DONE.

## Why
06-30 was a **TREND/CONT day** (day_type=Variation, opened OPEN_DRIVE, ~+96pt move) → **0 trades**. Michael wants the REAL, end-to-end reason **no WITH-TREND (continuation) trade fired** — via a **simulation on today's bars** that traces every signal to its exact death-stage. Cowork's live-log analysis narrowed it but Michael (rightly) wants a definitive replay, not piecemeal greps. **Find the single real root per with-trend signal.**

## Decided context — do NOT re-litigate
- **Backtest verdict (215 shadow trades 06-05→06-29, Cowork today, `v9_trades` mode=shadow):** REV on trend days = **−34.6R** (74 trades, 38% win); CONT = **+11.1R** (92, 64%); **ZLR +5.3R**, INITIATIVE_LONG +4.1R, TLB +2.8R. ⇒ **The edge is CONT/with-trend. Enabling reversals is OFF the table (data-proven loser).** The screenshot's GHOST SHORT blocked by `daytype_position_gate` is **correct**. The ONLY question: **why did the +EV with-trend (CONT) signals produce 0 trades today?**

## Goal
Replay **06-30 RTH** (`v9_bars_5min_woodies` where ts::date='2026-06-30') through the REAL detection + full gate pipeline. For EVERY signal, record the exact stage it died + why. Definitively answer: **which CONT signals were valid with-trend setups that should have traded, and the single root blocker for each.**

## Method (use the existing replay/backtest harness, or a focused replay)
For each 06-30 bar, in sequence, run the REAL functions and record pass/fail+reason:
1. **Detection** — `pattern_engine.detect_all_patterns` + the DLL-flag ZLR/HFE build path (`woodies_system.py:358-430`) on the bar buffer; `five_min` INITIATIVE/REACTIVE. Record every signal + source (python-detector vs DLL-flag).
2. **Sizing / RISK_CAP** — woodies giant_bar / RISK_CAP (`woodies_system.py:679-721`; `GIANT_BAR_EXCLUDE=ZLR,HFE` → ZLR `STRICT_SKIP` if stop>cap). Record stop_pts, cap(15), SKIP/SIZE_DOWN.
3. **fire_setup / A7** — decision_tree A1–A7 (`decision_tree.py:349-434`), `ready_to_route`. (CC's `fd153c3` A7 fix is live — confirm it PASSES for a routable CONT.)
4. **Auth (S2)** — `get_auth_cell(pattern, day_type)` (`auth_table_v1.py:134`). Record verdict (INITIATIVE@Variation=FULL; @Normal/UNKNOWN→Neutral_Center=SKIP).
5. **Gateway** — `daytype_position_gate.decide` (family gate), `direction_context`, `cont_trend_filter`, `cluster_guard` (`trading_gateway.py:380-450`). Record allow/block + which gate.
6. **DEMO slot** — D-094 R:R selection (`on_bar_close`, `trading_gateway.py:452-510`): did the CONT signal win/lose the single demo slot?

## Required output — per-signal trace table
`ts | sys | pattern | CONT/REV | dir | day_type@bar | trend | stage_reached | DIED_AT | reason | [ZLR: dll_flag? backend_detected? stop_pts/cap]`

## Specific questions (Rule 5 — paste raw)
1. The **9 ZLR detections** today: stop_pts vs 15-cap each; how many `STRICT_SKIP`.
2. The **DLL-flagged ZLRs the backend MISSED** (export `zlr=True` @21:35/21:40 IL = 18:35/18:40 UTC) — use the **ZLR-TRACE instrumentation (commit `3a8c16b`, live)**: is `closed_bar.zlr=True` but `routed.zlr=False` (**Mechanism A**: `current_bar` override `bars.py:954-988` drops the flag) OR `wb.zlr` arrives `is_new_bar=False` (**Mechanism C**: not-new-bar early-return `woodies_system.py:351` skips detection)? Quote the `[woodies_5min ZLR-TRACE]` / `[Woodies ZLR-TRACE]` lines.
3. Did ANY CONT signal reach `route_setup` → gateway today, and its fate (passed→demo? blocked→which gate? lost demo slot→D-094)?
4. The **"should have fired" call**: given the +96pt trend move, which CONT entries (ZLR/INITIATIVE/TLB) were valid with-trend setups, and the single root each was blocked.

## Known suspects — verify OR refute with raw data (Cowork's findings, build on them)
- **ZLR detection divergence** — DLL zlr flag (set on the CLOSED bar) dropped by current_bar routing override (`bars.py:954-988`) AND/OR not-new-bar early-return (`woodies_system.py:351`). Instrumented `3a8c16b`.
- **ZLR RISK_CAP** — `GIANT_BAR_EXCLUDE=ZLR,HFE` (`woodies_system.py:679`) → `STRICT_SKIP` when stop>15pt (volatile-day bars). Config decision → Michael.
- **A7/fire_setup** — `fd153c3` fixed (screenshot: `ready_to_route=true`). Confirm live for a routable CONT.
- **INITIATIVE auth-timing** — fired during UNKNOWN/Normal (pre-13:08 lock) → SKIP; @Variation post-lock = FULL.
- **FALSE ALARMS (do NOT chase, Cowork verified):** read.py→SQLite (standalone-only, live=Postgres 50 rows); cold buffer (buffer_size=50 live); S2→SHADOW (misleading log; route_setup runs DEMO too).

## Constraints
- **READ-ONLY simulation.** No flag flips, no live trading changes, no service restart for the sim (use the offline replay on DB bars; the live instrumentation is already deployed).
- **Rule 5:** command + raw output for every claim. Anti-tautological tests.
- **Deliverable:** `docs/reports/SIM_2026-06-30_WHAT_SHOULD_HAVE_FIRED.md` — the trace table + the SINGLE real reason no with-trend trade + the precise fix (flag-gated, Michael sign-off).

## NOT-DONE
- ❌ Do NOT enable reversals (backtest −34.6R).
- ❌ Do NOT flip `GIANT_BAR_EXCLUDE` / any trading flag without Michael sign-off — **propose, don't apply.**
- ❌ Do NOT re-chase the false alarms (read.py, cold buffer, S2-shadow).
- ❌ Do NOT "fix" by loosening the ZLR detector blindly — the sim must first prove Mechanism A vs B vs C.
