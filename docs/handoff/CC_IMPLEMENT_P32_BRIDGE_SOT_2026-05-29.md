# CC IMPLEMENTATION — P32 · Bridge TZ + sot_health Cleanup

**Date:** 2026-05-29
**Mode:** 🟡 IMPLEMENT · COMMIT-PER-TASK · PER-TASK UAT REQUIRED
**Branch:** `stabilize/mems26-local-truth-2026-05-16` (current)
**Prerequisite:** P31 should be merged or at least Tasks A-C landed.
P32 is independent (per consult §2.1) but co-existing on a clean tree
makes UAT cleaner.

**Output:** Code commits + per-task fix reports + 1 final P32 summary

**Reference (READ FIRST):**
1. `docs/reports/sot_health_audit/01_S3_COVERAGE.md`
2. `docs/reports/sot_health_audit/02_TPO_REPOINT.md`
3. `docs/reports/sot_health_audit/03_TICK_REVERSAL_FUTURE_TS.md`
4. `docs/reports/sot_health_audit/05_AUDIT_TABLES_RTH.md`
5. `CLAUDE.md` § Sierra real-time data + Bridge Local-Only Rule

---

## §0 · Why this is a separate prompt from P31

P32 = bridge TZ fix + monitoring cleanup. **Different domain** from P31
(date-of-truth in DB). Splitting:
- Allows independent rollback (bridge fix breaking ≠ daily reset breaking)
- Smaller review surface per PR
- The bridge work touches files **explicitly forbidden in P31**
  (`bridge/v9_streams/`)

**Per consult §2.1, the split is clean — no hidden dependency.** P32-I
(tick_reversal TZ) does NOT need to land before P31's `is_synthetic`
filter (which targets different tables).

---

## §1 · Hard rules

- **Commit per task.** 4 tasks (I, J, K, L). Each = own commit.
- **`CLOUD_URL=http://localhost:8000` only.** Per CLAUDE.md, the bridge
  refuses to start if `CLOUD_URL` is not local. Do not relax this for
  testing.
- **Sierra DLL stays untouched.** P32-I touches the **bridge** only,
  not `sc_study/`. The fix is in `bridge/v9_streams/` (Python side).
- **No `bytecode` commits.** No `*.pyc`, no `__pycache__/`.
- **Regression tests required** for each task.
- **4-axis UAT** for any data-path task (I).

---

## §2 · Tasks

### Task I — `tick_reversal` `+5h` future-ts ROOT FIX

**Origin:** `docs/reports/sot_health_audit/03_TICK_REVERSAL_FUTURE_TS.md`

**Diagnosis (from audit 03):** The Sierra DLL uses two timestamp
encodings:
- `v9_sc_datetime_to_unix()` for 5min/woodies → encodes NY wall-clock,
  NEEDS `+4h` conversion to UTC. ✅ Bridge correctly applies `_chicago_to_utc()`.
- `time(nullptr)` for tick_reversal → already-UTC, does NOT need
  conversion. ❌ Bridge double-corrects → `+5h future-ts` (audit found
  540,411 future rows post-fix).

**Other streams to audit (audit §3 open question):** `cumulative_delta`,
`imbalance_flags`, `stacked_imbalances`, `volume_profile` may also use
`time(nullptr)`. Determine before fix.

**Action (recommended option (a) per audit):**

1. **Audit each stream's DLL ts encoding.** Read `sc_study/MES_AI_DataExport.cpp`
   to identify which streams use `time(nullptr)` vs `v9_sc_datetime_to_unix()`.
   List the result in the fix report.

2. **Add a class attribute `DISABLE_CHICAGO_TS_FIX` on each stream that
   uses real UTC.** In `bridge/v9_streams/base_stream.py::_fix_chicago_bar_ts`,
   check the attribute and skip the conversion when `True`.

3. **Apply to streams that use `time(nullptr)`** (at least
   `tick_reversal_15`, `tick_reversal_12`; possibly others — confirm
   via §1 audit).

4. **Historical cleanup (separate commit, after step 3):**
   ```sql
   UPDATE v9_bars_tick_reversal
     SET ts = datetime(ts, '-4 hours')
     WHERE ts > datetime('now')
   ```
   Wrap in a transaction with `WHERE` guard. Log row count affected.

**Tests:**
- `tests/v9/bridge/test_tick_reversal_no_double_correct.py`
- `tests/v9/bridge/test_disable_chicago_ts_fix_attr.py`

**UAT (4 axes):**
- Quality: after fix, `SELECT COUNT(*) FROM v9_bars_tick_reversal WHERE ts > datetime('now')` → 0 (after both fix AND cleanup)
- Recency: `MAX(ts)` is within 5s of wall-clock UTC during active trading
- Cardinality: row insertion rate continues unchanged (no rows lost from over-aggressive guard)
- Latency: bridge stream tick latency unchanged (<1ms regression)

**Commit 1:** `fix(bridge): per-stream DISABLE_CHICAGO_TS_FIX attribute (P32-I.1)`
**Commit 2:** `fix(bridge): tick_reversal streams skip chicago→UTC conversion (P32-I.2)`
**Commit 3 (cleanup):** `data: backfill v9_bars_tick_reversal future-ts rows (P32-I.3)`

**Report:** `docs/reports/P32_I_TICK_REVERSAL_TZ_2026-05-29.md`

---

### Task J — `sot_health.py` TPO source repoint

**Origin:** `docs/reports/sot_health_audit/02_TPO_REPOINT.md`

**Diagnosis:** `v9_tpo_sessions` is legacy (last write 2026-04-29, 30
days dead). Replaced by `v9_tpo_history` (B1 snapshotter). `sot_health.py`'s
🔴 on `v9_tpo_sessions.opened_ts` is a permanent false-alarm.

**Action:**

1. In `scripts/sot_health.py`, replace:
   ```python
   ("v9_tpo_sessions", "opened_ts")
   ```
   with:
   ```python
   ("v9_tpo_history", "ts")
   ```

2. Add off-hours guard for `v9_tpo_history`: if `now_et < 09:30 ET`,
   stale-empty is 🟡 (expected pre-RTH), not 🔴.

3. Update `docs/reference/SOT_HEALTH.md` to reflect the new source.

**Tests:**
- `tests/scripts/test_sot_health_tpo_repoint.py`

**UAT (lite — sot_health is monitoring, not data path):**
- Quality: post-RTH (after 09:30 ET), `sot_health.py` shows 🟢 FRESH for `v9_tpo_history.ts`
- Pre-RTH: shows 🟡 OFF-HOURS (not 🔴)

**Commit:** `fix(sot_health): repoint TPO source from v9_tpo_sessions to v9_tpo_history (P32-J)`

**Report:** Inline in P32 final summary.

---

### Task K — Add S3 (footprint + tick_reversal) to `sot_health.py`

**Origin:** `docs/reports/sot_health_audit/01_S3_COVERAGE.md`

**Diagnosis:** S3 has 615K footprint bars + 15.9M tick_reversal bars,
but is not in `sot_health.py`'s system map.

**Action:**

1. Add to `sot_health.py` system map:
   ```python
   SystemSpec(
       key="S3_FOOTPRINT",
       label="S3 — Footprint / Tick Reversal",
       sierra_files=["footprint.json", "tick_reversal_15.json", "tick_reversal_12.json"],
       db_tables=[
           ("v9_bars_footprint", "ts"),
           ("v9_bars_tick_reversal", "ts"),  # ← only after P32-I fix
       ],
       api_endpoints=["/api/v9/footprint/current"],
   ),
   ```

2. **Order vs P32-I:** Adding `v9_bars_tick_reversal` to monitoring
   only makes sense AFTER P32-I cleans up the future-ts. Otherwise
   sot_health will show false-future-ts errors. **K commits AFTER I**.

**Tests:** add S3 expectation to `tests/scripts/test_sot_health_systems.py` if it exists.

**UAT (lite):**
- During RTH, sot_health shows 🟢 FRESH for both `v9_bars_footprint` and `v9_bars_tick_reversal`
- The relevant API (`/api/v9/footprint/current`) returns 200

**Commit:** `feat(sot_health): add S3 (footprint + tick_reversal) to system map (P32-K)`

**Report:** Inline.

---

### Task L — Remove `v9_audit_events` + `v9_trade_management_log` from `sot_health.py`

**Origin:** `docs/reports/sot_health_audit/05_AUDIT_TABLES_RTH.md`

**Diagnosis:** Orphaned schemas. Zero rows historically. Zero writers
in codebase. The SQLAlchemy models at `backend/v9/db/models/audit.py`
and `trade_log.py` point to wrong table names (`v9_ns`, `v9_n_log`)
that don't exist either.

**Action:**

1. In `scripts/sot_health.py` `TRADE_MANAGER` system spec, remove:
   ```python
   ("v9_trade_management_log", "ts"),
   ("v9_audit_events", "ts_ms"),
   ```
   Keep `("v9_trades", "entry_ts")`.

2. Add a `# TODO(P-future):` comment referencing audit 05 for when the
   audit/log infrastructure is built.

3. **Do NOT touch the SQLAlchemy models or the DB schema.** Removing
   tables would lose pre-existing schema artifacts and cause migration
   conflicts. The models stay (broken table names) — that's a separate
   cleanup for whoever wires the writers.

**Tests:** none (cleanup, no logic).

**UAT:** sot_health no longer shows 🔴 MISSING for these tables.

**Commit:** `chore(sot_health): remove orphaned v9_audit_events + v9_trade_management_log (P32-L)`

**Report:** Inline in P32 final summary.

---

## §3 · STOP conditions

1. **`sc_study/` audit reveals MORE streams use `time(nullptr)` than
   expected.** If `cumulative_delta` or `imbalance_flags` also use
   `time(nullptr)`, the fix scope expands. Stop and report — Michael
   may want to handle as separate sub-tasks.
2. **The historical cleanup `UPDATE` would affect more than 1M rows.**
   The `WHERE ts > datetime('now')` should bound it to ~540K per audit.
   If the count is much higher, stop — there may be additional bug
   sources.
3. **A test fails because someone wrote to `v9_audit_events` recently.**
   The audit said zero writers — verify with a fresh `git log` before
   removing from sot_health.
4. **`MES_AI_DataExport.cpp` is changed by another agent during P32.**
   Check `git log -1 -- sc_study/` before reading it. CLAUDE.md forbids
   DLL changes — if you see one, escalate.

---

## §4 · Per-task verification protocol

Same as P31 §4 — paste raw `pytest` output + `sqlite3` queries.

For Task I specifically:

```bash
# Before fix:
sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_bars_tick_reversal WHERE ts > datetime('now')"
# Should be ~540,000

# After fix (steps 1+2, before cleanup):
# New rows after the fix: should be 0 future
sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_bars_tick_reversal WHERE ts > datetime('now') AND id > <pre_fix_max_id>"
# Should be 0

# After cleanup (step 3):
sqlite3 data/mems26_local.db "SELECT COUNT(*) FROM v9_bars_tick_reversal WHERE ts > datetime('now')"
# Should be 0
```

---

## §5 · Final P32 summary report

**File:** `docs/reports/P32_BRIDGE_SOT_FINAL_2026-05-29.md`

Per-task commit hashes + UAT pasted output + before/after sot_health
output (the 🔴/🟡/🟢 status of every system).

---

## §6 · Acknowledgement

Confirm you read:
- [ ] All 4 sot_health audit reports (01, 02, 03, 05)
- [ ] `CLAUDE.md` Bridge Local-Only Rule + Sierra real-time data
- [ ] `bridge/v9_streams/base_stream.py` (current state of `_fix_chicago_bar_ts`)
- [ ] `sc_study/MES_AI_DataExport.cpp` (read-only, to identify ts encoding per export)
- [ ] This prompt

Confirm you did NOT touch:
- [ ] `sc_study/` (DLL is locked — read-only access for the audit step)
- [ ] `backend/v9/api/`, `backend/v9/systems/` (P31 owns these)
- [ ] `frontend/` (separate phase)
- [ ] `.cursor/rules/`, `CLAUDE.md` (Cursor owns)

Confirm:
- [ ] All commits are per-task
- [ ] Bridge `CLOUD_URL=http://localhost:8000` is unchanged
- [ ] No `*.pyc` / `__pycache__/` in commits
