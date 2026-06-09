# CC IMPLEMENTATION — P31.1 · Fix-up for P31 gaps + regressions

**Date:** 2026-05-29
**Mode:** IMPLEMENT · COMMIT-PER-TASK · RAW UAT REQUIRED PER COMMIT
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Output:** 6 commits + 1 final report with PASTED raw UAT output
**Reference:**
- `docs/handoff/CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` (original P31 prompt)
- `docs/reports/CC_INQUIRY_P31_GAPS_2026-05-29.md` (your inquiry response)
- `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` §14, §15, §16, §17
- `docs/reports/P31_DAILY_RESET_FINAL_2026-05-29.md` (your previous final report)
- `CLAUDE.md` § "Source-of-Truth Discipline" (Rule 5: paste output, not assertion)

---

## §0 · Why this exists

P31 shipped with 9 gaps and 31 test failures (6 are real new
regressions, 25 are pre-existing). Your inquiry response was honest
and your 6-commit plan is the starting point for P31.1 — but Cursor
adds 4 corrections to that plan based on architectural judgment.
**Read §2 carefully — your inquiry plan is NOT what we are
implementing.**

The 4 corrections (in priority order):

1. **F2 fix is NOT env-var guard.** It is making `check_rollover()`
   itself idempotent + ground-state-safe. See T1 below.
2. **F1+F4 fix MUST delete `data/v9.db` first.** Two DBs is worse
   than one wrong DB.
3. **F3 archive_yesterday() semantics MUST be explicit.** INSERT
   into archive, then UPDATE status='ROLLED_OVER'. NEVER DELETE the
   row. (Per CLAUDE.md Rule 1 — honest data > silent loss.)
4. **F6 test_migration_019 MUST use a temp DB.** It cannot run
   against `data/mems26_local.db` (which is live).

---

## §1 · Hard rules

- **NO subagents.** Per your inquiry §6, you delegated tasks C, G, F
  and lost test-file uniformity. P31.1 is small enough — do it
  yourself.
- **NO commit message until raw UAT pasted.** For every commit, paste
  to `git commit -m`'s draft area:
  - The `pytest` output (last 20 lines minimum)
  - For DB tasks: the `sqlite3 PRAGMA` or `SELECT COUNT(*)` output
  - For endpoint tasks: the `curl ... | head -30` output
- **NO "I checked" without raw output.** Every claim in the report
  must be verifiable from a pasted command.
- **MUST run full test suite** (`pytest tests/v9/`) at start AND end
  of P31.1 — count failures both times. If end > start, P31.1 broke
  something. If end < start, P31.1 is succeeding.
- **NO new `logger.debug` on failure paths.**
- **NO hard-coded absolute paths** (`/Users/michael/Downloads/...`).
- **No new TODO/FIXME without P-ID reference.**

---

## §2 · Tasks (in dependency order)

### Task T1 — Fix regression (Finding #2)

**Diagnosis (your inquiry §F2):** `_startup()` calls
`sbm.check_rollover()` → `day_type_machine.reset()` → wipes state
machine that other tests need.

**Cursor correction to your fix:** Do NOT use env-var guard. Make
`check_rollover()` itself ground-state-safe.

**File:** `backend/v9/services/session_boundary/manager.py`

**Action:**

1. In `check_rollover()`, change the logic:

```python
def check_rollover(self) -> bool:
    today = et_today()
    last = self._get_last_rollover_date()

    # FIRST RUN — no rollover history. Seed and skip.
    # This is NOT a rollover; we have no "yesterday" to archive.
    if last is None:
        logger.info("[SessionBoundary] first run on %s — seeding (no reset)", today)
        self._set_last_rollover_date(today)
        return False

    # Already rolled over today — no-op.
    if last >= today:
        logger.debug("[SessionBoundary] already rolled over for %s", today)
        return False

    # last < today → real rollover.
    return self._perform_rollover(today)
```

2. The change: when `last is None`, **seed without resetting**. This
   means a fresh DB or a fresh test DB doesn't trigger a state-machine
   wipe just because there's no history yet. Real rollovers (when
   `last < today`) still do the full chain.

**Why this is better than env-var:**
- Tests behave identically to production (no special-case wiring).
- A real first-day deployment doesn't accidentally reset state on
  startup just because nothing was archived yet.
- The regression is fixed at the architectural level, not papered
  over.

**Tests (UPDATE existing):**

`tests/v9/services/session_boundary/test_rollover_idempotency.py`:
- Add `test_first_run_seeds_without_reset` — fresh DB, machine NOT
  reset, returns False
- Add `test_real_rollover_triggers_reset` — DB has last=yesterday,
  machine IS reset, returns True
- Existing `test_first_call_performs_rollover` MUST be renamed/updated
  (its current semantics are wrong — first call should NOT reset)

**UAT (paste these literally in commit message):**

```bash
# Before fix — confirm regression exists
$ python3 -m pytest tests/v9/systems/test_day_type/test_day_type.py::TestStateMachineStages::test_a4_ib_lock -q
FAILED ... (1 failed)

# After fix — confirm green
$ python3 -m pytest tests/v9/systems/test_day_type/test_day_type.py::TestStateMachineStages::test_a4_ib_lock -q
1 passed

# Full state-machine suite — confirm no regressions remain
$ python3 -m pytest tests/v9/systems/test_day_type/ tests/v9/systems/test_day_type_ib_live.py -q
N passed
```

**Commit:** `fix(session_boundary): check_rollover seeds without reset on first run (P31.1-T1)`

---

### Task T2 — Migration cleanup + run (Findings #1, #4)

**File:** `backend/v9/db/migrations/versions/019_archive_and_session_meta.py`

**Action:**

1. Fix the `DB_PATH` default. Replace:
```python
DB_PATH = os.environ.get(
    "V9_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "v9.db"),
)
```
with:
```python
DB_PATH = os.environ.get(
    "V9_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "mems26_local.db"),
)
```

2. **Add the missing 5th ALTER (Finding #4):**
```python
"ALTER TABLE v9_audit_events ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0",
```
Append to the `alter_statements` list.

3. **Add the missing 4th archive table (Finding #4):**

```python
cur.execute("""
    CREATE TABLE IF NOT EXISTS v9_build_status_archive (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        trading_date TEXT NOT NULL,
        snapshot_ts  TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        archived_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )
""")
print("[019] v9_build_status_archive: OK")
```

4. **Cleanup orphan `data/v9.db` if it exists** (you may have created
   one in the failed run):

   - Run `ls -la data/v9.db` — if it exists, `rm data/v9.db`. If it
     does not exist, skip. Document either way in your UAT.

5. **Run the migration on the live DB:**
```bash
python3 backend/v9/db/migrations/versions/019_archive_and_session_meta.py data/mems26_local.db
```

**Verification (paste in commit message):**

```bash
$ ls -la data/v9.db data/mems26_local.db
# Expect: only mems26_local.db exists

$ sqlite3 data/mems26_local.db "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'v9_%_archive' OR name LIKE 'v9_session_meta' ORDER BY name"
v9_build_status_archive
v9_day_type_archive
v9_session_meta
v9_tpo_sessions_archive
v9_woodies_signals_archive

$ for t in v9_bars_5min v9_woodies_signals v9_trades v9_audit_events v9_five_min_setups; do
    echo -n "$t: "
    sqlite3 data/mems26_local.db "PRAGMA table_info($t)" | grep is_synthetic
  done
# Expect: each prints `<n>|is_synthetic|INTEGER|1|0|0`
```

**Commit:** `feat(db): migration 019 fixes + apply to live DB (P31.1-T2)`

---

### Task T3 — Complete SessionBoundaryManager (Finding #3)

**File:** `backend/v9/services/session_boundary/manager.py` + `backend/main.py`

**Action — three additions:**

**A. First-bar fallback subscription**

In `manager.py`, add:
```python
def subscribe_to_bar_router(self, bar_router) -> None:
    """First-bar fallback: trigger rollover on the first 5min bar
    of the new day. Belt-and-suspenders with the startup hook —
    handles the case where the backend has been running through
    the 18:00 ET boundary without a restart.
    """
    def _on_bar(bar):
        try:
            self.check_rollover()
        except Exception as e:
            logger.warning("[SessionBoundary] first-bar fallback error: %s", e, exc_info=True)
    bar_router.subscribe("5min", _on_bar)
    logger.info("[SessionBoundary] subscribed to 5min via BarRouter (first-bar fallback)")
```

In `main.py`, after `sbm = SessionBoundaryManager(...)`, also wire:
```python
sbm.subscribe_to_bar_router(bar_router)
```

**B. archive_yesterday() — explicit semantics (Cursor correction to your inquiry plan)**

`_perform_rollover()` MUST archive yesterday's data BEFORE the state
machine reset. Sequence:

```python
def _perform_rollover(self, today: date) -> bool:
    try:
        logger.info("[SessionBoundary] rollover fired for date=%s", today)

        # 1. ARCHIVE yesterday's data (INSERT + UPDATE, never DELETE).
        archived = self._archive_yesterday(today)
        logger.info("[SessionBoundary] archived: %s", archived)

        # 2. TRUNCATE stale v9_day_type_state rows (>2 days old).
        truncated = self._truncate_stale_state(today)
        logger.info("[SessionBoundary] truncated v9_day_type_state: %d rows", truncated)

        # 3. RESET state machine.
        if self.day_type_machine is not None:
            self.day_type_machine.reset()
            logger.info("[SessionBoundary] DayTypeStateMachine reset")

        # 4. RESET risk validator.
        if self.risk_validator is not None:
            self.risk_validator.daily_reset()
            logger.info("[SessionBoundary] RiskValidator daily_reset")

        # 5. MARK rollover complete.
        self._set_last_rollover_date(today)
        return True

    except Exception as e:
        logger.error("[SessionBoundary] rollover failed: %s", e, exc_info=True)
        return False


def _archive_yesterday(self, today: date) -> dict:
    """Archive rows with date < today (exclusive) into matching _archive
    tables, then mark them ROLLED_OVER. Never DELETE — per CLAUDE.md
    Rule 1, honest data preservation.
    """
    counts = {"day_type": 0, "tpo_sessions": 0, "woodies_signals": 0}
    conn = sqlite3.connect(self.db_path)
    try:
        cur = conn.cursor()

        # day_type_history → day_type_archive
        cur.execute("""
            INSERT INTO v9_day_type_archive
              SELECT *, datetime('now') AS archived_at
              FROM v9_day_type_history
              WHERE date < ? AND COALESCE(status, '') != 'ROLLED_OVER'
        """, (today.isoformat(),))
        counts["day_type"] = cur.rowcount

        cur.execute("""
            UPDATE v9_day_type_history
              SET status = 'ROLLED_OVER'
              WHERE date < ? AND COALESCE(status, '') != 'ROLLED_OVER'
        """, (today.isoformat(),))

        # tpo_sessions → tpo_sessions_archive (similar pattern, by trading_date)
        cur.execute("""
            INSERT INTO v9_tpo_sessions_archive
              SELECT *, datetime('now') AS archived_at
              FROM v9_tpo_sessions
              WHERE trading_date < ?
        """, (today.isoformat(),))
        counts["tpo_sessions"] = cur.rowcount

        # woodies_signals — by date(ts)
        cur.execute("""
            INSERT INTO v9_woodies_signals_archive
              SELECT *, datetime('now') AS archived_at
              FROM v9_woodies_signals
              WHERE date(ts) < ?
        """, (today.isoformat(),))
        counts["woodies_signals"] = cur.rowcount

        conn.commit()
    finally:
        conn.close()
    return counts


def _truncate_stale_state(self, today: date) -> int:
    """Delete v9_day_type_state rows older than 2 days."""
    cutoff = (today - timedelta(days=2)).isoformat()
    conn = sqlite3.connect(self.db_path)
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM v9_day_type_state WHERE date(ts) < ?", (cutoff,))
        n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()
```

**Tests:**

`tests/v9/services/session_boundary/test_archive_yesterday.py`:
- `test_archive_inserts_into_archive_table` — populate yesterday row, rollover, verify INSERT
- `test_archive_marks_rolled_over` — same, verify status='ROLLED_OVER' in v9_day_type_history (not deleted)
- `test_archive_skips_already_rolled_over` — idempotent: running twice doesn't double-insert
- `test_truncate_state_removes_old_rows` — 3-day-old row gone, 1-day-old kept

**UAT:**

```bash
# Before manual rollover trigger
$ sqlite3 data/mems26_local.db "SELECT date, status FROM v9_day_type_history ORDER BY date DESC LIMIT 5"
$ sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_day_type_archive"

# Trigger rollover (force last_rollover_date = older)
$ python3 -c "
import sys; sys.path.insert(0, '.')
from backend.v9.services.session_boundary import SessionBoundaryManager
from datetime import date, timedelta
sbm = SessionBoundaryManager(db_path='data/mems26_local.db')
sbm._set_last_rollover_date(date.today() - timedelta(days=1))
sbm.check_rollover()
"

# After
$ sqlite3 data/mems26_local.db "SELECT date, status FROM v9_day_type_history ORDER BY date DESC LIMIT 5"
# Expect: yesterday rows marked ROLLED_OVER
$ sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_day_type_archive"
# Expect: count > 0
```

**Commit:** `feat(session_boundary): archive_yesterday + first-bar fallback + truncate stale state (P31.1-T3)`

---

### Task T4 — Cleanup (Findings #5, #7, #8)

**Files:**
- `backend/v9/api/v9/tpo_routes.py:244` — Finding #5
- `backend/v9/systems/footprint/footprint_system.py:128` — Finding #5
- `backend/main.py:348` — Finding #7
- `backend/v9/systems/day_type/api.py:93` — Finding #8

**Action:**

1. **#5a** — `tpo_routes.py:244`: replace `date('now')` with bind:
   ```python
   "AND trading_date < ? "  # was: date('now')
   ```
   pass `et_today().isoformat()` as parameter.

2. **#5b** — `footprint_system.py:128`: same pattern.

3. **#7** — `main.py:348`:
   ```python
   db_path=os.path.join(os.path.dirname(__file__), '..', 'data', 'mems26_local.db')
   ```
   (or whatever the project-root-relative path resolves to — verify
   the path exists at startup).

4. **#8** — `api.py:93`: remove the dead `AND lock_state != 'ROLLED_OVER'`
   from the V1 compat query (per your inquiry §F8 — it's dead code).

**Tests:**

- `tests/v9/api/test_tpo_routes_et_today.py` — verify `tpo_routes` uses ET, not UTC
- `tests/v9/systems/footprint/test_footprint_system_et_today.py` — same for footprint
- (Hardcoded path #7 — no test, just visual)
- (Dead filter #8 — confirm V1 endpoint still returns the right row via `test_day_type_routes_rejects_rolled_over.py` updated)

**UAT:**

```bash
$ rg "date\('now'\)" backend/v9
# Expect: 0 matches

$ rg "/Users/michael/Downloads/mems26_web_git" backend/main.py
# Expect: 0 matches

$ rg "lock_state != 'ROLLED_OVER'" backend/v9
# Expect: 0 matches
```

**Commit:** `fix(query): remove 2 SQLite date('now'), hardcoded path, dead filter (P31.1-T4)`

---

### Task T5 — Missing test files (Finding #6)

Create the 4 test files with **isolated DB** pattern (Cursor correction to inquiry plan):

1. **`tests/v9/api/test_day_type_routes_et_today.py`** — verifies `/api/v9/day_type/v9/current` uses ET, not Israel TZ. Mock the machine clock to 22:30 ET (= 05:30 IL next day) and verify the endpoint returns the today (ET) row.

2. **`tests/v9/api/test_key_levels_et_today.py`** — same for `/api/v9/key_levels`. Particularly test the `_day_type_row()` query.

3. **`tests/v9/db/test_migration_019.py`** — **isolated temp DB** (CRITICAL):
```python
import tempfile, sqlite3
from backend.v9.db.migrations.versions import 019_archive_and_session_meta as m019

def test_migration_019_creates_all_tables():
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        # Seed minimal schema (the tables migration 019 ALTERs)
        conn = sqlite3.connect(f.name)
        for ddl in MINIMAL_SEED_DDL:
            conn.execute(ddl)
        conn.commit()
        conn.close()
        # Apply migration
        m019.migrate(f.name)
        # Verify
        conn = sqlite3.connect(f.name)
        ...
```
Tests must NOT touch `data/mems26_local.db`.

4. **`tests/v9/systems/day_type/test_compliance_manifest_enum.py`** — verify the `lock_state` enum in `compliance_manifest.yaml` includes every status string `DayTypeConsumer` may write.

**UAT:**

```bash
$ python3 -m pytest tests/v9/api/test_day_type_routes_et_today.py tests/v9/api/test_key_levels_et_today.py tests/v9/db/test_migration_019.py tests/v9/systems/day_type/test_compliance_manifest_enum.py -v
```
Paste the full output (all assertions, all green).

**Commit:** `test(p31): add 4 missing UAT files (P31.1-T5)`

---

### Task T6 — Final report with raw UAT (Finding #9)

**File:** `docs/reports/P31_1_FIXUP_FINAL_2026-05-29.md`

**Required sections:**

1. **Commit hashes** for T1–T5
2. **Full pytest output** at start of P31.1 (failure count) and end of P31.1 (failure count). The end count MUST be ≤ start count for the same suite.
3. **Per-task UAT** — paste the actual command output (not summary). For T2 specifically, paste the `PRAGMA table_info` output for all 5 modified tables.
4. **Pre-flight checklist re-run** — design §10, paste raw output for §10.1 (date.today count), §10.4 (UPSERTs into archive-source tables), §10.6 (latest migration number).
5. **Acknowledgement footer.**

**No-summarize rule:** Every claim of "X works" or "Y is fixed" must
have a pasted command output adjacent. Per CLAUDE.md Rule 5.

**Commit:** `docs(p31.1): final fixup report with raw UAT output`

---

## §3 · STOP conditions

Stop and write the discovery as a numbered finding at the top of
P31.1 final report, then ask Michael:

1. **Migration runs but fails on a column already exists** — the
   `try/except duplicate column` clause should handle this. If you
   see a different error, stop.
2. **Test T1 reveals MORE regressions** beyond the 6 listed — could
   mean `state_machine.reset()` itself has bugs (not just the wiring).
3. **`v9_day_type_state` already has rows older than 2 days** that
   you'd be deleting. Show the count first; if > 1000 rows, ask before
   truncating.
4. **`archive_yesterday()` finds rows where `date >= today`** in
   `v9_day_type_history` (shouldn't happen) — pre-existing data
   pollution. Don't delete; report.
5. **A new test (T5) exposes an issue in P31's existing code** that
   we didn't catch.

---

## §4 · Per-commit verification protocol (mandatory)

Per CLAUDE.md Rule 5 + your inquiry §F9 self-acknowledgement.

For **EVERY** commit (T1-T6), the commit message body MUST include:

```
UAT (raw, not summary):

$ <command 1>
<output line 1>
<output line 2>
...

$ <command 2>
<output>
```

If the commit message does not have raw UAT, the commit is incomplete.
You may amend the commit (within your own session, before push) to
add UAT. After push, no amend.

---

## §5 · Acknowledgement (top of final report)

- [ ] Original P31 prompt re-read
- [ ] Inquiry response (your own) re-read
- [ ] This P31.1 prompt read
- [ ] CLAUDE.md Rule 5 re-read
- [ ] Pre-P31.1 baseline test failure count recorded
- [ ] Post-P31.1 test failure count recorded (must be ≤ baseline)
- [ ] No subagents used in P31.1
- [ ] All 6 commits include raw UAT in commit message body
- [ ] All 4 missing test files created and passing
- [ ] Migration 019 applied to `data/mems26_local.db` (not `data/v9.db`)
- [ ] `data/v9.db` does not exist after P31.1 (or never existed)
- [ ] No new hard-coded absolute paths
- [ ] No new `logger.debug` on failure paths
