# CC Batch Queue — "run everything except Pipeline 5" (Michael 2026-06-24)

_Author: Cowork · contract: `docs/handoff/CC_HANDOFF_CONTRACT.md`. CC develops each task end-to-end; Cowork verifies EACH (code + tests GREEN + **backtest where applicable** + **NOT-DONE**) before it counts as done._

## Rules for this batch (read first)
- **One task at a time, in order.** Finish + write a per-task report (code + raw test output + backtest + NOT-DONE) before starting the next. Do NOT batch-commit half-done work.
- **Every behavior change is flag-gated, default-OFF**, unless it is a pure bug-fix or a safety-halt (T2). Trading-surface stays SHADOW; no enabling without Michael.
- **Anti-tautological tests** (flag-OFF = unchanged; flag-ON = the new behavior; a counter-case that must NOT fire). Run the FULL regression suite with the new flag ON (flag-interaction has bitten 4×).
- After each task: `python3 scripts/gen_flag_index.py` (+ `--check`=0) and update `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html`.
- **EXCLUDED from this batch:** Pipeline 5 (real DEMO order path to Sierra / DemoExecutor) — leave it; it's the only thing that should remain open after this queue.
- **NOT in scope (needs Michael's source sheets, not CC-buildable):** GHOST / FAMIR / GB100 / TT spec-rewrites. (TT already root-caused: fires but very rare — `outputs/tt_diagnostic.py`. ZLR + VEGAS already done.)

---

## T1 — Dynamic structure-trailing manager (THE HEART) — flag `DYNAMIC_STRUCT_TRAIL` (OFF)
Full spec: **`docs/handoff/CC_DYNAMIC_STRUCT_TRAIL_2026-06-24.md`** (read it — it has the audit map + exact rule). Summary: C1→first target→BE (exists); runners re-anchor on each NEW CONSOLIDATION (≥K bars tight range after advance) → move stop beyond the zone + next target = earlier of {zone, next key level POC/VAH/VAL/IB/PDH/PDL}; repeat through T3+. Woodies (S4) = separate params. Build the consolidation detector (K/R/M tunable in `config/stop_anchors.yaml`), wire into `bar_level_detector.on_bar()`, manage runner portion. Tests + **backtest vs static T2/T3** + NOT-DONE.

## T2 — Feed-watchdog + halt-on-death (LIVE blocker #0) — flag `FEED_WATCHDOG` (OFF in shadow; designed for ON at LIVE)
06-19 Juneteenth: bridge `bars_5min` died ~12:00, half-RTH blind, orphan position (186/187). Build: a watchdog that, during RTH, marks any canonical stream stale (`bars_5min` / `woodies_5min` / `live_price` last-update > threshold, e.g. 90s) → set readiness `HALTED`, **block all new fires**, emit a WARNING + alert (T7); auto-resume when fresh. Never silently trade on a dead feed. Tests: simulate stale stream → new fires blocked + halt logged; stream fresh again → resume. Reference CLAUDE.md §Bridge / the 06-19 EOD.

## T3 — Bug #1 [P0]: S4 `process_bar` crashes on `stop=None`
DLL-sourced ZLR/HFE fires can yield `stop=None` → `process_bar` raises. Root-cause where `None` propagates (woodies_system stop path), fix so a missing stop **skips the fire with a rate-limited WARNING, never crashes**. Regression test: a bar that produces stop=None → no crash, no trade, logged. (HFE now disabled lowers frequency but the path must be crash-safe.)

## T4 — Bug #3 [P1]: S2 detection on a partial bar (b4)
S2 can detect on an incomplete (still-forming) bar. Fix: S2 detects only on CLOSED bars. Regression test: a partial bar → no S2 fire; the closed bar → normal.

## T5 — Kill-switch (UI + API + script) — LIVE pre-flight
One control to instantly halt ALL firing (S2+S4) and (later) cancel working orders: an API endpoint (`POST /api/v9/admin/kill`), a CLI script, and a dashboard button. When engaged: every system returns no-fire, logged + alerted. Tested live (engage → next setups blocked; disengage → resume). Default DISENGAGED.

## T6 — Risk-caps audit + enforce
Verify and (where missing) enforce, with tests: per-trade max risk (`MEMS_MAX_RISK_POINTS`=60 exists), **daily-loss limit** (halt for the day after −$X), **consecutive-loss cooldown** (exists in gateway — verify wired), **max trades/day**. Report what's enforced vs missing in a table; add the missing as config-tunable caps (`config/stop_anchors.yaml` or risk config). Counterfactual test per cap (cap hit → next fire blocked).

## T7 — Alerting (health + trade)
Emit alerts on: feed-death/watchdog-halt (T2), uncaught error, and each fire/exit. The repo already has a Slack hook stub (`SLACK_WEBHOOK_URL`/`SLACK_UAT_WEBHOOK` — currently unset; the commit hook references it). Wire a minimal alerter (log + webhook-if-set), starting with the watchdog-halt + daily-loss-halt as critical alerts. Test with the webhook unset (no crash) and set (payload built).

## T8 — Redundancy (launchd + status hook)
Confirm + harden auto-restart: backend + bridge LaunchAgents use the conditional KeepAlive (CLAUDE.md §LaunchAgent Stability — do NOT set KeepAlive=true), `V9_DISABLE_WATCHDOG` exported, bridge local-only. Add a status hook (`/api/v9/admin/services/status` already exists — verify it reports bridge+backend+feed liveness). Document the recovery runbook.

---

## After this queue, the ONLY open LIVE item is **Pipeline 5** (DEMO execution → Sierra) + accumulating SHADOW-profitable days. Report each task to Cowork for verification as you finish it.
