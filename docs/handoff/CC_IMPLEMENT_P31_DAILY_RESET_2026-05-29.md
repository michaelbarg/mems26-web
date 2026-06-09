# CC IMPLEMENTATION — P31 · Daily Reset / Archive / Demo Readiness

**Date:** 2026-05-29
**Mode:** 🟡 IMPLEMENT · COMMIT-PER-TASK · PER-TASK UAT REQUIRED
**Branch:** `stabilize/mems26-local-truth-2026-05-16` (current)
**Output:** Code commits + per-task fix reports + 1 final P31 summary report

**Reference (READ FIRST, in this order):**
1. `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` — whole file (§14, §15, §16, §17 are NEW since your last read)
2. `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md` — your own audit
3. `docs/reports/CC_CONSULT_P31_2026-05-29.md` — your own consult (boundary decision)
4. `docs/reports/sot_health_audit/04_DAY_TYPE_API_NONE.md` — Bug 04 evidence (T-F)
5. `CLAUDE.md` + `.cursor/rules/mems26-pre-live-protocol.mdc`

---

## §0 · Why this prompt exists

Cursor accepted all 5 of your consult recommendations. This prompt
hands you the implementation. The design doc is the source of truth —
this prompt only adds task-level constraints (UAT, regression tests,
commit boundaries).

**You already proved you understand the problem space.** Your
recommendations (consumer write gate, state machine reset, calendar-date
semantic) are exactly what we're building. **Do not re-design.**

**P32 (tick_reversal TZ + sot_health cleanup) is a SEPARATE prompt.**
Do not touch any P32 items in this work.

---

## §1 · Hard rules (read every commit)

- **Commit per task.** 8 tasks (A–H) + infrastructure tasks (M19, SBM,
  archive tables, is_synthetic, account seed). Each = its own commit.
- **No "while I'm here" refactors.** Smallest correct change per CLAUDE.md.
- **`570f10d` stays.** Do not revert. P31 builds on it. (Per consult §1.4.)
- **`et_calendar_date`, NOT `et_trading_day_18`.** This was your own
  consult §1.4 — re-confirm by reading it before writing the boundary code.
- **Each task gets a regression test.** No "manually verified" — pytest
  green is the gate.
- **Each task UAT covers all 4 axes**: Quality / Recency / Cardinality /
  Latency (CLAUDE.md). Skipping any axis = work not done.
- **No `logger.debug` on failure paths.** Anything that hides a bridge or
  backend error must be `warning` or `error` with rate-limit.
- **No new `TODO` / `FIXME` comments** without a P-ID reference.
- **Bridge stays local-only.** Do not touch `bridge/v9_streams/` in P31
  (P32-I owns the bridge TZ work).
- **Sierra DLL stays untouched.** No `sc_study/` edits in P31.

---

## §2 · Task list (in order — A → B → C → G → E → D → F → H, then infra)

Per consult §2.2. Each task = own commit. Each ends with a UAT block in
its fix report.

### Task A — `_extract_session_date` confirms calendar-date semantic + adds gate hook

**File:** `backend/v9/systems/day_type/consumer.py`

**Action:** No change to the date logic itself (calendar-ET is correct).
Add a method `_should_gate_write(event) -> bool` that returns `True` when
`day_type ∈ (None, "", "UNKNOWN")` AND `lock_state == "PENDING"`. Call
it at the top of `consume()`. If `True`, log at `debug` (this path is
hit on every overnight bar) and return without UPSERTing.

**Why now first:** Closes the immediate bug (premature row writes).
Independent of all other tasks. Reversible.

**Tests (must add):**
- `tests/v9/systems/day_type/test_consumer_write_gate.py` — see design §14.4
  - `test_gate_refuses_unknown_pending` (no DB row written)
  - `test_gate_allows_locked_classification` (row written)
  - `test_gate_allows_locked_low_conf` (row written)
  - `test_gate_does_not_swallow_real_classifications_on_first_bar_of_rth`

**UAT (4 axes):**
- Quality: SQLite `SELECT COUNT(*) FROM v9_day_type_history WHERE date=tomorrow_in_ET AND day_type='UNKNOWN'` → 0 after 30 min of overnight bars
- Recency: an existing classified row's `last_updated_at` does NOT advance during overnight (gate prevents the no-op write)
- Cardinality: 1 row per ET-calendar-date — no duplicates
- Latency: `consume()` p99 stays under 50ms (gate adds <1ms)

**Commit:** `fix(day_type): consumer write gate — refuse UNKNOWN/PENDING UPSERTs (P31-A)`

**Report:** `docs/reports/P31_A_CONSUMER_GATE_2026-05-29.md` — include the 4-axis UAT block.

---

### Task B — State machine reset at 18:00 ET boundary

**Files:**
- `backend/v9/systems/day_type/state_machine.py` — add `reset()` method
- `backend/v9/services/session_boundary/manager.py` — NEW file (`SessionBoundaryManager`)
- `backend/main.py` — wire SBM into startup

**Action (smallest correct change):**

1. Add `DayTypeStateMachine.reset()` that resets all stage state, IB
   accumulator, classification cache, and `_last_classification` to
   initial values. After `reset()`, `to_classification()` returns `None`
   until new bars arrive.

2. Create `SessionBoundaryManager` per design §2.2:
   - Hybrid trigger: FastAPI startup hook + first-bar fallback
   - Idempotency via `v9_session_meta.last_rollover_date`
   - At rollover, calls (in order): `day_type_machine.reset()`,
     `risk_validator.daily_reset()` (Task D), `archive_yesterday()` (infra task)

3. Wire startup hook in `backend/main.py` — wrap in `try/except` per design
   §7.1; never raise.

**Tests:**
- `tests/v9/services/session_boundary/test_rollover_idempotency.py`
- `tests/v9/services/session_boundary/test_state_machine_reset_integration.py`
- `tests/v9/systems/day_type/test_state_machine_reset.py`

**UAT:**
- Quality: after manual rollover trigger, `to_classification()` returns `None`
- Recency: SBM watchdog ticks every 60s as designed
- Cardinality: `v9_session_meta.last_rollover_date` advances by 1 calendar day per rollover, never twice
- Latency: rollover completes in <500ms

**Commit:** `feat(session_boundary): SessionBoundaryManager + state machine reset (P31-B)`

**Report:** `docs/reports/P31_B_SBM_RESET_2026-05-29.md`

---

### Task C — Replace 13× `date.today()` + 2× SQLite `date('now')` with `et_today()`

**MUST land in same PR/series as A. Per consult §STOP, this is the
atomic-with-A item.** If C is delayed, `key_levels_routes._day_type_row()`
breaks the day_type pill for 4 hours every evening.

**Action:**

1. Create `backend/v9/common/trading_date.py`:
   ```python
   from datetime import date, datetime
   from zoneinfo import ZoneInfo
   _ET = ZoneInfo("America/New_York")

   def et_today() -> date:
       """Calendar date in America/New_York. Use for all `today` queries."""
       return datetime.now(_ET).date()
   ```

2. Replace each occurrence (audit §1 catalog, 13 sites):
   - `backend/v9/api/v9/day_type_v9_routes.py::get_current` (🔴)
   - `backend/v9/api/v9/shadow_routes.py::shadow_soak_progress` (🟡)
   - `backend/v9/systems/day_type/hydration.py::hydrate_day_type` (🔴)
   - `backend/v9/systems/day_type/api.py::get_current` (V1 compat) (🔴)
   - `backend/v9/systems/build_status/row_helpers.py::_fires_today` (🔴)
   - `backend/v9/systems/tpo/tpo_system.py::hydrate` (🔴)
   - `backend/v9/systems/tpo/tpo_system.py::process_bar` (🔴) — see Task E
   - `backend/v9/systems/five_min/five_min_system.py::hydrate` (🔴)
   - `backend/v9/systems/build_status/day_type_inspector.py::inspect` (🔴)
   - `backend/v9/systems/build_status/aggregator.py::_get_current_day_type` (🔴)
   - `backend/v9/systems/build_status/aggregator.py::_rth_session_approx` (🟡)
   - `backend/v9/systems/build_status/woodies_inspector.py::_day_type_context` (🔴)
   - test fixture in `tests/v9/test_day_type_api_v9.py` (🟢) — leave it

3. Replace 2× SQLite `date('now')`:
   - `backend/v9/api/v9/key_levels_routes.py::_day_type_row` — bind `et_today().isoformat()` as parameter
   - `backend/v9/api/v9/day_type_v9_routes.py::get_stats` — same

**Tests:**
- `tests/v9/common/test_trading_date.py` — 3 timestamps in different TZs
- `tests/v9/api/test_day_type_routes_et_today.py` — call `/api/v9/day_type/v9/current` with mocked machine TZ shifted to Israel; result must NOT include "tomorrow" data
- `tests/v9/api/test_key_levels_et_today.py` — equivalent for `/api/v9/key_levels`

**UAT:**
- Quality: at 22:30 ET (= 05:30 IL), `/api/v9/day_type/v9/current` returns the **correct** ET-today row (not tomorrow's row)
- Recency: same — `latest_ts` matches `MAX(date)` filtered by `et_today()`
- Cardinality: each `/current` returns ≤ 1 row (no double-rows)
- Latency: <50ms p99 (no regression vs current)

**Commit:** `fix(tz): replace 13 date.today() + 2 SQLite date('now') with et_today() (P31-C)`

**Report:** `docs/reports/P31_C_ET_TODAY_2026-05-29.md` — explicit 4-axis UAT for at least 2 endpoints.

---

### Task G — `logger.debug` → `logger.warning` on failure paths in `backend/main.py`

**Files:** `backend/main.py:282` and `backend/main.py:336`

**Action:** Per CLAUDE.md "No silent failures":

```python
# backend/main.py:282 (current)
_logger.debug("[DayType] DB persist skipped: %s", db_err)
# →
_logger.warning("[DayType] DB persist skipped: %s", db_err, exc_info=True)
```

```python
# backend/main.py:336 (current)
_logger.debug("[DayType] process_bar error: %s", e)
# →
_logger.warning("[DayType] process_bar error: %s", e, exc_info=True)
```

**Why early in sequence:** Once these are at `warning`, all subsequent
tasks' debugging is visible. Almost free fix.

**Tests:** small unit test that triggers each error path, asserts log level ≥ WARNING.

**UAT:** flush logs, run for 5 min, confirm no `[DayType]` warnings in healthy state. Confirm a forced exception (e.g. dropping `v9_day_type_history` temporarily in test DB) DOES surface a warning.

**Commit:** `fix(logging): elevate DayType failure logs to warning per CLAUDE.md (P31-G)`

**Report:** Inline 1-paragraph in P31 final summary (no separate file).

---

### Task E — `tpo_system.process_bar()` `session_id` uses `et_today()`

**File:** `backend/v9/systems/tpo/tpo_system.py::process_bar`

**Action:** `session_id = f"{session_type}_{et_today().isoformat()}"` (depends on Task C).

**Why this is its own task (not folded into C):** It's a state amplifier
per CLAUDE.md Rule 3 (`min/max` aggregators). The TPO session lookup on
restart uses `session_id` — wrong date = wrong session = stale IB
forever. Verifying TPO behaves correctly across rollover deserves its
own UAT block.

**Tests:**
- `tests/v9/systems/tpo/test_tpo_session_id_et_today.py`
- Restart simulation: write a session at 22:00 ET, restart at 22:30 ET, verify hydration loads correct session

**UAT:**
- Quality: `v9_tpo_sessions.session_id` after rollover boundary uses tomorrow's date, not yesterday's
- Recency: `v9_tpo_sessions.opened_ts` matches the session_id date
- Cardinality: 1 RTH session_id per ET-calendar-date
- Latency: hydrate() p99 <100ms

**Commit:** `fix(tpo): session_id uses et_today() not date.today() (P31-E)`

**Report:** Inline in P31 final summary.

---

### Task D — Wire `RiskValidator.daily_reset()` into `SessionBoundaryManager`

**Files:**
- `backend/v9/services/session_boundary/manager.py` (extend Task B)
- `backend/v9/services/risk_validator/validator.py` (no changes — just call it)

**Action:** Inside `SessionBoundaryManager.rollover()`, call `risk_validator.daily_reset()` between `day_type_machine.reset()` and `archive_yesterday()`.

**Tests:**
- `tests/v9/services/session_boundary/test_rollover_calls_risk_reset.py`

**UAT:**
- Quality: after rollover, `RiskValidator.daily_trades_count == 0` and `consecutive_losses == 0`
- (no other axes — purely state reset)

**Commit:** `feat(session_boundary): wire RiskValidator.daily_reset into rollover (P31-D)`

**Report:** Inline in P31 final summary.

---

### Task F — `five_min_system.hydrate()` overnight early-return fix

**File:** `backend/v9/systems/five_min/five_min_system.py::hydrate`

**Action:** Per design §16.3, move the day_type hydrate block (lines
129-155 in current code) to BEFORE the session-type early-return.
Also: skip-if `day_type == "UNKNOWN"` (don't pollute with garbage).

**Tests:**
- `tests/v9/systems/five_min/test_hydrate_day_type_overnight.py`:
  - `test_hydrate_picks_up_day_type_during_overnight` (Normal classification yesterday → today's overnight S2 has `current_day_type=Normal`)
  - `test_hydrate_skips_unknown_day_type` (UNKNOWN row → `current_day_type` stays None)

**UAT:**
- Quality: backend restart at 03:00 ET → `current_day_type` reflects yesterday's last LOCKED classification (NOT None)
- Recency: hydrate uses the latest non-UNKNOWN row from `v9_day_type_state`
- Cardinality: `current_day_type` is a single value (no list/set leak)
- Latency: hydrate completes in <100ms

**Commit:** `fix(five_min): hydrate day_type before overnight early-return (P31-F)`

**Report:** `docs/reports/P31_F_FIVE_MIN_HYDRATE_2026-05-29.md`

---

### Task H — `/current` endpoints reject `ROLLED_OVER` rows

**Files:**
- `backend/v9/api/v9/day_type_v9_routes.py::get_current`
- `backend/v9/api/v9/key_levels_routes.py::_day_type_row` (also gates the pill)
- `backend/v9/systems/day_type/api.py::get_current` (V1 compat)

**Action:** When querying `WHERE date = et_today()`, also `AND status != 'ROLLED_OVER'`. If only ROLLED_OVER row exists, return `{classified: false, status: 'PENDING'}` (same shape as no-row).

**Why depends on B:** ROLLED_OVER status only exists after `SessionBoundaryManager.rollover()` writes it.

**Tests:**
- `tests/v9/api/test_day_type_routes_rejects_rolled_over.py`

**UAT:**
- Quality: after rollover archives yesterday's row, `/current` does NOT return it
- Recency: returns today's PENDING (or null) until first new classification
- Cardinality: 1 row max
- Latency: same (single SQL filter)

**Commit:** `fix(api): /current endpoints reject ROLLED_OVER rows (P31-H)`

**Report:** Inline in P31 final summary.

---

### Infrastructure tasks (in parallel with A–H, but commit separately)

After A–H land, also:

#### M19 — Migration 019: archive tables + `v9_session_meta` + `is_synthetic` columns

Per design §3 + §4 + §11. Single migration file `019_archive_and_session_meta.sql`.

**Tables to add:**
- `v9_session_meta` — `last_rollover_date`, `last_archive_date`, etc.
- `v9_day_type_archive`
- `v9_tpo_sessions_archive`
- `v9_woodies_signals_archive`
- `v9_build_status_archive`
- (per design §3.2)

**Columns to add:**
- `v9_bars_5min.is_synthetic INTEGER NOT NULL DEFAULT 0`
- `v9_woodies_signals.is_synthetic INTEGER NOT NULL DEFAULT 0`
- `v9_trades.is_synthetic INTEGER NOT NULL DEFAULT 0`
- `v9_audit_events.is_synthetic INTEGER NOT NULL DEFAULT 0`
- `v9_five_min_setups.is_synthetic INTEGER NOT NULL DEFAULT 0`

**Indices:** per design §11 — partial index `WHERE is_synthetic = 0` for hot-path queries.

**Tests:** `tests/v9/db/test_migration_019.py` — round-trip apply/rollback.

**Rollback SQL:** Save in migration file as comment block. Per design §7.2.

**Commit:** `feat(db): migration 019 — archive tables + session_meta + is_synthetic (P31-M19)`

**Report:** `docs/reports/P31_M19_MIGRATION_2026-05-29.md`

#### IS — `is_synthetic = 0` filters across ~20 query sites

Per audit §6. After M19 lands. Apply `WHERE is_synthetic = 0` to:
- `v9_bars_5min` — 8 prod queries
- `v9_woodies_signals` — 1 query
- `v9_trades` — 11 queries

**Tests:** existing query tests must still pass + new test that synthetic rows are filtered.

**Commit:** `fix(query): add is_synthetic=0 filter to 20 production queries (P31-IS)`

#### SEED — Seed `v9_account_status` with DEMO mode

Per design §8.1. After M19. Single INSERT.

**Commit:** `feat(account): seed v9_account_status DEMO mode (P31-SEED)`

#### COMPLIANCE — Update `compliance_manifest.yaml`

Add `DEVELOPING`, `ROLLED_OVER` to line 130 enum. Add a test that asserts the manifest enum matches every status string `DayTypeConsumer` may write.

**Commit:** `chore(compliance): add DEVELOPING + ROLLED_OVER to lock_state enum (P31-COMPLIANCE)`

---

## §3 · STOP conditions — pause and ask Michael

Stop the work and write the discovery as a numbered finding at the top
of the **next** report you write, then ask Michael:

1. **`v9_day_type_state` truncation policy unclear.** If audit found 122
   stale `Normal` rows + 133 `UNKNOWN` rows, your rollover must clear
   them. But should it `DELETE WHERE date < today` or mark them stale
   with a flag? Pick the simpler (DELETE) but ask if you find S2 hydrate
   reads pre-yesterday rows.
2. **`compliance_manifest.yaml` enum has a runtime validator** (your
   audit said no — but if you find one, the enum change is no longer
   safe).
3. **Existing migration runner** has issues with adding columns to large
   tables (`v9_bars_5min` = 3,398 rows currently, but MIGRATIONS RUN
   ON LIVE DB).
4. **A pre-existing test breaks** because of the consumer write gate
   (Task A) — possible if a test injects UNKNOWN/PENDING events and
   expects a row.
5. **`570f10d` is reverted by another agent** during your work (check
   `git log -1 --format='%h %s' -- backend/v9/systems/day_type/consumer.py`
   before each task).

---

## §4 · Per-task verification protocol (CC must paste raw output)

Per CLAUDE.md Rule 5 ("Verification quote, not assertion"):

For **every** task UAT, paste **at least**:

```bash
# Targeted test suite — must all pass
pytest tests/v9/<task_path>/ -q

# Full API regression suite — must NOT regress
pytest tests/v9/api/ -q

# 4-axis UAT — paste the actual curl + DB query output for at least 2 axes
curl -s http://localhost:8000/api/v9/<endpoint> | python3 -m json.tool | head -30
sqlite3 data/mems26_local.db "SELECT ..." | head -20
```

**Don't summarize.** Paste the raw output.

---

## §5 · Final P31 summary report

After all tasks land:

**File:** `docs/reports/P31_DAILY_RESET_FINAL_2026-05-29.md`

**Contents:**
- 1 commit hash per task (A through H + infra)
- Rolled-up 4-axis UAT for the integrated system (run a full RTH
  rollover simulation: 17:55 ET → 18:05 ET window, observe DB state)
- Confirm: no `logger.debug` left on failure paths in `backend/v9/`
- Confirm: regression test count ≥ 12 (one per task minimum)
- Pre-flight checklist (design §10) re-run after all changes
- Acknowledgement of read files

---

## §6 · Acknowledgement (for top of P31 final report)

Confirm you read:
- [ ] `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` (whole file, with §14-§17)
- [ ] `docs/reports/CC_AUDIT_DAILY_RESET_2026-05-29.md`
- [ ] `docs/reports/CC_CONSULT_P31_2026-05-29.md`
- [ ] `docs/reports/sot_health_audit/04_DAY_TYPE_API_NONE.md`
- [ ] `CLAUDE.md`
- [ ] `.cursor/rules/mems26-pre-live-protocol.mdc`
- [ ] This prompt

Confirm you did NOT touch:
- [ ] `bridge/v9_streams/` (P32 owns it)
- [ ] `sc_study/` (DLL is locked)
- [ ] `frontend/` (P31 is backend-only; UI happens in Phase 4)
- [ ] `.cursor/rules/` (Cursor owns)

Confirm:
- [ ] All commits are per-task (1 commit = 1 task)
- [ ] All tasks have a regression test
- [ ] No `logger.debug` on failure paths in changed files
- [ ] All 4 UAT axes verified for endpoint-touching tasks
- [ ] `570f10d` is still on HEAD path (no revert)
