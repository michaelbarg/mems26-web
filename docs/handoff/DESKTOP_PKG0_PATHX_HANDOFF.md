# Handoff to Claude Desktop · Pkg 0 (Path X · expanded scope)

**Date:** 2026-05-23 18:20 IL
**From:** Michael (via Cursor agent)
**To:** Claude Desktop
**Task:** Write the full MEGA prompt for Claude Code (CC) to execute Pkg 0 · Path B deletion + EventDispatcher rewire (Path X).
**Authority:** D-090 (Path A canonical) + verify-first audit 23/5 18:15 (this doc §1)

---

## 1 · Context · why Pkg 0 grew from 1-2h to 1 day

Cursor's verify-first investigation found **two wired paths** for `system_id=2`:

### Path A (canonical · keep)
- File: `backend/v9/systems/five_min/five_min_system.py`
- Class: `FiveMinSystem(BaseV9TradingSystem)` · `system_id=2` · `name="five_min"`
- Wired in: `backend/v9/main.py` via `bar_router.subscribe()`
- Status: **firing** real signals · D-090 keeper

### Path B (stale · delete)
- File: `backend/v9/systems/wrappers.py::Chart5MinSystem`
- Detector: `backend/v9/systems/chart_5min/` (entire directory · ~2000 LOC · 19 patterns)
- Wired in: `backend/v9/app.py::init_event_dispatcher` via `dispatcher.register_system(chart_5min_system)`
- subscribed_streams: `["cumulative_delta"]`
- Status: **CPU consumed, never fires** · D-090 target for deletion

### Side-finding · SYSTEM_NAMES drift (latent bug)
- `backend/v9/services/snapshot_service/snapshot.py:23` → `2: "chart_5min"`
- `backend/v9/api/v9/shadow_routes.py:79` → `"five_min": 2`
- **Two production files give different names for system 2.** Snapshot writes Redis under `mems26:state:chart_5min` but shadow_routes reads/expects `"five_min"`. Pkg 0 fixes this drift.

### Cross-system impact verified (read-only audit)
- 5 other systems (S1/S3/S4/S5/S6) subscribe to **independent streams** — none depend on Chart5MinSystem
- "cumulative_delta" stream **still has S1 (DayType)** as subscriber → not orphaned
- `rg "chart_5min" frontend/v9/` → 0 hits → zero frontend impact
- `len(dispatcher._systems)` will drop 6→5 · acceptable (Michael approved Path X)

---

## 2 · The 10 sub-steps Pkg 0 must execute

| # | Step | File(s) | Verify |
|---|------|---------|--------|
| 1 | Remove `Chart5MinSystem` class | `backend/v9/systems/wrappers.py` (class block) | grep returns 0 hits |
| 2 | Remove `Chart5MinSystem` import + instantiation + `register_system()` call | `backend/v9/app.py::init_event_dispatcher` | dispatcher registers 5 systems |
| 3 | Update `dispatcher.py` docstring example | `backend/v9/services/event_dispatcher/dispatcher.py:24` | cosmetic — example uses `five_min_system` instead |
| 4 | Fix SYSTEM_NAMES drift: `2: "chart_5min"` → `2: "five_min"` | `backend/v9/services/snapshot_service/snapshot.py:23` + `:10` comment | aligns with `shadow_routes.py` |
| 5 | Redis key audit + migration plan | runtime script | enum keys under `mems26:state:chart_5min`, rename to `mems26:state:five_min` OR drop (Michael decides at G3) |
| 6 | Update `five_min/compliance_manifest.yaml` (remove chart_5min refs) | `backend/v9/systems/five_min/compliance_manifest.yaml` | grep returns 0 hits |
| 7 | Delete entire dir | `backend/v9/systems/chart_5min/` (~2000 LOC · 19 patterns) | dir gone |
| 8 | Delete/refactor 7 test files referencing chart_5min | see list below | pytest green |
| 9 | Verify `pytest tests/v9/ -q` green | full suite | exit 0 |
| 10 | Verify `rg "chart_5min" backend/ tests/` returns 0 hits (acceptable: history docs only) | repo-wide | grep clean |

### Test files for step 8

```
tests/v9/systems/test_chart_5min_patterns/conftest.py
tests/v9/systems/test_chart_5min_patterns/test_group_a.py
tests/v9/systems/test_chart_5min_patterns/test_group_b.py
tests/v9/systems/test_chart_5min_patterns/test_group_c.py
tests/v9/systems/test_chart_5min_patterns/test_helpers.py
tests/v9/systems/test_chart_5min_patterns/test_patterns_direct.py
tests/v9/systems/test_chart_5min.py
tests/v9/compliance/test_chart_5min_compliance.py
tests/v9/compliance/v1_generated/test_system2_v1.py
tests/v9/compliance/v2_generated/test_snapshot_compliance.py  ← check first: does it test "chart_5min" name? If yes → update to "five_min". If no → keep.
tests/v9/services/test_event_dispatcher.py  ← check first: does it instantiate Chart5MinSystem? If yes → replace with FiveMinSystem mock. If no → keep.
```

**For each of the last 2 files (test_snapshot_compliance · test_event_dispatcher) — CC must READ first and report which path applies before deleting.**

---

## 3 · Files CC must read before writing

Attach these inline to the mega prompt (Desktop, you must paste their full contents):

1. `backend/v9/systems/wrappers.py` (entire · ~430 lines · so CC sees Chart5MinSystem class location)
2. `backend/v9/app.py::init_event_dispatcher` (lines 270-310 approximately · the wiring section)
3. `backend/v9/services/event_dispatcher/dispatcher.py` (entire · ~140 lines · CC must understand routing logic)
4. `backend/v9/services/snapshot_service/snapshot.py` (entire · for SYSTEM_NAMES dict)
5. `backend/v9/api/v9/shadow_routes.py` (lines 70-100 · for comparison · already uses `"five_min"`)
6. `backend/v9/systems/five_min/compliance_manifest.yaml` (entire)
7. `backend/v9/main.py::main` (lines that wire `FiveMinSystem` via bar_router — so CC knows Path A is preserved)
8. `tests/v9/services/test_event_dispatcher.py` (entire · CC must check if Chart5MinSystem is used)
9. `tests/v9/compliance/v2_generated/test_snapshot_compliance.py` (entire · CC must check if `"chart_5min"` literal is asserted)

---

## 4 · Acceptance criteria (G4 UAT)

CC must self-verify ALL of these:

- ✅ `len(dispatcher._systems) == 5` after `init_event_dispatcher()` runs (assert in unit test)
- ✅ Bar arrival on `cumulative_delta` routes ONLY to `DayTypeSystem` (not to Chart5MinSystem — verified via dispatcher routing table inspection)
- ✅ `FiveMinSystem` still wired via BarRouter (asserted by reading `main.py` post-edit · or via integration smoke)
- ✅ `pytest tests/v9/ -q` exit code = 0
- ✅ `rg "chart_5min" backend/v9/` returns 0 hits (allowed exceptions: `docs/decisions/D-090*.md`, `docs/reports/*.md`, decision history)
- ✅ `rg "Chart5MinSystem" backend/ tests/` returns 0 hits
- ✅ `rg "Chart5MinDetector" backend/ tests/` returns 0 hits
- ✅ SYSTEM_NAMES drift fixed: `snapshot.py` and `shadow_routes.py` both use `"five_min"` for system_id=2
- ✅ ReadLints clean (no new linter errors)
- ✅ Backend boots without ImportError (CC must run `python -c "from backend.v9.app import create_app; create_app()"`)

---

## 5 · Constraints (must not violate)

- **No "while I'm here" refactors** outside Path B removal + SYSTEM_NAMES sync
- **Path A untouched** — `backend/v9/systems/five_min/` is forbidden territory (read-only · only `compliance_manifest.yaml` if it references chart_5min)
- **Backend must boot** post-edits — CC verifies via `python -c "from backend.v9.app import create_app; create_app()"`
- **No new dependencies**
- **Redis migration step (5):** CC must NOT execute the actual `KEYS` / `DEL` Redis command — only write the migration script + report Redis state. Michael decides at G3 whether to run rename or drop.
- **No silent excepts** — anywhere CC adds error handling, must `logger.warning(...)` rate-limited per the pre-LIVE protocol
- **Don't commit `*.pyc` / `__pycache__/`** files in the commit

---

## 6 · Stop signal triggers

CC must STOP and report (NOT guess) if:

- Any file outside SCOPE has `chart_5min` references that aren't safe to delete (e.g. a system that imports a pattern by name)
- `test_event_dispatcher.py` or `test_snapshot_compliance.py` have non-trivial setup that's hard to refactor — CC must report findings, not improvise
- `main.py` wiring of `FiveMinSystem` requires changes for the dispatcher reduction (it shouldn't — they're independent — but if CC finds coupling, STOP)
- Backend boot fails post-edit with any error trace — STOP, capture trace, report

Output format on STOP: `"STOP — <reason> · need Michael decision on <specific question>"`

---

## 7 · Deliverable format CC must produce

1. **Files deleted** (full paths · D)
2. **Files modified** (full paths · M · with diff lines)
3. **Commit message:** `chore(s2): delete Path B chart_5min + Path X dispatcher rewire per D-090`
4. **rg outputs** (paste verbatim · `chart_5min`, `Chart5MinSystem`, `Chart5MinDetector`)
5. **pytest output** tail 30 lines
6. **Boot smoke** output: `python -c "from backend.v9.app import create_app; app = create_app(); print('OK · systems:', len(...))"`
7. **Redis migration script** (separate file `scripts/pkg0_redis_migrate.py`) · NOT executed · just delivered for Michael
8. **Self-report:**
   - Any TODOs left? (must be empty)
   - Any spec ambiguity encountered? (list)
   - Any forbidden constraint accidentally violated? (own up)

---

## 8 · Desktop's deliverable

Desktop, please produce a single mega prompt for CC following `docs/templates/MEGA_PROMPT_TEMPLATE.md` structure (7 fields + Stop signal).

Use this handoff as the spec authority. Inline the file contents listed in §3. The mega prompt is what Michael will paste into Claude Code.

**Length expectation:** ~600-900 lines (includes inlined files). Quality > brevity.

---

*End of handoff · Cursor agent · 2026-05-23 18:20 IL*
