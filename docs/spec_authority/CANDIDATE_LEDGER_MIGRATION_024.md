# Candidate Ledger — Migration 024 design

**Status:** design only. Do not run against live DB until Michael go + snapshot.
**Follows:** `CANDIDATE_LEDGER_CONTRACT.md` §7 · live persist map 2026-08-24.
**Style:** same as `022_day_type_state_n1_columns.py` / `023_pnl_sierra_column.py`
(standalone idempotent `migrate()`, not Alembic).

## 1. Goal

Stamp a stable `candidate_id` onto the two existing detection tables so JSONL
events can join to S2/S4 detection rows. Observability only. Historical rows
stay NULL.

No third table. No backfill. No synthesized IDs for old rows.

## 2. Preconditions

1. `scripts/mems26_snapshot.sh "pre-candidate-ledger-024"`
2. `DATABASE_URL` is local-only (`localhost` / `127.0.0.1` / unix socket).
   Refuse remote `host` / `hostaddr` / `PGHOST` / `PGHOSTADDR` / `PGSERVICE`
   the same way `backend/v9/replay/data_source.py` does.
3. Dry-run print of `ALTER` statements before execute.
4. Bridge/backend may keep running: additive nullable columns + `SHARE UPDATE EXCLUSIVE` on PG `ALTER … ADD COLUMN` without default rewrite. Still do this outside the forbidden restart window if a backend restart is needed for the ORM.

## 3. Columns

### `v9_five_min_setups`

| Column | Type | Null | Notes |
|--------|------|------|-------|
| `candidate_id` | `VARCHAR(64)` | yes | hex SHA256 of identity JSON; see contract §3 |
| `detected_at` | `TIMESTAMPTZ` | yes | wall clock when DETECTED was written |
| `confirmed_at` | `TIMESTAMPTZ` | yes | emit/gateway time if the candidate left DETECTED |
| `source_pid` | `INTEGER` | yes | `os.getpid()` |
| `source_commit` | `VARCHAR(40)` | yes | git HEAD at process boot |
| `policy_id` | `VARCHAR(64)` | yes | detector/policy tag, not a verdict |

Indexes (create `IF NOT EXISTS`):

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_v9_five_min_setups_candidate_id
  ON v9_five_min_setups (candidate_id)
  WHERE candidate_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_v9_five_min_setups_detected_pat_dir
  ON v9_five_min_setups (detected_at, pattern, direction);
```

ORM (`backend/v9/db/models/five_min_setups.py`): add the six columns **and**
`is_synthetic = Column(Integer, nullable=False, default=0)` which 019 already
put on the table but the model still omits. Do not backfill `is_synthetic`.

### `v9_woodies_signals`

Same six nullable columns. Same unique partial index on `candidate_id`.
No `(detected_at, pattern, direction)` index — pattern lives in `signal_type`.

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_v9_woodies_signals_candidate_id
  ON v9_woodies_signals (candidate_id)
  WHERE candidate_id IS NOT NULL;
```

Do **not** alter `v9_woodies_signals_archive`.
`session_boundary/manager.py:198-210` copies an explicit column list, so extra
live columns are ignored and the 03.08 `SELECT *` breakage cannot recur.

`bar_id` is currently always `None` at insert (`woodies_system.py:1371-1400`).
Do not “fix” that in 024 — out of scope.

## 4. What 024 must not do

- No `v9_candidate_events` table.
- No `NOT NULL`, no `DEFAULT` that rewrites the table.
- No UPDATE of existing rows.
- No drop/rename.
- No change to `v9_trades`.
- No JSONL rewrite.
- No flag enable.

## 5. Implementation sketch

File: `backend/v9/db/migrations/versions/024_candidate_ledger_columns.py`

```python
COLUMNS = [
    ("candidate_id", "VARCHAR(64)"),
    ("detected_at", "TIMESTAMPTZ"),
    ("confirmed_at", "TIMESTAMPTZ"),
    ("source_pid", "INTEGER"),
    ("source_commit", "VARCHAR(40)"),
    ("policy_id", "VARCHAR(64)"),
]
TABLES = ("v9_five_min_setups", "v9_woodies_signals")
```

For each table/column: `ALTER TABLE … ADD COLUMN …` and catch
duplicate-column. Then create the indexes. Print ADDED vs already-exists.

Local DSN guard before connect. `autocommit = True`.

Run:

```bash
DATABASE_URL=postgresql://localhost/mems26 \
  python3 backend/v9/db/migrations/versions/024_candidate_ledger_columns.py
```

## 6. Verification (Rule 5)

After dry-run + apply:

```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name IN ('v9_five_min_setups', 'v9_woodies_signals')
  AND column_name IN ('candidate_id','detected_at','confirmed_at',
                      'source_pid','source_commit','policy_id')
ORDER BY table_name, column_name;

SELECT indexname FROM pg_indexes
WHERE tablename IN ('v9_five_min_setups','v9_woodies_signals')
  AND indexname LIKE '%candidate_id%';

SELECT count(*) FILTER (WHERE candidate_id IS NOT NULL)
FROM v9_five_min_setups;   -- must be 0 until the writer is ON

SELECT count(*) FILTER (WHERE candidate_id IS NOT NULL)
FROM v9_woodies_signals;   -- must be 0 until the writer is ON
```

Rerun the script: every column/index prints skip. That is acceptance test 9.

## 7. Rollback

Forward-only. If it must be undone: `DROP INDEX` + `ALTER TABLE DROP COLUMN`
in a new 025 after snapshot + Michael go. Do not hide a drop inside 024.

## 8. Flag

`CANDIDATE_LEDGER_V1` default `0`. Add to `docs/FLAG_REGISTRY.yaml` category
`misc` when the writer lands. The migration itself does not read the flag.
The writer no-ops when unset. Enabling writes is observability-only and
does not require a trading-risk ruling; it does require restart outside the
forbidden window and independent review of one live candidate lifecycle.
