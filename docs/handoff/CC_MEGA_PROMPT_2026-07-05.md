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

## DO NOT REBUILD — already built this session (flag-OFF unless noted)
LIVE (ON): RR_ENTRY_GATE_V1 · FIXED_CONTRACTS_3 · DAYTYPE_TARGETS_STRUCTURAL ·
resolver(item-2) · counter-SKIP(item-1) · RUNNER_TRAIL_V1 · I-53/57/58/59/60/61/62.
Built + WIRED, flag-OFF: item-4 STOP_RESOLVER_V1 · item-22 TARGET_ZONES_V1 ·
item-6 S4_ENTRY_CONFIRM_V1 · item-18 DAY_DIRECTION_DOCTRINE_V1(+halt-proof) ·
item-10 OPENING_WINDOW_FIRE_V1 · item-19 RISK_HALT_V1 · item-21 EOD_RISK_WINDOW_V1.
System 6 (endpoint `/api/v9/system6/diagnose` live): SYSTEM6_SUPERVISOR ·
SYSTEM6_EXIT_SIGNALS (stall/opposite/counter_flow/cvd_divergence + hold_confirmation
gate) · SYSTEM6_EXIT_JOURNAL (v9_exit_decisions + outcome-fill hook + hit-rates).
120 session tests green. Read the modules; extend, don't duplicate.

## BUILD QUEUE (the remaining tool completion)
1. **item-11 sizing consolidation** — retire the legacy `calculate_size` path
   (still in 5 files) so V2 is the ONLY sizer; add the TradeManager single-point
   close-notify. Fails-on-old test for the A5-reject-while-V2-said-3 bug.
2. **item-12 TT_SPEC_V2** — the live TT detector is shallow (0 fires ever). Port
   the transcribed source spec (docs/spec_authority, TT) into `woodies/patterns/tt.py`;
   flag TT_SPEC_V2.
3. **item-13 PB_SHAPE_FILTER_V1** — pullback-shape filter (P/b).
4. **item-16 VOL_REGIME_V1** — volatile-day: WIDER stops + entry-confirm (NOT
   contracts — Michael ruled contracts stay 3). Canonical regime signal
   (avg-14-bar range, threshold 8pt).
5. **item-17 entry-side journal** — "why no trade" decision journal (entry side;
   System 6's v9_exit_decisions covers the exit side only). ADAPT the existing
   missed_trade_detector.
6. **Shallow S4 patterns** (pattern audit): FAMIR fires on the WRONG structure
   (FAMIR_SPEC_V2 built but OFF — validate + enable) · HTLB loose ±15pt tolerance
   + stop-anchor dispute (D-6) · TT (item-12). Fix or retire per the audit.
7. **System 6 finish**: (a) reframe the exit-signal weights to lean on
   cvd_divergence (net-positive) over raw counter_flow (net-negative); (b) T2/T3
   perspective in the runner path (item-22 zones govern the runner, exit signals
   can take it off early); (c) item-20 reconcile periodic alert (Michael declined
   a scheduled task — wire a throttled WARNING inside an existing backend loop OR
   surface it in the dashboard panel; ask him which).
8. **Mechanism-C behavioral test** — replace the tautological string-check
   (e291bed) with a real double-push-after-hours behavioral test.
9. **De-bias the manager backtest** — re-run `backtest_manager_combined.py` with
   INITIAL stops (from the management-log SMART_BE.from) + a structural endpoint,
   for a tighter number than the optimistic +574pt.

## VALIDATION PATH (after the build)
Enable the proven pieces as ONE package in DEMO (resolver/zones/doctrine/System 6
advisory), run a CLEAN 5-demo-day window: ≥+2R cumulative AND zero mechanical
faults, with RISK_HALT_V1 + reconcile live. That + Michael's sign-off = LIVE.

## Definition of done
Every profitability lever enabled, a clean 5-day demo ≥+2R with zero mechanical
faults, safety halts + reconcile live, Michael's sign-off. The code is nearly
there; the PROOF is the remaining distance.
