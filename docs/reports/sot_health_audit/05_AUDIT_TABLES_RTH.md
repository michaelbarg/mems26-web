# SOT_HEALTH Audit — 05 — audit_events / trade_management_log
Run: 2026-05-29 15:00 IL · 08:00 ET · market: OFF-HOURS (pre-RTH)
Verdict: BROKEN — tables exist but have ZERO writers in the codebase

## What was checked
Whether `v9_audit_events` (ts_ms) and `v9_trade_management_log` (ts) are legitimately empty off-hours or permanently broken. Checked DB content, codebase for write sites, and sot_health.py RTH logic.

## Evidence

### v9_audit_events (count · last_ts · rows in last RTH day)

| Metric | Value |
|--------|-------|
| Table exists | YES (schema: id, ts_ms BIGINT, event_type, correlation_id, source, price, payload, stream_id) |
| Total rows | **0** |
| Rows from May 28 RTH | **0** |
| Rows from any RTH ever | **0** |

### v9_trade_management_log (count · last_ts · rows in last RTH day)

| Metric | Value |
|--------|-------|
| Table exists | YES (schema: id, trade_id, ts DATETIME, action, value JSON, created_at) |
| Total rows | **0** |
| Rows from May 28 RTH | **0** |
| Rows from any RTH ever | **0** |

### Write path search

**Zero write sites found in the entire codebase** for either table:

```
rg -rn "v9_audit_events" backend/ --type py   → 0 hits (excluding test/schema)
rg -rn "v9_trade_management_log" backend/ --type py → 0 hits (excluding test/schema)
```

The SQLAlchemy models reference different table names:
- `backend/v9/db/models/audit.py` → `__tablename__ = "v9_ns"` (not `v9_audit_events`)
- `backend/v9/db/models/trade_log.py` → `__tablename__ = "v9_n_log"` (not `v9_trade_management_log`)

Neither `v9_ns` nor `v9_n_log` exist in the DB either. The models are orphaned — they define tables that were never created, and the actual DB tables (`v9_audit_events`, `v9_trade_management_log`) have no code that writes to them.

**These tables are schema-only artifacts.** They were created (likely via a migration or manual DDL) but never wired to any writer.

### Script RTH logic (file:line · how these tables are treated off-hours)

`sot_health.py:403-406` — both tables are listed under `TRADE_MANAGER` system:
```python
db_tables=[
    ("v9_trades", "entry_ts"),
    ("v9_trade_management_log", "ts"),
    ("v9_audit_events", "ts_ms"),
],
```

`probe_db_table()` (line 191-211): when `row is None` (zero rows), returns `Status.MISSING` with note "no rows". This bypasses `fresh_status()` entirely — **the RTH/off-hours threshold logic never fires** because there's no timestamp to compare.

The script's RTH-aware thresholds (`THRESH_OFF_FRESH = 6h`, `THRESH_OFF_STALE = 4d`) only apply when a row EXISTS but is old. Zero rows = unconditional 🔴 MISSING regardless of market hours.

## Finding

**NOT "empty off-hours" — permanently broken.** Both tables have:
- Zero rows historically (not just today)
- Zero write sites in the codebase
- Orphaned SQLAlchemy models pointing to wrong table names

The 🔴 MISSING is technically correct — the tables are genuinely empty. But the script shouldn't flag them as health failures because **no code was ever built to populate them**. They're aspirational schema, not broken data pipelines.

The distinction matters: `v9_trades` (also under TRADE_MANAGER in sot_health) IS populated and working. The audit/log tables are planned infrastructure that was never wired.

## Recommendation (for Cursor/Michael — DO NOT execute)

1. **Remove from sot_health.py** — delete `("v9_trade_management_log", "ts")` and `("v9_audit_events", "ts_ms")` from the TRADE_MANAGER `db_tables` list. They produce false 🔴 that will fail `--strict` every run regardless of market state.

2. **Keep `("v9_trades", "entry_ts")`** — this table IS populated and is the real health signal for TradeManager.

3. **Do NOT add RTH-awareness for these tables** — the problem isn't off-hours; it's that no code writes to them at all. RTH-awareness wouldn't help.

4. **Future:** when audit/log infrastructure is built, re-add the tables with a new flag like `optional=True` or `min_rows=0` so they don't block `--strict` until the writer is confirmed active.

5. **No DB cleanup needed** — tables are empty, nothing to clean.

## Open questions

1. **Were these tables planned for Pipeline 3?** The model file names (`audit.py`, `trade_log.py`) and the table schemas suggest they were designed for trade audit trail and lifecycle logging. If so, they should be tracked as "not yet implemented" rather than "broken."

2. **The model/table name mismatch** (`v9_ns` vs `v9_audit_events`, `v9_n_log` vs `v9_trade_management_log`) — if someone eventually wires the models, they'll create the wrong tables. The model `__tablename__` values need to match the existing DDL.
