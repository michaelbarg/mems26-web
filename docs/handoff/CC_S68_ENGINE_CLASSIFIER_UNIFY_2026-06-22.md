# CC Handoff — Unify the LIVE engine to the validated 7-type classifier (#68 part-b)

**Date:** 2026-06-22 · **Owner:** Cowork → CC · **Contract:** see `docs/handoff/CC_HANDOFF_CONTRACT.md`
**Risk:** trading-surface (live per-bar day-type) · **Default:** flag-OFF · **Enable:** Michael sign-off + SHADOW validation
**Do NOT build/restart the engine mid-RTH** — the live `day_type_machine` accumulates session state; do this when the market is closed.

## Goal
Make the LIVE engine's per-bar `day_type` come from the **validated 7-type classifier** (the one
behind `classify_replay`, Michael-approved 11/11), so EVERY surface agrees by construction:
pills / `cockpit/systems-snapshot` / per-bar `day_type_classification` event (S2/S4) / `day_type_at_entry`
stamp == Build Status. Today (2026-06-22) they disagreed (pills=old-engine "Variation",
Build Status=new "Normal_Variation") because two classifiers run in parallel.

## Current state (diagnosed 2026-06-22)
- **Per-bar handler:** `backend/main.py` `_day_type_on_bar` (~L206) → `day_type_machine.process_bar()` (L285).
  The machine is the OLD classifier (3 live types: Trend_Normal/Variation/Normal).
- **Existing promotion (wrong source):** L288–330, flag `S1_LIVE_RECLASS` (default OFF), promotes a
  crude `ShadowReclassifier` whose `vah/val/poc/cvd` are hardcoded `None` (L304–307) and which only
  emits Normal/Variation/Trend. **This is NOT the validated classifier — do not enable it.**
- **Validated classifier:** embedded in `backend/v9/api/v9/daytype_classify_routes.py::classify_replay`
  (L78+). Reads RTH bars + Sierra TPO IB/VA + history; returns `{"final": {"day_type","status",...}}`.
  **Not reusable** as-is (logic lives inside the route).
- **Enum:** `backend/v9/systems/day_type/state_machine.py` `DayType` has all 7 +Neutral/Normal/Variation.
- **Display already unified (Cowork, done):** `systemStateStore` S1 reads only `classify_replay`; dead
  `/current` wrappers retired. So part-b is ONLY the engine/per-bar path.

## Build (flag-gated `S1_ENGINE_NEW_CLASSIFIER`, default OFF)
1. **Refactor classifier into a pure fn** — extract the core of `classify_replay` into
   `backend/v9/systems/day_type/classifier_core.py::classify_session(bars, ib_high, ib_low, vah, val,
   poc, profile_shape, ib_width_hist) -> {day_type, status, segments, measured}`. `classify_replay`
   then calls it (no behavior change to the route — regression-test that the endpoint output is byte-identical
   on the 11 validated days BEFORE wiring the engine).
2. **Per-bar wiring** — in `_day_type_on_bar`, after `process_bar`, when `S1_ENGINE_NEW_CLASSIFIER` is on
   AND `ib_locked`: call `classify_session(...)` using the bars/levels **already in memory on the machine**
   (NO new per-bar DB reads — must not block the single-worker event loop; health must stay <100ms).
   Map the 7-type string → `DayType` (`Normal_Variation→Variation`; others direct), set `state.day_type`
   and `day_type_machine._last_state.day_type`. **Fail-safe:** any error → keep the old-engine value
   (never throw on the hot path). Replace the `S1_LIVE_RECLASS`/ShadowReclassifier block.
3. **Snapshot** — confirm `cockpit/systems-snapshot` system-1 reads the promoted `state.day_type` /
   `_last_state` (so it follows automatically). If it reads a different field, point it at the promoted one.

## Tests (anti-tautological — per contract)
- `classify_session` parity: same output as the current `classify_replay` on all 11 validated days
  (Trend_Normal=06-05 · Trend_DD=06-16/17 · Normal_Variation=06-10/12/15 · Neutral_Center=06-09/11 ·
  Neutral_Extreme=06-08 · Normal=06-18 · Nontrend=06-19).
- Engine promotion: feed 06-11 bars (failed-low→reversal) → with flag ON the machine's `state.day_type`
  becomes the validated type; flag OFF → unchanged (old engine). Flip a known day → the promoted type flips.
- Latency: per-bar handler adds <5ms (in-memory, no DB); health <100ms under the 5s poll floor.

## SHADOW validation (before any LIVE) — Rule 5
Enable `S1_ENGINE_NEW_CLASSIFIER=1` on a **closed market** or next session open; over one full RTH verify:
pill == Build Status == `day_type_classification` event == `day_type_at_entry` stamp (all equal, all bars),
0 tracebacks, health <100ms. Paste raw evidence.

## NOT-DONE / open
- `S1_LIVE_RECLASS` + `ShadowReclassifier` should be **removed** (superseded) once part-b lands — do not
  leave two promotion paths. Flag for Michael before deleting (it's referenced in main.py).
- The `v9_bars_5min` raw-stream stall (2026-06-22, stuck 08:55 while woodies/continuous live) is a
  SEPARATE infra blocker (blocker-LIVE #0, feed-watchdog) — the classifier's bar source must be the
  fresh table or the engine re-classifies on stale bars (same root that misclassified today).
- Enabling is a trading-risk-surface change → **Michael sign-off required**; do not set the flag without it.
