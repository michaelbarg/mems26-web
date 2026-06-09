# CC Prompt — B-11: bridge_inspector `rowid` breaks on Postgres (false OFFLINE)

**Class:** PG-migration regression (SQLite-ism). Same family as B-8/B-9.
**Severity:** 🔴 false-alarm — dashboard lies (all streams `no_data`, Bridge
"OFFLINE") while the bridge pushes fine. Not a trading-logic change → no
strategic stop. Per `CC_HANDOFF_CONTRACT.md` + CLAUDE.md Rule 5.

## Symptom (verified Cowork, against code)
`/tmp/bridge.err.log` shows push #50, errors≈0, age=1s — bridge healthy. Yet
Build Status renders BLOCKED, all 8 streams `DEAD`/`no_data`, Bridge OFFLINE.

## Root cause (confirmed in code, 2 sites)
`backend/v9/systems/build_status/bridge_inspector.py`
- L82  `f"SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1"`
- L204 `f"SELECT {ts_col} FROM {table} ORDER BY rowid DESC LIMIT 1"`

`rowid` is a SQLite pseudo-column; on Postgres the query raises
`column "rowid" does not exist`. L82 is inside `_check_stream`'s `try` →
returns DEAD for every stream. L204 (`_get_single_age`) is inside a bare
`except: pass` (L210) → silently swallowed. Net: every stream marked dead,
Bridge OFFLINE — purely a read-path bug, system is actually live.

## Fix (smallest correct change)
Both sites already `SELECT {ts_col}` and order to get the newest row. Replace
the SQLite-only ordering with the timestamp column that's already selected:

```python
f"SELECT {ts_col} FROM {table} ORDER BY {ts_col} DESC LIMIT 1"
```

at both L82 and L204. `{ts_col}` is the per-stream config-driven timestamp
column, so ordering by it returns the freshest row on PG. No schema change.

## Regression test (anti-tautological — assert the detector, not a helper)
Add a test that fails on the OLD code and passes on the NEW:
- Point `read_one` at the real PG (or a PG fixture) for one stream table with
  ≥1 fresh row.
- Assert `_check_stream(...)["status"] != "DEAD"` AND `last_ts == MAX(ts)` from
  a direct `SELECT MAX({ts_col})`.
- Prove RED: temporarily revert to `ORDER BY rowid DESC` → test must error/raise
  (`column "rowid" does not exist`), confirming the test exercises the real
  query path, not a mock that hides it.

## Verification required back (Rule 5 — paste command + raw output, not "confirmed")
1. `grep -n "ORDER BY" backend/v9/systems/build_status/bridge_inspector.py`
   → both lines show `ORDER BY {ts_col} DESC`.
2. Run the new regression test — paste raw pytest output (RED on revert, GREEN
   on fix).
3. Live proof via the running backend: hit the Build Status endpoint and paste
   the JSON showing streams with real `age_sec` / non-DEAD status and Bridge
   not OFFLINE, alongside `/tmp/bridge.err.log` tail showing the bridge pushing.
4. Confirm `bad_count`-equivalent: 0 streams falsely DEAD when bridge age < threshold.

## NOT-DONE (mandatory section — list anything skipped)
- State explicitly if any of the 8 streams legitimately had no rows (genuine
  no_data) vs. the false-OFFLINE this fixes — don't mask a real dead stream.
- This fixes only the `rowid` SQLite-ism. The broader SQLite-isms scan (B-3 /
  §3: `str(ts)` dedup, `PRAGMA`, `datetime('now')`, string-assumption on ts)
  is a separate thread — do not fold it in here.

## Board updates after GO (CLAUDE.md Reporting Workflow)
- `STATUS_BOARD.md`: close B-11 with root + fix + raw verification (one dated line).
- `ROADMAP_TO_LIVE.html`: mark B-11 done, refresh "עודכן" line.
