# CC MEGA PROMPT — complete MEMS26 to LIVE-ready (2026-07-05)

You are Claude Code on the Mac. Mission: finish the remaining BUILD so the tool
is complete, then help run the validation window. Read these first, in order:
`docs/plans/COMPLETION_ROADMAP_2026-07-05.md` · `docs/plans/GAP_ANALYSIS_2026-07-05.md`
· `CLAUDE.md` · `docs/handoff/CC_HANDOFF_CONTRACT.md`.
Everything below is pushed to origin `stabilize/mems26-local-truth-2026-05-16`.

## Ground rules (non-negotiable)
- Every new behaviour flag-gated **default-OFF**. Nothing changes live trading
  until Michael enables it.
- Every fix gets a **fails-on-old** regression test (stash the fix → the test
  must FAIL → pop). A test green on `HEAD~1` is rejected.
- Restart ONLY via `launchctl kickstart -k gui/$(id -u)/com.mems26.backend`,
  after a 0-open-trades check. NEVER manual nohup.
- `python3 scripts/gen_flag_index.py` after any flag change; `--check` must PASS.
- Update `docs/plans/STATUS_BOARD.md` + `ROADMAP_TO_LIVE.html` per completed item.
- End with an explicit NOT-DONE list. STOP + ask Michael before enabling any flag
  or any trading-risk decision.

## CURRENT STATE (verified 2026-07-05 22:1x — this supersedes any earlier draft)
LIVE (ON): RR_ENTRY_GATE_V1 · FIXED_CONTRACTS_3 · DAYTYPE_TARGETS_STRUCTURAL ·
resolver(item-2) · counter-SKIP(item-1) · RUNNER_TRAIL_V1 · I-53/57/58/59/60/61/62.
**ENABLED for the Monday DEMO validation window (Michael 07-05):**
`STOP_RESOLVER_V1=1` · `TARGET_ZONES_V1=1` · `S4_ENTRY_CONFIRM_V1=1` (all wired,
now ON in .env). Built + WIRED but flag-OFF: item-18 DAY_DIRECTION_DOCTRINE_V1 ·
item-10 OPENING_WINDOW_FIRE_V1 (auto-enable Mon) · item-19 RISK_HALT_V1 ·
item-21 EOD_RISK_WINDOW_V1 · System 6 (SYSTEM6_SUPERVISOR / SYSTEM6_EXIT_SIGNALS /
SYSTEM6_EXIT_JOURNAL — endpoint `/api/v9/system6/diagnose` live; exit engine has
stall/opposite/counter_flow/**cvd_divergence** + hold_confirmation gate + journal
outcome-fill). 120 session tests green. Read modules; extend, don't duplicate.

## BUILD QUEUE — Michael's 07-05 ruling: ONLY item-11 is commissioned now
The rest is DEFERRED until a profitable demo baseline (don't build them yet).
1. **item-11 sizing consolidation — THE only commissioned build.** See the
   dedicated handoff `docs/handoff/CC_ITEM11_SIZING_CONSOLIDATION_2026-07-05.md`.
   Retire the legacy `calculate_size` path (still in 5 files) so V2 is the ONLY
   sizer + TradeManager single-point close-notify. Fails-on-old test for the
   A5-reject-while-V2-said-3 bug. Real LIVE-blocker (two sizers can disagree).

**DEFERRED until the demo proves a profitable baseline (do NOT start):**
item-12 TT_SPEC_V2 · item-13 PB_SHAPE_FILTER_V1 · item-16 VOL_REGIME (wider stops
+ entry-confirm, contracts stay 3) · item-17 entry-side journal · item-7/8
(phase/pullback) · shallow-S4 fixes (FAMIR_SPEC_V2/HTLB/TT) · Mechanism-C
behavioral test · System-6-advisory enable · manager-backtest de-bias · item-20
reconcile periodic alert (delivery-mechanism TBD with Michael).
Rationale: prove item-4/22/6 improve the demo first; add more only on a
profitable base, so attribution stays clean.

## VALIDATION PATH (after the build)
Enable the proven pieces as ONE package in DEMO (resolver/zones/doctrine/System 6
advisory), run a CLEAN 5-demo-day window: ≥+2R cumulative AND zero mechanical
faults, with RISK_HALT_V1 + reconcile live. That + Michael's sign-off = LIVE.

## Definition of done
Every profitability lever enabled, a clean 5-day demo ≥+2R with zero mechanical
faults, safety halts + reconcile live, Michael's sign-off. The code is nearly
there; the PROOF is the remaining distance.
