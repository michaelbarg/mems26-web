# Pytest Triage — 2026-05-30

**Run:** `python3 -m pytest tests/v9/ -q --ignore=tests/v9/api` (api/ blocked by conftest pytest_plugins error)
**Result:** 38 failed, 1994 passed, 1 skipped

## Triage Table

| # | File | Count | Type | Blocks Trading? | Root Cause |
|---|------|-------|------|-----------------|------------|
| 1 | `test_snapshot_compliance.py` | 5 | FIXTURE-DRIFT | Yes | Snapshot schema V1.1 not wired in TradeManager |
| 2 | `test_api.py::test_trade_lifecycle` | 1 | REGRESSION | **Yes — fixed** | `V9Trade.is_synthetic` missing from ORM model; added in this session |
| 3 | `test_trade_time_dual_tz.py` | 1 | LEGACY | No | Frontend file path check, not trading path |
| 4 | `test_snapshot_service.py` | 3 | FIXTURE-DRIFT | Yes | Same as #1 — snapshot schema mismatch |
| 5 | `test_tpo_history_snapshotter.py` | 7 | REGRESSION | Yes | `slot_start_ts_str()` TZ conversion returns UTC not ET |
| 6 | `test_trade_manager.py` | 2 | REGRESSION | **Yes — fixed** | Same as #2 — `is_synthetic` attr missing |
| 7 | `test_trail_engine.py` | 2 | FIXTURE-DRIFT | No | Mock signature drift |
| 8 | `test_bar_level_detector_entry_guard.py` | 3 | FIXTURE-DRIFT | Yes | Entry guard test fixtures don't match current BarLevelDetector API |
| 9 | `test_day_type.py` | 4 | REGRESSION | Yes | State machine stages A4/B1: vote_history not populated, IB lock not firing |
| 10 | `test_day_type_ib_live.py` | 5 | REGRESSION | Yes | `ib_locked` stays False after A4 (session_min≥60 not triggering lock) |
| 11 | `test_five_min_day_type_wiring.py` | 2 | FIXTURE-DRIFT | No | NT skip counter mock setup doesn't match current process_bar flow |
| 12 | `test_tpo_session_id_et_today.py` | 2 | REGRESSION | No | `et_today()` mock not patched in correct module |

## Summary

- **Critical regressions (groups 2, 5, 6, 9, 10):** 14 failures on trading paths — **is_synthetic fix applied this session**
- **Fixture drift (groups 1, 4, 7, 8, 11):** 15 failures from spec evolution outpacing test updates
- **Legacy/non-trading (3, 12):** 3 failures on non-critical paths
- **API collection error:** `tests/v9/api/conftest.py` defines `pytest_plugins` in non-top-level conftest — blocks entire api/ test dir

## Fix Status

- Groups 2, 6: **Fixed** — added `is_synthetic` column to V9Trade ORM model
- Groups 9, 10: Need investigation — state machine stage progression may have regressed
- Group 5: TPO slot TZ — separate fix needed
- Remaining: fixture updates needed but not on critical pre-LIVE path
