# CC Prompt · Write Pkg 6 G3 PASS Report

**To:** Claude Code
**From:** Cursor (via Michael)
**Date:** 2026-05-25 14:35 IL
**Task:** Write G3 PASS report for Pkg 6 (TradeManager extensible) at `docs/reports/PKG6_G3_PASS_2026-05-25.md`

---

## Context

Pkg 6 (TradeManager extensible · RiskRule registry) is the **LAST Phase A package**. You implemented it in commit `77dd4cf` (39 new tests + 8 new prod files + 1 modified file). Cursor then fixed a name-collision bug in the handoff (commit `ed76e78` — rename `test_trade_manager/` → `test_trade_manager_rules/`) and verified G3.

Phase A is now **14/15 done** (Pkg 4a/4b deferred per D-095).

## Authority documents (read these · cite verbatim in the report)

- `docs/spec_authority/S2_TRADEMGR_HOOKS_V1.md` (🔒 LOCKED 25/5 13:57 · Q9.1-Q9.4 decisions)
- `docs/handoff/DESKTOP_PKG6_TRADEMGR_HANDOFF.md` (the handoff CC implemented)
- `docs/plans/STATUS_BOARD.md` (amendment log 25/5 14:35 has full G3 verification data — use this verbatim for the report body)
- `docs/decisions/D-095_DEFER_4A_4B_SCOPE_ABSORBED.md` (defer 4a/4b · scope absorbed by Pkg 6)
- `docs/reports/PKG8_G3_PASS_2026-05-25.md` (template · most recent similar G3 PASS report)

## Commits in scope

```
77dd4cf · feat(s2): Pkg 6 · TradeManager extensible · RiskRule registry + 5 wrappers · D-095 zero functional change · Phase A mechanical · DEMO+ parametric calibration
ed76e78 · fix(test): rename Pkg 6 test dir to avoid name collision · test_trade_manager → test_trade_manager_rules
de1cf4b · docs(status): Pkg 6 G3 verified by Cursor · 39/39 tests PASS · zero regressions · CC report pending
```

## Report structure (use PKG8_G3_PASS_2026-05-25.md as template)

1. **Header:** package · authority · branch · HEAD commits · Phase A status (14/15)
2. **Summary (TL;DR):** 3-5 lines · G3 PASS · zero regressions · zero-diff layer4
3. **Files changed (commit-by-commit breakdown):**
   - `77dd4cf` · 13 files (+887/-54): list all 8 new prod files + 5 new test files + 1 modified
   - `ed76e78` · 5 files (rename only · 0 diff): document the name collision root cause
4. **Acceptance criteria verification (10/10):** verbatim from STATUS_BOARD amendment 25/5 14:35 · one row per criterion · paste evidence (rg / git diff / pytest counts)
5. **Q9.1-Q9.4 lock verification:** each Q with one-line evidence (which test confirms it)
6. **D-095 zero-functional-change verification:** `git diff 12edadc..77dd4cf -- backend/v9/services/layer4/` = 0 lines · the 5 layer4 services are byte-identical
7. **Regression sweep:** baseline `30 failed / 1523 passed` at 12edadc · post-Pkg6+rename `30 failed / 1562 passed` · delta = +39 (exactly the 39 new Pkg 6 tests)
8. **The 2 pre-existing failures (TestDBPersistence):** prove they are pre-Pkg6 (manager.py untouched · no transitive Pkg 6 import in fixture · same failures at 12edadc)
9. **CC design choice highlight (approved by Cursor):** PRE_TIGHTEN/POST_TIGHTEN as module-level constants instead of string literals — refactor-safer
10. **Risk #8 cleanup discipline:** future-rule stub tests use try/finally `unregister_rule` cleanup · no test pollution
11. **Phase A completion outlook:** 14/15 done · 1 remaining = "Phase A Consolidation Pkg" (6 stale-fixture failures deferred from B2 25/5 13:35) · 4a+4b stay deferred per D-095
12. **Constitution V3 amendment status:** §Layer 4 pointer to `S2_TRADEMGR_HOOKS_V1.md` added 25/5 13:58 (1 line · already in MEMS26_CONSTITUTION_V3_FINAL.txt)
13. **Next steps:** (a) G4 UAT on /cockpit/systems-snapshot during RTH · (b) Phase A → Phase B transition decision · (c) Constitution V3 amendment block ready · (d) Phase A Consolidation Pkg post-Pkg6

## Constraints

- **Do NOT modify any code.** Report-only.
- Cite commit SHAs verbatim (`77dd4cf` · `ed76e78` · `de1cf4b`).
- Cite line numbers verbatim where relevant (`trail_engine.py:27-28` · `:594` · `:620`).
- Use the same Hebrew/English mix style as `PKG8_G3_PASS_2026-05-25.md`.
- **No "TODO:" markers** in the report.
- **Final line:** `Status: ✅ G3 PASS · Pkg 6 GREEN · Phase A 14/15`.

## Commit

After writing the report:
```
git add docs/reports/PKG6_G3_PASS_2026-05-25.md
git commit -m "docs(s2): Pkg 6 G3 PASS report · TradeManager extensible · 39 tests + zero regressions + D-095 verified"
```

---

*End of CC prompt · ready for paste into CC*
