# Next-chat continuation prompt · 2026-05-23 PM

**Date generated:** 2026-05-23 19:10 IL
**Author:** Cursor agent
**For:** Michael (paste into the next chat to resume cleanly)

---

## TL;DR

Pre-LIVE plan is V2-stable. Pkg 0 shipped (commit `1c805ea`). Pkg 1 handoff is finalized + 4-fix Claude Desktop review applied. D-093 + Pipeline 5 (Sierra Order Routing · 9 packages) locked — discovered no MEMS26 trade has ever reached Sierra (DLL TODO + unwired bridge + dead executors). Pkg 1 mega prompt is the next thing Claude Desktop builds; Pipeline 5 P5-0 audit is the next thing CC runs in parallel.

---

## Paste-this prompt for the next chat

> Resume MEMS26 pre-LIVE work from 2026-05-23 PM. Read these in order before anything else:
>
> 1. `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` (V2 master plan · §13 Pipeline 5 is newest)
> 2. `docs/plans/STATUS_BOARD.md` (current build queue · Pipeline 1 + Pipeline 5)
> 3. `docs/decisions/D-091_S2_LIVE_SCOPE.md` (S2 LIVE scope · adaptive stop · 2 pseudo-code bugs documented in §Stop calculation)
> 4. `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` (Pipeline 5 spec · 9 packages · 2 sub-decisions Q1/Q2 deferred)
> 5. `docs/handoff/DESKTOP_PKG1_ADAPTIVE_STOP_HANDOFF.md` (Pkg 1 finalized handoff for Claude Desktop)
> 6. CLAUDE.md + `.cursor/rules/mems26-pre-live-protocol.mdc` (guardrails)
>
> Then check progress on:
> - **Pkg 0 G3:** PASS (Cursor verified · commit `1c805ea`). Pending Michael: Redis migration mode (rename or drop chart_5min keys via `scripts/pkg0_redis_migrate.py`).
> - **Pkg 1:** Ready for Claude Desktop mega-prompt build. Handoff is in `DESKTOP_PKG1_ADAPTIVE_STOP_HANDOFF.md` with all corrections applied.
> - **Pipeline 5 P5-0:** Pending CC audit. Handoff to be drafted next session (gateway reconciliation · verify-first).
>
> Strategic stops waiting on Michael:
> 1. Redis migration mode for Pkg 0 (rename/drop)
> 2. D-093.Q1 gateway canonical (after CC P5-0a audit report)
> 3. D-093.Q2 Sierra DEMO account identifier
> 4. S1 Day Type verify report
> 5. S3 Footprint verify report (incl. O-4 entry/stop audit)
> 6. 10 P-W open questions on S4 Woodies (Pipeline 2 build start gate)
> 7. EXIT_V6 fix for 7 day types
>
> Do NOT advance any G2 (CC execution) until Michael signs off on the relevant strategic stop above.

---

## Current state snapshot

### Pipeline 1 · S2 D-091

| Pkg | State |
|-----|-------|
| **0** | ✅ G3 PASS · commit `1c805ea` · 5613 LOC deleted from `chart_5min/` · 5 systems registered |
| **1** | ⏳ Handoff finalized · awaiting Claude Desktop mega-prompt build |
| 2a-c | ⏳ Spec locked · queued behind Pkg 1 |
| 3a-c | ⏳ Spec dep on EXIT_V6 fix (7 day types) |
| 4a-b | ⏳ Spec dep on Pkg 3 |
| 5a-c | ⏳ Spec locked (Bulkowski edges · lock 3) · independent |
| 8 (Quality V2) | ⏳ Spec dep on Authority Table |
| **6** | ⏳ LAST · hook-based extensible · depends on ALL above |

### Pipeline 5 · Sierra Order Routing (NEW)

All 9 packages queued · waiting on Q1 (gateway canonical · CC audit) + Q2 (DEMO account · Michael).

### Open per-Michael decisions

1. **Redis migration mode** for Pkg 0 (`scripts/pkg0_redis_migrate.py` · rename vs drop).
2. **D-093.Q1** Gateway canonical · choose after CC delivers P5-0a audit.
3. **D-093.Q2** Sierra DEMO account · NOT PA-APEX-125218-01 (placeholder).
4. **EXIT_V6 fix** for 7 day types (Pkg 3a blocker).
5. **10 P-W open questions** on S4 Woodies (Pipeline 2 build-start gate).
6. **S1 Day Type verify report** (Pipeline 3).
7. **S3 Footprint verify report** including O-4 audit (Pipeline 4).
8. **SPEC_LOCK_TEMPLATE.md V2** simplification (Cursor in-progress).

---

## Pkg 1 handoff · what to know

`docs/handoff/DESKTOP_PKG1_ADAPTIVE_STOP_HANDOFF.md` has these critical sections:

- **§1 · 2 D-091 pseudo-code bugs documented + corrected formulas.** Bug 1: `reduce_size_signal` inequality reversed. Bug 2: `max(struct, cap, floor)` doesn't enforce floor. Corrected: `stop = min(max(struct, cap), floor)` for LONG · mirror for SHORT. Floor semantics = Option A (hard 4-tick minimum distance).
- **§1 + §8 · "TESTS ARE AUTHORITY."** If D-091 pseudo-code conflicts with §4 tests, tests win.
- **§4 · 18 golden tests** with full arithmetic table for tests 6/7/8 covering Layer A/B/C binding.
- **§7 + §8 + §9 · 4 layers of guard** for `five_min_system.py` lines 206-208 (chronic toxicity comment · deferred to Pkg 2a · forbidden to modify in Pkg 1).
- **§7 · line 5 verify-before-edit** safeguard against M13 (if Pkg 0 already cleaned · report "skipped" not invent a fake reference).

---

## D-093 · what to know

Pre-LIVE deep dive uncovered 4 gaps:

1. **DLL never places orders** — `MES_AI_DataExport.cpp:813-815` is `result_status = "ACK_SHADOW"` instead of `sc.SubmitOCOOrder()`. **Every mode (SHADOW/DEMO/LIVE) is paper-trading today.**
2. **Two `TradingGateway` impls** coexist · only legacy `backend/v9/gateway/` is wired in main.
3. **3 dead executor stubs** in `gateway/{live,demo,shadow}_executor.py` (24 LOC each · unimported).
4. **Bridge `TradeCommandHandler`** (193 LOC · checksum + polling complete) never wired on startup.

**9 packages · ~9.5 CC days · 5-6 calendar days with buffer.**
P5-0 verify-first must complete before any other Pipeline 5 work.

---

## What Cursor will do next chat

1. Draft `DESKTOP_PIPELINE5_P5-0_GATEWAY_AUDIT_HANDOFF.md` (CC verify-first task).
2. Wait for Claude Desktop to ship Pkg 1 mega prompt + paste to CC.
3. Review Pkg 1 G3 (CC delivery) per `.cursor/rules/mems26-pre-live-protocol.mdc` four-UAT-axes.
4. Resume Pipeline 1 packages 2a/2b/2c after Pkg 1 G6.
5. If Michael provides D-093.Q1/Q2 answers → unblock Pipeline 5 packages.

---

## Files changed this session (for git-stash awareness)

- `docs/decisions/D-091_S2_LIVE_SCOPE.md` (corrected pseudo-code · added Floor semantics)
- `docs/decisions/D-093_SIERRA_ORDER_ROUTING.md` (NEW · 9-package spec)
- `docs/plans/PRE_LIVE_PIPELINE_2026-05-23.md` (added §13 Pipeline 5 + 3 amendments)
- `docs/plans/STATUS_BOARD.md` (added Pipeline 5 board · 4 new pre-flight items · 3 new amendments)
- `docs/handoff/DESKTOP_PKG1_ADAPTIVE_STOP_HANDOFF.md` (4 Claude Desktop review fixes applied)
- `docs/handoff/NEXT_CHAT_CONTINUATION_2026-05-23_PM.md` (this file)

No source code touched. No git commits made (Cursor doesn't commit without explicit ask).

---

*End of continuation prompt · paste-ready · 2026-05-23 19:10 IL*
