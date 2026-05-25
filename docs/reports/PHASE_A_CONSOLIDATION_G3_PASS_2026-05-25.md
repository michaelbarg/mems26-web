# Phase A Consolidation · G3 PASS Report · Stale-Fixture Repair

**Status:** GREEN
**Date:** 2026-05-25
**Reviewer:** Cursor agent (G3 adversarial)
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Authority:** `DESKTOP_PHASE_A_CONSOLIDATION_STALE_FIXTURES_HANDOFF` (Cursor 25/5 14:55)
**Phase A:** 15/15 COMPLETE

---

## 1 · Summary

Phase A Consolidation repairs 6 stale test fixtures that broke when Pkg 2bc introduced `MIN_BARS_REQUIRED=7` (commit `dfdf91f`). **Zero production code touched.** 3 test files modified (+30/-5). All 18 tests in the 3 target files pass. Zero regressions. Phase A is now 15/15 complete.

---

## 2 · Commits

| Commit | Subject | Files | +/- |
|--------|---------|-------|-----|
| `799e00c` | fix(test): Phase A Consolidation · stale-fixture repair | 3 | +30/-5 |
| `018526a` | docs(status): Phase A 15/15 COMPLETE | 1 | STATUS_BOARD update |

---

## 3 · Root Cause Analysis

Pkg 2bc (commit `dfdf91f`, 23/5 20:46) introduced `MIN_BARS_REQUIRED: int = 7` at `five_min_system.py:30`. The detectors (`_detect_reactive` at line 407, `_detect_initiative` at line 484) short-circuit with `(None, 0, {})` when `len(bars_5m) < 7`. Six tests in `backend/v9/systems/five_min/tests/` still supplied only 4 bars — the original pre-Pkg-2bc fixtures. Pattern assertions failed because the detector never reached the pattern logic.

The lookback contract (lines 433-437 for Reactive, 511-515 for Initiative) requires:
- 3 bars at `bars_5m[-7:-4]` with `v > 0` for all 3
- `max(lookback.volume) < b1.volume * LOOKBACK_MAX_VOL_RATIO` (0.6)

---

## 4 · Commit `799e00c` (3 files · +30/-5)

### `test_e2e_t1.py` (+18 lines)

| Fixture | b1.v | Lookback v | Volume check |
|---------|------|------------|-------------|
| `_bars_reactive_long()` | 1000 | 300 | 300 < 0.6 * 1000 = 600 |
| `test_reactive_short_mirror` inline | 1000 | 300 | 300 < 600 |
| `_bars_initiative_long()` | 600 | 200 | 200 < 0.6 * 600 = 360 |
| `test_initiative_long_poc_return_alt` inline | 600 | 200 | 200 < 360 |

Each prepend: 3 zero-range doji bars (`o==h==l==c`) at neutral price, with volume satisfying the lookback invariant. Pattern bars (last 4) unchanged.

Added `_get_belly_ratio_from_footprint` mock (return_value=2.0) to `test_reactive_long_full_pipeline` and `test_reactive_short_mirror`.

### `test_poc_return_alt.py` (+6 lines)

Both inline lists (`test_initiative_long_poc_return` + `test_initiative_long_no_hl_no_poc_fails`) extended with 3 lookback bars at v=200.

### `test_process_bar_emission.py` (+6/-5 lines)

`_reactive_long_bars()` extended from 4 to 7 bars (3 lookback at v=300 prepended). Added `_get_belly_ratio_from_footprint` mock to `test_process_bar_emits_setup_on_pattern_match` and `test_process_bar_handles_emitter_exception`.

---

## 5 · CC Discovery Beyond Handoff (Cursor Approved)

The `_get_belly_ratio_from_footprint` mock was not in the Cursor handoff — CC discovered during testing that Reactive detectors also gate on belly dominance ratio (introduced in Pkg 2bc alongside lookback). Without the mock, `_get_belly_ratio_from_footprint` returns `None` → graceful degradation (skip check) → test passes in ISOLATION but fails when combined with other tests that set up footprint state differently.

Adding `return_value=2.0` (above the 1.5 threshold) ensures deterministic PASS regardless of test execution order. Cursor approved during G3 as a defensive-correct extension of the fixture repair scope.

---

## 6 · Acceptance Criteria (7/7)

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All 6 originally-failing tests PASS | `pytest ...3 files... -v` → 18 passed / 0 failed |
| 2 | No new regressions in same dir | `pytest backend/v9/systems/five_min/tests/ -q` → 0 new failures |
| 3 | No new regressions in broader v9 sweep | `pytest tests/v9/ --ignore=tests/v9/api -q` → 30 failed / 1562 passed (identical to Pkg 6 G3 baseline) |
| 4 | Zero production-code changes | `git diff --stat ... -- ':!tests/'` → empty |
| 5 | Only 3 test files modified | `git diff --name-only` → exactly 3 files |
| 6 | ReadLints clean | 0 errors on all 3 files |
| 7 | Pattern semantics preserved | Lookback bars are zero-range dojis with low volume — don't trigger patterns |

---

## 7 · Regression Sweep

| Scope | Pre-Consolidation (`e7094d3`) | Post-Consolidation | Delta |
|-------|------------------------------|-------------------|-------|
| `tests/v9/ --ignore=api` | 30 failed / 1562 passed | 30 failed / 1562 passed | 0 (identical) |
| `backend/v9/systems/five_min/tests/` | 6 failed / 12 passed | 0 failed / 18 passed | -6 failures fixed |

---

## 8 · The 6 Fixed Tests

```
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_reactive_long_full_pipeline
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_reactive_short_mirror
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_initiative_long_fires
backend/v9/systems/five_min/tests/test_e2e_t1.py::TestE2EScenarios::test_initiative_long_poc_return_alt
backend/v9/systems/five_min/tests/test_poc_return_alt.py::TestPocReturnAlt::test_initiative_long_poc_return
backend/v9/systems/five_min/tests/test_process_bar_emission.py::test_process_bar_emits_setup_on_pattern_match
```

---

## 9 · `test_initiative_long_no_hl_no_poc_fails` Integrity

This test was PASSING before the fix but for the **wrong reason** — the length-gate (`len < 7`) returned `(None, 0, {})` before reaching the pattern-fail path. After extending to 7 bars, it now passes for the **right reason**: the detector reaches the Initiative LONG logic, evaluates bar 2 conditions (`b2.low < b1.low` AND `b2.close` far from POC), and correctly returns `direction is None` via the pattern-fail path.

---

## 10 · Phase A 15/15 COMPLETE

| # | Package | Status |
|---|---------|--------|
| 0 | Path B deletion | G3 PASS |
| 1 | Adaptive Stop | G3 PASS |
| 2a | OFA Entry Signal | G3 PASS |
| 2bc | OFA Config + Validators | G3 PASS |
| 3a (S1+S1.5+S2) | NeuE/NeuC + targets + NT gate | G3 PASS |
| 3b-1 | Trail infrastructure | G3 PASS |
| 3b-2 | TrailEngine + persistence | G3 PASS |
| 3b-3 | D-094 retrofit + Layer 4 | G3 PASS |
| 3c | Contract split | G3 PASS |
| 5a | Inv H&S + H&S Top | G3 PASS |
| 5b | Double Bottom + Top | G3 PASS |
| 5c | Bull Flag + Bear Flag | G3 PASS |
| 8 | Quality V2 + Auth Table | G3 PASS |
| **6** | **TradeManager extensible** | **G3 PASS** |
| **Consolidation** | **Stale-fixture repair** | **G3 PASS** |
| 4a/4b | Risk Rules | DEFERRED per D-095 |

---

## 11 · Next Steps

1. **G4 UAT** for Pkg 6 + Pkg 8 on `/cockpit/systems-snapshot` during RTH
2. **Phase A → Phase B transition decision** (Michael)
3. **SHADOW gate (P-S0)** — build-side now complete · awaiting G4 + soak

---

## 12 · Test Pollution Discipline

No `_skip_limiter.reset()` or registry cleanup needed. The lookback bars are pure data fixtures with no shared mutable state. Zero pollution risk.

---

Status: G3 PASS · Phase A Consolidation GREEN · Phase A 15/15 COMPLETE
