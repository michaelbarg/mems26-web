# CC INQUIRY — P31 Gaps & Regressions

**Date:** 2026-05-29
**Mode:** 🟢 INQUIRY · NO CODE CHANGES · NO COMMITS · NO MIGRATIONS · NO TEST RUNS
**Output:** `docs/reports/CC_INQUIRY_P31_GAPS_2026-05-29.md` (single file, ≤200 lines)
**Reference:**
- `docs/handoff/CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md` (the original prompt)
- `docs/reports/P31_DAILY_RESET_FINAL_2026-05-29.md` (your final report)
- `docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md` §14, §15, §16, §17

---

## §0 · Why this exists

Cursor verified your P31 work against:
- The live DB (`data/mems26_local.db`) — `PRAGMA table_info`
- The live test suite (`pytest tests/v9/`)
- The live code (file reads, `git show`)
- The original implementation prompt

**Found 9 gaps between your final report and reality.** This inquiry
is to understand **why** before we write a fix-up prompt. Per Michael:
*"first ask CC what happened, then have CC recommend, then we write
the fix prompt"*.

**This is not blame.** It is verification protocol per CLAUDE.md Rule
5 ("paste the command + raw output, not 'confirmed, moving on'"). You
made 11 commits in ~30 min. Some scope was deferred consciously
(P31-IS, P31-SEED), some was a misunderstanding, some was a regression
you did not catch. We need you to tell us which is which, per gap.

---

## §1 · Findings (raw evidence)

### Finding 1 — Migration 019 NOT applied to live DB

**Evidence:**
```
$ sqlite3 data/mems26_local.db "SELECT name FROM sqlite_master WHERE name='v9_session_meta'"
(empty — table does not exist)

$ for t in v9_bars_5min v9_woodies_signals v9_trades v9_audit_events v9_five_min_setups; do
    sqlite3 data/mems26_local.db "PRAGMA table_info($t)" | grep is_synthetic
  done
(no output — none of the 5 tables have is_synthetic column)
```

**Suspected cause:** The migration's `DB_PATH` default is
`data/v9.db`, not `data/mems26_local.db`. If you ran it without the
env var, you migrated a non-existent DB. Confirm.

### Finding 2 — Regression: `test_a4_ib_lock` + 5 others passing on `99671e4`, FAILING on HEAD

**Evidence:**
```
$ git checkout 99671e4 -- backend/v9 && pytest tests/v9/systems/test_day_type/test_day_type.py::TestStateMachineStages::test_a4_ib_lock -q
1 passed in 0.39s

$ git checkout HEAD -- backend/v9 && pytest .../test_a4_ib_lock -v
FAILED — assert sm.ib_locked == True; actual False
```

Other regressions:
- `test_b1_initial_vote`
- `test_open_drive_narrow_ib_trend_dd`
- `test_full_session_to_lock`
- 6× `test_day_type_ib_live` (TestIBLiveMeta, TestToClassificationDeveloping)
- `test_open_session_new_trading_date_resets_ib`

Total: **31 test failures** vs your report's "0 new failures".

**Suspected cause:** `state_machine.reset()` you added in commit B
(`27c3145`) likely cleared a field needed by the IB lock check
(`_check_a4_lock` or sibling). Confirm by reading your diff:
```
$ git show 27c3145 -- backend/v9/systems/day_type/state_machine.py
```

### Finding 3 — Task B incomplete: no first-bar fallback, no archive_yesterday, no truncate v9_day_type_state

**Your final report claims:**
> "Hybrid trigger (startup + first-bar fallback). Calls
> day_type_machine.reset() + risk_validator.daily_reset() at rollover."

**Reality (from `backend/main.py` and `manager.py`):**
- `check_rollover()` is called **once at startup**. There is no
  `bar_router.subscribe("5min", lambda bar: sbm.check_rollover())`
  anywhere — search confirms.
- `_perform_rollover()` does NOT call any `archive_yesterday()`.
- `_perform_rollover()` does NOT truncate `v9_day_type_state` (per design §16.4).

**Why this matters:** if the backend runs continuously from 14:00 ET
through 20:00 ET, it never restarts → no rollover triggers → all the
work is dead.

### Finding 4 — Migration 019 missing items

**Your `019_archive_and_session_meta.py` has:**
- 4 `is_synthetic` ALTERs (`v9_bars_5min`, `v9_woodies_signals`,
  `v9_trades`, `v9_five_min_setups`)
- 3 archive tables (`v9_day_type_archive`, `v9_tpo_sessions_archive`,
  `v9_woodies_signals_archive`)

**Prompt + design §3.2 + §11 required:**
- 5 `is_synthetic` ALTERs (also `v9_audit_events`)
- 4 archive tables (also `v9_build_status_archive`)

### Finding 5 — Task C missed 2 SQLite `date('now')` occurrences

**Evidence:**
```
$ rg "date\('now'\)" backend/v9
backend/v9/api/v9/tpo_routes.py:244:    "AND trading_date < date('now') "
backend/v9/systems/footprint/footprint_system.py:128:    "WHERE date(created_at) = date('now')"
```

**Your report claims:** "All date queries now use ET timezone."
Reality: 2 still use SQLite UTC `date('now')`.

The audit (§9.2) only flagged `key_levels._day_type_row()` and
`day_type_v9_routes.get_stats()`. These 2 new ones (`tpo_routes.py:244`
and `footprint_system.py:128`) were not in the audit catalog. **Did
you grep for `date('now')` before claiming "all replaced", or did you
only fix the 2 from the audit?**

### Finding 6 — Test files claimed-but-missing

**Your report claims** "35+ tests added" and "All tasks have regression
tests."

**File-level inventory:**
| Required by prompt | Status |
|---|---|
| `test_consumer_write_gate.py` | ✅ exists |
| `test_trading_date.py` | ✅ exists |
| `test_hydrate_day_type_overnight.py` | ⚠ exists but in `tests/v9/systems/test_five_min/` (typo: should be `tests/v9/systems/five_min/`) |
| `test_tpo_session_id_et_today.py` | ✅ exists |
| `test_rollover_idempotency.py` | ✅ exists |
| `test_state_machine_reset.py` | ✅ exists |
| `test_day_type_routes_rejects_rolled_over.py` | ✅ exists |
| `test_day_type_routes_et_today.py` | ❌ **missing** (Task C UAT) |
| `test_key_levels_et_today.py` | ❌ **missing** (Task C UAT) |
| `test_migration_019.py` | ❌ **missing** (Task M19) |
| `test_compliance_manifest_enum.py` | ❌ **missing** (COMPLIANCE) |

**35 tests across 7 files** — not 4 separate UAT-axis files. The 35
count is honest at the assertion level, but Task C and Task M19
shipped without their dedicated UAT tests.

### Finding 7 — Hard-coded absolute paths in production code

```
$ rg "/Users/michael/Downloads/mems26_web_git" backend/main.py backend/v9/systems/day_type/api.py
backend/main.py:348:                db_path="/Users/michael/Downloads/mems26_web_git/data/mems26_local.db",
backend/v9/systems/day_type/api.py:88:    DB_PATH = "/Users/michael/Downloads/mems26_web_git/data/mems26_local.db"
```

**main.py:348 is your code (P31-B commit).** `api.py:88` may be
pre-existing — confirm with `git blame -L 88,88 -- backend/v9/systems/day_type/api.py`.

CLAUDE.md ENVIRONMENT.md (and common sense) forbids hard-coded
absolute paths. Should be from env or `os.path.dirname(__file__)`.

### Finding 8 — Task H V1 compat (`api.py:93`) filter is logically odd

**Code:**
```python
"SELECT * FROM v9_day_type_state WHERE lock_state='LOCKED' AND lock_state != 'ROLLED_OVER' AND date(ts)=? ORDER BY id DESC LIMIT 1"
```

**Two issues:**
1. The redundant `AND lock_state != 'ROLLED_OVER'` after
   `lock_state='LOCKED'` is dead code — `'LOCKED' != 'ROLLED_OVER'`
   is always true.
2. The query is on `v9_day_type_state`, but `ROLLED_OVER` per design
   is a `status` value on `v9_day_type_history`. The filter applies
   to the wrong table.

**The V9 + key_levels endpoints ARE correct.** Just V1 compat is
weird. Did you intend the V1 query to gate on `v9_day_type_history`
or is the V1 path already using `v9_day_type_state` for a different
reason?

### Finding 9 — Final report missing 4-axis UAT raw output

**The original prompt (§4) required:**
> Per CLAUDE.md Rule 5: For every task UAT, paste at least pytest
> output + curl + sqlite3 query output. Don't summarize. Paste the
> raw output.

**Your final report has:** 1-line summary per task. No raw curl
output. No sqlite3 PRAGMA or COUNT outputs. No timing for latency
axis.

This is what triggered Cursor to do the verification — and finding
the issues above. **What stopped you from running the UAT before
declaring P31 complete?**

---

## §2 · Your job — answer 3 questions per finding

For **each** finding above (1-9), write 3 short answers:

1. **What happened?** (your perspective — bug? misunderstanding?
   skipped intentionally? not visible to you?)
2. **Did you know it was a gap when you wrote the report?** (yes /
   no / partial)
3. **What is the smallest correct fix?** (1-2 sentences)

Format: bullet list under each finding. No paragraphs.

---

## §3 · Your recommendation for P31.1 fix-up

After answering all 9 findings, write a **§Recommendation** section:

1. **Ordering** — which fixes must be atomic (e.g. is the regression
   #2 a hard prerequisite for #1 — without fixing the state machine
   first, the migration writes a broken row?)
2. **Is any finding actually NOT a bug** (you'd push back) — argue.
3. **Estimated commits** for P31.1 (per-task, like P31).
4. **Risk** — does any fix touch shared code that might re-break the
   passing 35 tests? Specifically: regression #2 — what's your
   diagnosis and proposed fix?

---

## §4 · Hard rules

- **NO code changes**, **NO commits**, **NO migration runs**, **NO
  pytest runs**.
- This is **inquiry only**. We will write the implementation prompt
  ourselves once we read your answers.
- **Cite by symbol** (function/class) + line range when reading code.
- **Do not extrapolate fixes you have not analyzed** — if you don't
  know why `test_a4_ib_lock` fails, say so. Don't guess "it's
  probably the state cache" without reading the diff.

---

## §5 · STOP conditions

If you discover during this inquiry:
- A 10th gap not in §1 above → add it as Finding 10 (with raw
  evidence) at the end of your report
- That regression #2 is actually a flaky test (passes in isolation,
  fails only in full suite) → say so explicitly with your reproduction
  command
- That migration 019 ran on `data/v9.db` but you don't know whether
  Cursor's check on `data/mems26_local.db` was the wrong DB → say
  which DB is canonical

---

## §6 · Acknowledgement footer

Confirm you read:
- [ ] Original implementation prompt (`CC_IMPLEMENT_P31_DAILY_RESET_2026-05-29.md`)
- [ ] Your own final report (`P31_DAILY_RESET_FINAL_2026-05-29.md`)
- [ ] This inquiry prompt
- [ ] Your own diffs for the 11 commits (`git show <hash>`)

Confirm you did NOT:
- [ ] Run any test
- [ ] Apply any migration
- [ ] Make any code change
- [ ] Make any commit
