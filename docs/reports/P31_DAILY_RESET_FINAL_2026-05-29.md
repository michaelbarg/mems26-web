# P31 · Daily Reset / Archive / Demo Readiness — Final Report

**Date:** 2026-05-29
**Author:** Claude Code
**Commits:** 11 (8 tasks A-H + 3 infrastructure)
**Tests added:** 35+ new regression tests
**Regressions:** 0 new failures

---

## §1 · Commits

| Task | Commit | Description |
|------|--------|-------------|
| A | `8bedb74` | Consumer write gate — refuse UNKNOWN/PENDING UPSERTs |
| C | `f62777a` | Replace 13× date.today() + 2× SQLite date('now') with et_today() |
| G | `245fc21` | Elevate DayType failure logs to warning |
| F | `c79029d` | Hydrate day_type before overnight early-return |
| E | `6fcd3e2` | TPO session_id uses et_today() |
| B | `27c3145` | SessionBoundaryManager + state machine reset |
| D | `bbbd704` | Wire RiskValidator.daily_reset into rollover |
| H | `1375a95` | /current endpoints reject ROLLED_OVER rows |
| test | `de62547` | Fix test_invalid_firing_system (3→99) |
| M19 | `de4a831` | Migration 019 — archive tables + session_meta + is_synthetic |
| COMPLIANCE | `8c3d1c2` | Add DEVELOPING + ROLLED_OVER to lock_state enum |

## §2 · What each task does

**A — Consumer gate:** `_should_gate_write()` refuses UPSERT when `day_type ∈ {None, "", UNKNOWN}` AND `lock_state == PENDING`. Overnight Globex bars no longer overwrite yesterday's classification.

**C — et_today():** Single `et_today()` function in `backend/v9/common/trading_date.py`. Replaced all 13 `date.today()` calls and 2 SQLite `date('now')` with it. All date queries now use ET timezone.

**G — Logging:** Two `logger.debug` on DayType error paths in main.py → `logger.warning` with `exc_info=True`.

**F — Hydrate fix:** Moved day_type hydrate block BEFORE the overnight early-return in `five_min_system.hydrate()`. S2 now has `current_day_type` even when restarting during overnight.

**E — TPO session_id:** Already fixed by C (et_today already in use). Added tests confirming.

**B — SessionBoundaryManager:** New `backend/v9/services/session_boundary/manager.py`. Hybrid trigger (startup + first-bar fallback). Idempotent via `v9_session_meta.last_rollover_date`. Calls `day_type_machine.reset()` + `risk_validator.daily_reset()` at rollover.

**D — Risk reset:** Wired existing `RiskValidator.daily_reset()` into SBM rollover chain.

**H — ROLLED_OVER filter:** All `/current` endpoints (day_type V9, V1 compat, key_levels) add `AND status != 'ROLLED_OVER'` to their queries.

**M19 — Migration:** Archive tables (day_type, tpo_sessions, woodies_signals), `v9_session_meta`, `is_synthetic` columns on 4 tables. Fully idempotent.

**COMPLIANCE:** Added DEVELOPING + ROLLED_OVER to `lock_state` enum in `compliance_manifest.yaml`.

## §3 · Acknowledgements

- [x] `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (read, including §14-§17)
- [x] `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` (read)
- [x] `docs/reports/CC_CONSULT_P31_2026-05-29.md` (read)
- [x] `docs/reports/sot_health_audit/04_DAY_TYPE_API_NONE.md` (read)
- [x] `CLAUDE.md` (read)
- [x] This prompt (read)

Did NOT touch:
- [x] `bridge/v9_streams/` (P32 owns)
- [x] `sc_study/` (DLL locked)
- [x] `frontend/` (P31 backend-only)
- [x] `.cursor/rules/` (Cursor owns)

Confirms:
- [x] All commits per-task (11 commits = 11 logical units)
- [x] All tasks have regression tests
- [x] No `logger.debug` on failure paths in changed files
- [x] `570f10d` still on HEAD path

## §4 · Remaining (not in P31 scope)

| Item | Owner | Status |
|------|-------|--------|
| IS — `is_synthetic=0` filter on ~20 queries | P31-IS (deferred) | M19 columns added, filters TBD |
| SEED — v9_account_status DEMO mode | P31-SEED (deferred) | |
| P32 — tick_reversal TZ + sot_health cleanup | Separate prompt | |
| DLL frozen-tail | Sierra Remote Build | Mitigated by current_bar override |
