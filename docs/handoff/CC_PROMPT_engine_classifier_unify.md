# CC prompt — paste into Claude Code

Build #68 part-b: unify the LIVE engine's per-bar `day_type` to the validated 7-type classifier.
Follow `docs/handoff/CC_S68_ENGINE_CLASSIFIER_UNIFY_2026-06-22.md` exactly, and the rules in
`docs/handoff/CC_HANDOFF_CONTRACT.md` and `CLAUDE.md` (Pre-LIVE discipline, Rule 5 raw verification).

Hard constraints:
- New flag `S1_ENGINE_NEW_CLASSIFIER`, **default OFF**. Do NOT enable it. Do NOT set it in `.env`.
- **Market is open today (RTH).** You MAY do Step 1 (pure-fn refactor) now — it's route-only and
  restart-safe. Do NOT do the Step 2 per-bar wiring restart while RTH is live unless I say so; stage the
  code flag-OFF and tell me it's ready to restart after close.
- Hot path: the per-bar classify must run from the machine's **in-memory bars/levels — no new DB reads**
  per bar. Health must stay <100ms. Fail-safe: any error → keep the old-engine value, never throw.

Steps:
1. Extract the core of `daytype_classify_routes.py::classify_replay` into a pure
   `backend/v9/systems/day_type/classifier_core.py::classify_session(...)`. `classify_replay` calls it.
   Prove (Rule 5) the endpoint output is unchanged on all 11 validated days
   (Trend_Normal=06-05 · Trend_DD=06-16/17 · Normal_Variation=06-10/12/15 · Neutral_Center=06-09/11 ·
   Neutral_Extreme=06-08 · Normal=06-18 · Nontrend=06-19).
2. In `backend/main.py::_day_type_on_bar`, after `process_bar`, flag-gated on `S1_ENGINE_NEW_CLASSIFIER`
   + `ib_locked`: call `classify_session(...)` from in-memory state, map 7-type→`DayType`
   (`Normal_Variation→Variation`; rest direct), set `state.day_type` and `day_type_machine._last_state.day_type`,
   fail-safe. This **replaces** the old `S1_LIVE_RECLASS`/`ShadowReclassifier` block (3-type, vah/val/poc/cvd=None).
3. Confirm `cockpit/systems-snapshot` system-1 reflects the promoted `state.day_type`.

Tests (anti-tautological): parity test for `classify_session` vs current endpoint on the 11 days;
engine-promotion test (06-11 bars → promoted type with flag ON; unchanged with flag OFF; flip a known
day → promoted type flips); latency assertion (<5ms added per bar, no DB).

Report back with: the diff, raw test output, and a **NOT-DONE** section. Do NOT enable the flag — I enable
`S1_ENGINE_NEW_CLASSIFIER=1` only after reviewing a SHADOW session (pill==Build-Status==per-bar event==
day_type_at_entry stamp, all bars, 0 tracebacks, health<100ms). Also flag the `v9_bars_5min` raw-stream
stall (blocker-LIVE #0) — the classifier's bar source must be the fresh table, not the stalled one.
