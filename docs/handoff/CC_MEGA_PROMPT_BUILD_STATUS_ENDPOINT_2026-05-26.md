# MEGA PROMPT · Package BUILD-STATUS-1 · Pattern Status Aggregator Endpoint

**Owner:** Cursor (authored 2026-05-26 07:30 IL)
**Consumer:** Claude Code (CC)
**Reviewer:** Cursor verifies in G3 after delivery
**Block:** Frontend "Build Status" tab (T-08) is in parallel · CC has 2–3 h target

---

## Spec authority (verbatim · locked)

- **Design document (authoritative for this package):** `docs/reports/BUILD_STATUS_ENDPOINT_DESIGN.md` v1 — Cursor authored · Michael-approved · §2 contract · §3 per-system shape · §4 component lists · §5 implementation outline · §6 tests · §10 sequencing
- **`docs/spec_authority/S2_AUTH_TABLE_V1.md`** (🔒 LOCKED 25/5 12:22) — §2 lists the 10 PatternName values · §4 lists the 70 (pattern × day_type) cells · §3 lists the 7 day_type enum values
- **`docs/decisions/D-091_S2_LIVE_SCOPE.md`** — §"Coverage Matrix" lines 33-50 (the live coverage gates for each pattern)
- **`docs/decisions/D-092_S4_WOODIES_UPDATE.md`** (🔒 LOCKED) — §2 lists the 9 Woodies patterns · §3 references the 21-stage decision tree
- **`docs/spec_authority/MEMS26_WOODIES_DECISION_TREE_V1.md`** — A1..A7 and B1..B14 stage definitions
- **`docs/spec_authority/S2_EXIT_DEFINITION_V6.md`** (🔒 LOCKED) — §"שלושת סוגי יציאה" Type A/B/C exit triggers

**You MUST quote these verbatim in code comments where they justify a
behavioral choice. No paraphrasing. No "based on spec" — cite section.**

---

## Existing code (read-only · do NOT modify outside SCOPE)

### `backend/v9/api/v9/day_type_v9_routes.py` (162 lines · attached below for reference)

```python
"""API: /api/v9/day_type/v9/* — V9 Day Type endpoints (3a-S4 REVISED C3)."""
# Router prefix: /api/v9/day_type/v9
# Key fn: get_current() reads v9_day_type_history for today
# Returns: {classified, developing, session_date, data: {day_type, probability,
#          directional_certainty, trading_confidence, ib_h/l/width, opening_type,
#          last_updated_at, reasoning_notes, active_zohar_rules}}
# DB_PATH: /Users/michael/Downloads/mems26_web_git/data/mems26_local.db
# Helper: _row_to_v9_dict(r) — see lines 116-161 for V9 ↔ V1 field mapping
```

Read the full file before writing the day-type inspector. Do NOT call this
endpoint over HTTP from your aggregator — import the helper or duplicate
the DB read with the same SQL.

### `backend/v9/systems/woodies/woodies_system.py` (key methods)

```python
class WoodiesSystem(BaseV9TradingSystem):
    # Line 509:
    def get_current(self) -> dict:
        return dict(self.current_state)

    # current_state keys (from woodies routes consumption):
    # - active_patterns: list[dict] · each has {id, direction, entry_price,
    #   stop, targets, confidence, ...}
    # - trend_state: "GREEN" | "RED" | "GRAY"
    # - cci_14: float | None
    # - tcci_value: float | None
    # - classification: str (e.g., "NO_SETUP" | pattern-specific)
    # - ready_to_route: bool
    # - direction: "LONG" | "SHORT" | None
    # - entry_classification_spec: str | None
    # - decision_tree: dict (A1..A7, B1..B14) · each stage has {passed: bool, reason: str}
```

Access via `request.app.state.woodies_system`. Handle `None` gracefully
(system uninitialized — return `running=false, hydrated=false`).

### `backend/v9/systems/five_min/five_min_system.py` (key methods · lines 944-960)

```python
def get_state(self) -> dict:
    return {
        "running": self._hydrated,
        "hydrated": self._hydrated,
        "mode": self.mode,
        "buffer_size": self.buffer_size,
        "opening_type": self.opening_type,
        "last_pattern": self.last_pattern,
        "last_confluence": self.last_confluence,
        "last_classification": self.last_classification,
        "last_reasoning_notes": self.current_state.get("last_reasoning_notes"),
    }

def get_current(self) -> dict:
    return self.get_state()
```

This is **less rich than Woodies**. You will need to inspect:
- `self._bar_buffer` for CCI history + buffer size
- `self.current_state` for any pattern-specific keys (e.g., `last_pattern`)
- DB `bars_5min` for recency

Access via `request.app.state.five_min_system`.

### `docs/reports/BUILD_STATUS_ENDPOINT_DESIGN.md` — READ ALL 11 SECTIONS

This is your primary spec. The design doc is the authority. The auth-table
data and pattern lists in §4 must match exactly.

---

## SCOPE — exactly these files

**WRITE NEW:**
- `backend/v9/api/v9/build_status_routes.py` (router)
- `backend/v9/systems/build_status/__init__.py`
- `backend/v9/systems/build_status/aggregator.py` (`BuildStatusAggregator`)
- `backend/v9/systems/build_status/s2_inspector.py`
- `backend/v9/systems/build_status/woodies_inspector.py`
- `backend/v9/systems/build_status/day_type_inspector.py`
- `backend/v9/systems/build_status/auth_table_lookup.py` (Python const dict — NOT JSON file read)
- `backend/v9/systems/build_status/types.py` (Pydantic schemas)
- `tests/v9/build_status/__init__.py`
- `tests/v9/build_status/test_endpoint.py`
- `tests/v9/build_status/test_s2_inspector.py`
- `tests/v9/build_status/test_woodies_inspector.py`
- `tests/v9/build_status/test_day_type_inspector.py`
- `tests/v9/build_status/test_auth_table_lookup.py`
- `tests/v9/build_status/conftest.py` (fixtures · uses real `FiveMinSystem` and `WoodiesSystem` instances per §5 live-repro lesson)

**MODIFY EXISTING (exact lines · do not exceed):**
- `backend/main.py` — register the new router (1 import line + 1
  `app.include_router(...)` line · grep to find where existing routers
  register; add yours at the bottom of that block)

**FORBIDDEN — do NOT touch:**
- `bridge/` (any file)
- `sc_study/` (DLL)
- `frontend/` (Cursor owns)
- `backend/v9/systems/five_min/` except read-only imports
- `backend/v9/systems/woodies/` except read-only imports
- `backend/v9/systems/day_type/` except read-only imports
- `backend/v9/services/trade_manager/` (reserved)
- `backend/v9/services/trail_engine.py`
- `docs/spec_authority/*.md` (locked)
- `docs/decisions/*.md` (locked)
- `docs/spec_authority/MEMS26_CONSTITUTION_V3_FINAL.txt` — Michael decision
  pending (option ג open · do not revert/commit)
- LaunchAgent (`~/Library/LaunchAgents/com.mems26.bridge.plist`)
- `.gitignore`, `.env`, any credentials file
- Existing tests outside `tests/v9/build_status/`

---

## Golden tests (must pass · minimum N=16)

All 16 from `BUILD_STATUS_ENDPOINT_DESIGN.md` §6, paraphrased here for clarity:

1. `test_build_status_endpoint_returns_200_when_all_systems_up` — full happy path · 3 systems · all responding
2. `test_build_status_endpoint_returns_200_when_woodies_uninitialized` — `app.state.woodies_system = None` → response includes Woodies block with `running=false, hydrated=false`, NOT a 500
3. `test_build_status_endpoint_p95_latency_under_300ms` — 50 runs · p95 < 300 ms · use `pytest-benchmark` only if already in repo · else `time.perf_counter()` loop
4. `test_s2_inspector_returns_10_patterns` — exactly these IDs in this order: `REACTIVE_LONG, REACTIVE_SHORT, INITIATIVE_LONG, INITIATIVE_SHORT, INVERSE_HNS_LONG, HNS_TOP_SHORT, DOUBLE_BOTTOM_EE_LONG, DOUBLE_TOP_AA_SHORT, BULL_FLAG_LONG, BEAR_FLAG_SHORT` — copy verbatim from `S2_AUTH_TABLE_V1.md` §2
5. `test_woodies_inspector_returns_9_patterns` — exactly: `ZLR, TLB, TT, GB100, Vegas, Ghost, FaMir, HTLB, HFE` — copy verbatim from `D-092` §2
6. `test_day_type_inspector_returns_single_entity` — one entity with 7 components (per design §4.3)
7. `test_pattern_status_fired_when_setup_emitter_emitted_today` — uses DB fixture inserting one row into a relevant fires table (find the actual table by reading `setup_emitter.py` · do NOT guess) · expect `status="fired"`, `fired_today=true`, `last_fire_ts` ≠ null
8. `test_pattern_status_armed_when_all_components_present_no_fire_yet` — fixture with everything present but no fire row → `status="armed"`
9. `test_pattern_status_blocked_when_auth_table_cell_is_skip` — set day_type=Nontrend in fixture → all S2 patterns must return `status="blocked"` (or `vetoed` for NT global gate · pick consistent semantics and assert)
10. `test_pattern_status_vetoed_when_nt_day_type` — NT global short-circuit · explicit `vetoed` semantic
11. `test_pattern_status_unknown_when_day_type_developing` — `ib_width_class="DEVELOPING"` → day-type entity `status="armed"` (not blocked · still in progress)
12. `test_response_shape_matches_pydantic_schema` — Pydantic round-trip: parse response, serialize, compare equal
13. `test_endpoint_includes_data_freshness_block` — per system: `data_freshness.last_bar_ts`, `lag_seconds`, `fresh`, `threshold_seconds`
14. `test_endpoint_handles_inspector_exception_returns_partial_result_with_error` — monkeypatch one inspector to raise · response must be 200, that system marked `status="unknown"`, top-level `errors` array has one entry · **logger.warning was called** (assert)
15. `test_endpoint_no_self_http_calls` — assert `httpx`, `requests`, `aiohttp` are NOT imported anywhere in `backend/v9/systems/build_status/` and `backend/v9/api/v9/build_status_routes.py` (use `pathlib` + grep · runtime assertion)
16. `test_build_status_live_repro_with_real_five_min_system_instance` — **§5 anti-regression test** · construct a real `FiveMinSystem()` instance, hydrate it with a fixture of 14+ 5-min bars, call the aggregator, assert at least one S2 pattern's `components[*].present` field reflects buffer state (i.e., `five_min_bar_recency.present == true`)

If you write a test that uses a `FakeFiveMinSystem` or a `MagicMock` for
`FiveMinSystem`, you have **violated §5 lesson #1**. Use the real class.
Use fakes only for external dependencies (DB connection if absolutely
necessary), never for the system under test or its peer state holders.

---

## Allowed imports (whitelist)

```python
# Standard library
import logging
import sqlite3
import time
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional, Literal, Tuple, Dict, List, Any

# Third-party (already in repo · check requirements.txt before adding)
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

# Internal — read-only access to existing systems
from backend.v9.systems.five_min.five_min_system import FiveMinSystem  # for type hint
from backend.v9.systems.woodies.woodies_system import WoodiesSystem    # for type hint
# DO NOT import from setup_emitter, trade_manager, trail_engine, contract_split

# Auth table — Python const dict, NOT external file read
# (Define in backend/v9/systems/build_status/auth_table_lookup.py as a literal dict)
```

**Forbidden imports:**
- `httpx`, `requests`, `aiohttp` (no self-HTTP calls)
- `subprocess`, `os.system` (no shell-out)
- `backend.v9.systems.five_min.setup_emitter`
- `backend.v9.systems.five_min.contract_split`
- `backend.v9.services.trade_manager.*`
- `backend.v9.services.trail_engine`
- Any new pip package
- Frontend or bridge modules

If you need an API outside this list, **STOP** and report.

---

## Acceptance criteria

- `pytest tests/v9/build_status/ -q` → all 16+ green
- `pytest tests/v9/ -q` → no new failures in unrelated suites (regression-clean)
- `ReadLints backend/v9/api/v9/build_status_routes.py backend/v9/systems/build_status/ tests/v9/build_status/` → 0 new linter errors
- `curl -fsS http://localhost:8000/api/v9/build/pattern-status | python3 -m json.tool` → valid JSON · contains 3 systems · S2 has 10 patterns · Woodies has 9 patterns · Day Type has 1 entity
- Latency on live endpoint: p95 < 300 ms (measure with 20 sequential `curl` calls)
- `rg "logger.debug" backend/v9/api/v9/build_status_routes.py backend/v9/systems/build_status/` → only ALLOWED in success/info paths · 0 hits on `except` branches
- `rg "import httpx|import requests|import aiohttp" backend/v9/systems/build_status/ backend/v9/api/v9/build_status_routes.py` → 0 hits

---

## Constraints (must not violate)

a) **§5 lesson #1 · No mocked system under test.** Tests 14, 16 must use
   real `FiveMinSystem` and `WoodiesSystem` instances. `FakeFiveMinSystem`
   class is forbidden in this package's tests.

b) **§5 lesson #2 · Payload field name check.** When reading from
   `WoodiesSystem.get_current()` and `FiveMinSystem.get_state()`, every
   field access must match the actual return shape in the linked source
   files above. No `.data` vs `.payload` typos. Add an explicit unit test
   asserting that your inspector dict keys match the real return shape
   keys.

c) **No silent excepts.** Every `try/except` in the aggregator and
   inspectors must include `logger.warning(...)` (rate-limited via a
   simple module-level dict if needed · 1 log per (system, key) per 60s).
   `except Exception: pass` is forbidden. `logger.debug` on error paths
   is forbidden.

d) **No `return None` on failure paths without a prior `logger.warning`.**
   Replace with `return {"status": "unknown", "error": str(e)}` (typed
   per Pydantic schema in §3.2 of design doc).

e) **No new dependencies.** Do not add to `requirements.txt`. Use stdlib
   + existing deps only.

f) **No "while I'm here" refactors.** Strict scope. If you spot a bug in
   `WoodiesSystem.get_current()`, file it as a TODO in your deliverable
   report's "spec ambiguity" section · do NOT fix it in this PR.

g) **No DB writes.** Aggregator is read-only. Inspectors may open
   sqlite3 connections in read-only mode (`?mode=ro&immutable=1` URI) but
   must close them and must not write.

h) **No async I/O on the hot path.** Endpoint handler is `async def`,
   but every call to a system object must be sync (those methods are
   sync · do not wrap with `asyncio.to_thread` unless they actually
   block on I/O, which they don't · they're in-memory dict access).

i) **Pydantic schemas are the contract.** Define `SystemStatus`,
   `PatternStatus`, `Component` in `types.py`. Endpoint returns
   `.model_dump()`. Test 12 asserts the round-trip.

j) **Component spec strings are verbatim from spec sources.** When you
   write `"spec": "S2_AUTH_TABLE_V1[BULL_FLAG_LONG][NeuC] ≠ SKIP"`, that
   string is rendered to the frontend. Use the exact citation from the
   spec source. Do not invent terminology.

---

## Deliverable format

After completion, output:

1. **List of files** (full paths · A/M/D markers):
   - A `backend/v9/api/v9/build_status_routes.py`
   - A `backend/v9/systems/build_status/__init__.py`
   - ... etc
   - M `backend/main.py` (with diff lines · 2 lines added)

2. **Commit message** (conventional · single line):
   `feat(build-status): add /api/v9/build/pattern-status aggregator endpoint`

3. **Self-report:**
   - Any TODOs left in code? (must be empty)
   - Any spec ambiguity encountered? (list explicitly · do NOT silently
     resolve)
   - Any forbidden import accidentally used? (own up)
   - Any test that uses a fake `FiveMinSystem` or `WoodiesSystem`?
     (must be NO · §5 lesson)
   - Endpoint p95 latency on local curl loop (paste numbers)

4. **`ReadLints` output** (paste verbatim)

5. **`pytest tests/v9/build_status/ -q` output** (paste verbatim · tail 50 lines)

6. **`pytest tests/v9/ -q` output** (paste verbatim · tail 30 lines · prove no regression)

7. **Live curl output** (paste verbatim):
   ```bash
   curl -fsS -m 5 http://localhost:8000/api/v9/build/pattern-status | python3 -m json.tool | head -100
   ```

---

## Stop signal

IF any of these conditions met, STOP and report — do NOT guess, do NOT
add `TODO: ask Michael`:

- The pattern list in `S2_AUTH_TABLE_V1.md` §2 does not match exactly
  10 names · or D-092 §2 does not match exactly 9 names
- `app.state.five_min_system` or `app.state.woodies_system` are not
  attached in `backend/main.py` (you'll need to verify — read the file
  first)
- A spec source listed above does not exist at the cited path
- An "allowed import" doesn't exist in the codebase
- A forbidden file appears in your edit list
- A golden test fixture is impossible to construct
- The `Constitution V3` drift turns out to block your work (it
  shouldn't · note for Cursor only)
- Endpoint p95 latency exceeds 300 ms even after optimization

Output exactly: `STOP — <reason> · need Michael decision on <specific question>`

---

## Memorial Day lesson reminders (§5 of NEXT_CHAT_CONTINUATION_2026-05-26_AM.md)

These were the bugs that ate Sunday. Do NOT replay them:

1. **Dead-code wiring** — `FakeEvent` mocks passed unit tests but the
   real wiring didn't exist. Counter: tests 14 and 16 use real
   `FiveMinSystem` and `WoodiesSystem` instances + fixtures.
2. **`.data` vs `.payload` typo** — accessed wrong key on event object,
   silently returned empty. Counter: explicit shape-match unit test +
   verbatim quotes of source method return shapes in this prompt.
3. **Silent debug logs on failure paths** — bugs were hidden in
   `logger.debug` instead of surfaced. Counter: constraint (c) above.
4. **Trusting CC report at face value** — fixture said "12/12 green"
   when raw output showed 9/12. Counter: Cursor will compare raw `pytest`
   output to your "self-report" in step 3 of deliverable format.

If you violate any of these, Cursor will catch it in G3 review and the
package will fail promotion.

---

**End of mega-prompt · CC begin work · ETA 2–3 hours · report back to
Cursor on completion via STATUS_BOARD update or chat ping.**
