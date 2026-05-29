# SOT_HEALTH Audit — 01 — S3 (Footprint) Coverage
Run: 2026-05-29 12:52 IL · 05:52 ET · market: OFF-HOURS (Globex overnight)
Verdict: CONFIRMED-GAP

## What was checked
S3 (Footprint) data pipeline: Sierra DLL exports → bridge streams → DB tables → API endpoints → firing status. Goal: determine if S3 has live data and what `(table, ts_col)` tuple is needed to add it to `sot_health.py`.

## Evidence

### Sierra JSON

| File | mtime | age (s) | size |
|------|-------|---------|------|
| `tick_reversal_15.json` | 09:51:42 | 2 | 5,531 B |
| `tick_reversal_12.json` | 09:51:42 | 2 | 7,609 B |
| `footprint.json` | 09:51:42 | 2 | 24,865 B |
| `footprint_5min.json` | — | — | NOT FOUND |

All 3 files are live (2s old). DLL is actively writing.

### DB tables

| Table | ts_col | rowcount | last_ts | age | exists? |
|-------|--------|----------|---------|-----|---------|
| `v9_bars_footprint` | `ts` (DATETIME) | 615,269 | `2026-05-29 06:51:39` | ~2min | YES |
| `v9_bars_tick_reversal` | `ts` (DATETIME) | 15,949,030 | `2026-05-29 11:52:09` | ~0s | YES |
| `v9_footprint_signals` | — | — | — | — | **NOT FOUND** (no table) |
| `v9_footprint_setups` | `ts` (TEXT) | 0 | — | — | YES (empty) |
| `v9_footprint_journal` | (exists) | — | — | — | YES (not queried) |
| `v9_footprint_markers` | (exists) | — | — | — | YES (not queried) |

Notes:
- `v9_bars_tick_reversal.ts` contains the future-ts bug that `sot_health.py` already detected (`2026-05-29 11:52:09` at wall-clock 05:52 ET = +6h, consistent with the Chicago TS over-correction prior to the America/New_York fix for the 5min stream — tick_reversal stream may still use the old TZ).
- `v9_footprint_signals` does not exist as a table. The inspector prompt assumed it did.
- `v9_footprint_setups` exists but has 0 rows.

### API

| Endpoint | HTTP | Notes |
|----------|------|-------|
| `/api/v9/bars/tick_reversal?tick_count=15` | 422 | Requires additional params (not a simple GET) |
| `/api/v9/bars/tick_reversal?tick_count=12` | 422 | Same |
| `/api/v9/footprint/current` | 200 | Returns live footprint state |

### S3 firing now?

**YES — actively firing.** `v9_trades` has recent S3 shadow trades:

| id | mode | direction | state | entry_ts |
|----|------|-----------|-------|----------|
| 323 | shadow | LONG | PARTIAL | 2026-05-29 06:50:55 |
| 322 | shadow | LONG | PARTIAL | 2026-05-29 06:50:51 |
| 321 | shadow | LONG | PARTIAL | 2026-05-29 06:50:51 |
| 320 | shadow | LONG | PARTIAL | 2026-05-29 06:50:43 |
| 319 | shadow | LONG | PARTIAL | 2026-05-29 06:50:39 |

5 shadow trades in 16 seconds — S3 is actively firing into the gateway.

## Finding

S3 has a complete live data pipeline:
- **DLL** writes 3 JSON files every ~2s
- **Bridge** pushes via `FootprintStream`, `TickReversal15Stream`, `TickReversal12Stream`
- **DB** has 615K footprint bars + 15.9M tick_reversal bars
- **Backend** `FootprintSystem` is hydrated, subscribed to `["tick_reversal_15", "tick_reversal_12"]` via BarRouter (`main.py:96-102`)
- **Gateway** is receiving shadow trades from S3 (`firing_system=3`)

**S3 is NOT in `sot_health.py`'s system map** despite having more data volume than any other system (15.9M rows in tick_reversal alone).

The ts_col for each table:
- `v9_bars_footprint` → `ts` (DATETIME)
- `v9_bars_tick_reversal` → `ts` (DATETIME) — **WARNING: this table has future-ts bug from Chicago TZ; the America/New_York fix may not have been applied to the tick_reversal stream**

`v9_footprint_signals` does NOT exist — the prompt's reference to it was incorrect. The actual signals table is `v9_footprint_setups` (currently empty — S3 fires directly to gateway without persisting setups to a signals table).

## Recommendation (for Cursor/Michael — DO NOT execute)

Add to `sot_health.py` system map:
```python
("S3_footprint_bars", "v9_bars_footprint", "ts"),
("S3_tick_reversal", "v9_bars_tick_reversal", "ts"),
```

Before adding: verify that the `v9_bars_tick_reversal.ts` future-ts bug is resolved by the America/New_York TZ fix. If the tick_reversal bridge stream still uses the old Chicago TZ, the freshness check will report false-stale or false-fresh depending on direction.

## Open questions

1. **tick_reversal ts still shifted?** The last row shows `11:52:09` at wall-clock ~05:52 ET — a +6h shift. The America/New_York fix was applied to `base_stream.py` (all streams), but the tick_reversal data may have been written before the fix. Need to verify with fresh data after a bridge restart.

2. **v9_footprint_signals does not exist.** S3 fires to gateway directly. Should `sot_health.py` monitor `v9_footprint_setups` (currently empty) or `v9_trades WHERE firing_system=3`?

3. **S3 fires very frequently** (5 trades in 16s during overnight). Is this expected behavior or a dedup gap in footprint_system? Not in scope for this audit but worth flagging.

4. **tick_reversal API returns 422** — may need `symbol` or other required params. The sot_health script may need to use DB queries instead of API for tick_reversal freshness.
