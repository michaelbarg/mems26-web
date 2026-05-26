# CC Prompt · Write Phase A Consolidation G3 PASS Report

**To:** Claude Code
**From:** Cursor (via Michael)
**Date:** 2026-05-25 15:15 IL
**Task:** Write G3 PASS report at `docs/reports/PHASE_A_CONSOLIDATION_G3_PASS_2026-05-25.md`

---

## Context

Phase A Consolidation Pkg (stale-fixture repair · 6 failing tests) is the **15th and FINAL Phase A package**. You implemented it in commit `799e00c` (3 test files · +30/-5 · zero production diff). Cursor verified G3 and confirmed all 7 acceptance criteria PASS.

**Phase A is now 15/15 COMPLETE.**

## Authority documents (read these · cite verbatim in the report)

- `docs/handoff/DESKTOP_PHASE_A_CONSOLIDATION_STALE_FIXTURES_HANDOFF.md` (the handoff CC implemented)
- `docs/plans/STATUS_BOARD.md` (amendment log 25/5 15:15 has the full verification data — use verbatim)
- `docs/reports/PKG6_G3_PASS_2026-05-25.md` (template · the most recent similar G3 PASS report)
- `backend/v9/systems/five_min/five_min_system.py` lines 30-32 (the MIN_BARS_REQUIRED=7 contract introduced by Pkg 2bc that caused the staleness)

## Commits in scope

```
799e00c · fix(test): Phase A Consolidation · stale-fixture repair · prepend 3 lookback bars to 6 stale fixtures (post-Pkg-2bc 7-bar contract) + add belly_ratio mock · tests-only · zero production diff
018526a · docs(status): Phase A 15/15 COMPLETE · Consolidation Pkg G3 verified by Cursor · CC report pending
```

## Report structure (use `PKG6_G3_PASS_2026-05-25.md` as template · keep concise · ~120-150 lines)

1. **Header:** package name (Phase A Consolidation · stale-fixture repair) · authority · branch · HEAD commit · Phase A status (**15/15 COMPLETE**)
2. **Summary (TL;DR):** 3-5 lines · G3 PASS · zero regressions · zero production diff · Phase A complete
3. **Root cause analysis:** Pkg 2bc (commit `dfdf91f`) introduced `MIN_BARS_REQUIRED=7` (4 pattern + 3 lookback) · 6 tests in `backend/v9/systems/five_min/tests/` still supplied 4 bars · detector short-circuited at line 407/484 with `(None, 0, {})` · pattern assertions failed. The fix: prepend 3 quiet doji bars to satisfy length + volume invariants.
4. **Commit `799e00c` (3 files · +30/-5):** breakdown per file · what was prepended + why (volume math: `v=300 < 0.6*1000` for Reactive · `v=200 < 0.6*600` for Initiative)
5. **CC discovery beyond handoff (approved):** `_get_belly_ratio_from_footprint` mock addition · explain it's defensive (gate determinism vs graceful-None-degradation) · note Cursor approved during G3
6. **Acceptance criteria verification (7/7):** verbatim from STATUS_BOARD amendment 25/5 15:15 · one row per criterion · paste evidence (pytest counts · git diff · ReadLints)
7. **Regression sweep:** baseline `30 failed / 1562 passed` at HEAD `e7094d3` (Pkg 6 G3 baseline) · post-Consolidation `30 failed / 1562 passed` (identical) · zero new regressions
8. **The 6 fixed tests (verbatim list):**
   - `test_e2e_t1.py::TestE2EScenarios::test_reactive_long_full_pipeline`
   - `test_e2e_t1.py::TestE2EScenarios::test_reactive_short_mirror`
   - `test_e2e_t1.py::TestE2EScenarios::test_initiative_long_fires`
   - `test_e2e_t1.py::TestE2EScenarios::test_initiative_long_poc_return_alt`
   - `test_poc_return_alt.py::TestPocReturnAlt::test_initiative_long_poc_return`
   - `test_process_bar_emission.py::test_process_bar_emits_setup_on_pattern_match`
9. **`test_initiative_long_no_hl_no_poc_fails` integrity note:** this test was PASSING before fix but for the WRONG reason (length-gate · not pattern-fail). After fix it passes for the RIGHT reason (pattern-fail-path · `direction is None` due to `b3.l < b1.l`). Confirm via §3 of handoff §3.
10. **Phase A 15/15 ✅ COMPLETE table:** all 13 GREEN + Pkg 6 GREEN + Consolidation GREEN · 4a+4b deferred
11. **Next steps:**
    - G4 UAT for Pkg 6 + Pkg 8 on `/cockpit/systems-snapshot` during RTH
    - Phase A → Phase B transition decision (Michael)
    - SHADOW gate (P-S0) build-side now complete · awaiting G4 + soak
12. **Test pollution discipline confirmation:** no `_skip_limiter.reset()` needed here · the lookback bars are pure data fixtures with no shared state · zero pollution risk

## Constraints

- **Do NOT modify any code.** Report-only.
- Cite commit SHAs verbatim (`799e00c` · `018526a`).
- Cite line numbers verbatim (`five_min_system.py:30-32` for MIN_BARS_REQUIRED · `:407` for reactive guard · `:484` for initiative guard · `:433-437` for lookback_quiet · `:511-515` for initiative lookback).
- Use the same Hebrew/English mix style as `PKG6_G3_PASS_2026-05-25.md`.
- **No "TODO:" markers** in the report.
- **Final line:** `Status: ✅ G3 PASS · Phase A Consolidation GREEN · Phase A 15/15 COMPLETE`.

## Commit

After writing the report:
```
git add docs/reports/PHASE_A_CONSOLIDATION_G3_PASS_2026-05-25.md
git commit -m "docs(test): Phase A Consolidation G3 PASS report · stale-fixture repair · 18 tests + zero regressions + zero production diff · Phase A 15/15 COMPLETE"
```

---

*End of CC prompt · ready for paste into CC*
