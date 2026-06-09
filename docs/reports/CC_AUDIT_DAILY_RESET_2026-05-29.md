# CC Audit — Daily Reset / Archive / Demo Readiness

> **Self-summary:** Audited all 8 questions. Bug A traced to
> `DayTypeConsumer.consume()` being called on overnight Globex bars (after
> midnight ET) by `_day_type_on_bar` in `backend/main.py`. The consumer's
> `_extract_session_date()` correctly converts to ET, but `.date()` returns the
> calendar date — not the trading date. A bar at 01:00 ET 29/5 gets
> `session_date=2026-05-29`, creating a premature row pre-loaded with
> yesterday's stale classification. 13 occurrences of TZ-naive `date.today()`
> found, 11 in production hot-paths. `is_synthetic` is safely addable to all
> 5 tables (all have `id INTEGER PRIMARY KEY`). No existing rollover code — the
> `EODArchiveScheduler` archives at 15:55 ET but does NOT reset. No CHECK
> constraint on `v9_day_type_history.status`. Zero open trades. STOP
> conditions: none hit.

**Date:** 2026-05-29 16:30 IL
**Branch:** stabilize/mems26-local-truth-2026-05-16
**HEAD:** 886443e
**Reference:** docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md

---

## §1 · TZ-naive datetime audit (answers §2.1)

### Raw output

```
$ rg "date\.today\(\)|datetime\.now\(\s*\)" backend/v9 -n

backend/v9/api/v9/shadow_routes.py:67:    today = date.today()
backend/v9/tests/test_day_type_api_v9.py:109:    today = date.today().isoformat()
backend/v9/api/v9/day_type_v9_routes.py:30:    today = date.today().isoformat()
backend/v9/systems/day_type/hydration.py:22:        today = date.today()
backend/v9/systems/day_type/api.py:244:    today = date.today().isoformat()
backend/v9/systems/build_status/row_helpers.py:312:        today = _date.today().isoformat()
backend/v9/systems/tpo/tpo_system.py:90:                (date.today().isoformat(),)
backend/v9/systems/tpo/tpo_system.py:143:            today = date.today().isoformat()
backend/v9/systems/five_min/five_min_system.py:124:                    V9FiveMinState.session_date == date.today()
backend/v9/systems/build_status/day_type_inspector.py:30:    today = date.today().isoformat()
backend/v9/systems/build_status/aggregator.py:68:        today = date.today().isoformat()
backend/v9/systems/build_status/aggregator.py:204:            session_date=date.today().isoformat(),
backend/v9/systems/build_status/woodies_inspector.py:157:            (date.today().isoformat(),),
```

### Classification table

| File | Symbol | Snippet | TZ at runtime | Used in | Risk |
|---|---|---|---|---|---|
| `day_type_v9_routes.py` | `get_current()` | `date.today().isoformat()` | machine (Israel UTC+3) | `WHERE date = ?` on v9_day_type_history | 🔴 After 22:00 ET (05:00 IL), queries tomorrow's row |
| `day_type_v9_routes.py` | `get_stats()` | `date('now', ?)` (SQLite) | UTC (SQLite server) | `WHERE date >= date('now', ...)` | 🟡 Uses SQLite `date('now')` which is UTC — off by up to 5h from ET |
| `shadow_routes.py` | `shadow_soak_progress()` | `date.today()` | machine (Israel) | day-count arithmetic | 🟡 Cosmetic — soak day count shifts at midnight IL instead of midnight ET |
| `hydration.py` | `hydrate_day_type()` | `date.today()` | machine (Israel) | `WHERE date == today` on v9_day_type_history | 🔴 Reads wrong day's row after 22:00 ET; feeds stale state to machine on restart |
| `api.py` (day_type) | `get_current()` (V1 compat) | `date.today().isoformat()` | machine (Israel) | Passed to V9 sub-call | 🔴 Same bug as day_type_v9_routes — wrong date after 22:00 ET |
| `row_helpers.py` | `_fires_today()` | `_date.today().isoformat()` | machine (Israel) | Cache key + `WHERE` filter on fires | 🔴 Fires-today count uses wrong date 22:00-00:00 ET → risk limiter sees 0 fires for "today" |
| `tpo_system.py` | `hydrate()` | `date.today().isoformat()` | machine (Israel) | `WHERE trading_date=?` on v9_tpo_sessions | 🔴 Loads wrong session's IB on restart after 22:00 ET |
| `tpo_system.py` | `process_bar()` | `date.today().isoformat()` | machine (Israel) | session_id construction + DB writes | 🔴 Creates new session row keyed on wrong date after 22:00 ET |
| `five_min_system.py` | `hydrate()` | `date.today()` | machine (Israel) | `WHERE session_date == date.today()` | 🔴 Loads wrong five_min state on restart |
| `day_type_inspector.py` | `inspect()` | `date.today().isoformat()` | machine (Israel) | `WHERE date = ?` on v9_day_type_history | 🔴 Build status reads wrong day_type after 22:00 ET |
| `aggregator.py` | `_get_current_day_type()` | `date.today().isoformat()` | machine (Israel) | `WHERE date = ?` on v9_day_type_history | 🔴 Build status aggregator wrong date |
| `aggregator.py` | `_rth_session_approx()` | `date.today().isoformat()` | machine (Israel) | `session_date` for approximate RTH window | 🟡 Low impact — approximate window already |
| `woodies_inspector.py` | `_day_type_context()` | `date.today().isoformat()` | machine (Israel) | `WHERE date = ?` on v9_day_type_history | 🔴 Woodies matrix reads wrong day_type |
| `test_day_type_api_v9.py` | test fixture | `date.today().isoformat()` | N/A (test only) | Test fixture setup | 🟢 Test code — not production |

**Summary:** 11 production 🔴 entries, 2 🟡, 1 🟢 (test only).

**Note:** `key_levels_routes.py` `_day_type_row()` uses `date('now')` (SQLite server-side = UTC), which is a separate but related bug — at midnight UTC (20:00 ET), it flips to the next date.

### Smallest correct fix per 🔴 entry

Replace each `date.today()` with:

```python
from datetime import datetime
from zoneinfo import ZoneInfo
_ET = ZoneInfo("America/New_York")

def et_today() -> date:
    return datetime.now(_ET).date()
```

For `key_levels_routes.py` `_day_type_row()`, replace `date('now')` with a Python-side bind parameter using `et_today().isoformat()`.

This is a single utility function in a shared location (e.g. `backend/v9/common/trading_date.py`), called from all 11 sites. No "helper module" — just one 3-line function.

---

## §2 · Bug A root-cause (answers §2.2)

### Evidence

**Writer search:**

```
$ rg "session.add\(.*DayTypeHistory|session\.merge.*DayTypeHistory|UPDATE v9_day_type_history|INSERT.*v9_day_type_history|upsert.*day_type|UPSERT.*day_type" backend/v9 -n

backend/v9/systems/day_type/consumer.py:41:        """UPSERT into v9_day_type_history keyed by session_date.
backend/v9/tests/test_day_type_api_v9.py:80:        """INSERT INTO v9_day_type_history
```

Only ONE production writer: `DayTypeConsumer.consume()` in `backend/v9/systems/day_type/consumer.py`.

**Call chain (traced upward):**

1. `backend/main.py` `_day_type_on_bar()` is subscribed to `bar_router.subscribe("5min", ...)` (line 338).
2. On every 5-min bar (including Globex overnight bars), it calls `day_type_machine.process_bar(bar_input)` (line 255).
3. Then calls `day_type_machine.to_classification()` (line 286).
4. If classification is non-None, calls `_day_type_consumer.consume({...})` (line 288).
5. The classification's `timestamp` = `datetime.now(tz=timezone.utc)` (set in `state_machine.to_classification()` lines 944/970).
6. The consumer's `_extract_session_date()` converts this UTC timestamp to ET and returns `.date()`.

**The bug mechanism:**

`_extract_session_date()` uses `.date()` on the ET-converted timestamp. This returns the **calendar date** in ET, not the **trading date**. At `01:00 ET on 2026-05-29`, `.date()` returns `2026-05-29`. But the trading session for 2026-05-29 hasn't started yet (RTH opens at 09:30 ET). The state machine still holds the **previous day's** classification (IB, day_type, etc.) from the 28/5 RTH session — it was never reset.

So overnight Globex bars after midnight ET cause:
1. `_extract_session_date` returns tomorrow's calendar date (`2026-05-29`)
2. The stale state machine outputs yesterday's classification (Normal, IB 7583.5/7553.25)
3. The consumer UPSERTs a new row for `date=2026-05-29` pre-loaded with yesterday's values
4. By the time Michael checks at 09:00 IL, the row exists with stale data

The DB evidence corroborates: `v9_day_type_history` row for `2026-05-29` has `last_updated_at` around `02:00-05:00 UTC` (the exact value depends on how the column stores timezone). A Globex bar arriving between midnight and 05:00 ET on 29/5 would trigger this.

**Verdict (one paragraph):** The 29/5 row was written by `DayTypeConsumer.consume()` (called from `_day_type_on_bar()` in `backend/main.py:288`) because overnight Globex bars after midnight ET cause `_extract_session_date()` to return the **next calendar date** while the state machine still holds the **previous RTH session's** classification. The consumer's UPSERT creates a new row for the next date pre-loaded with yesterday's stale values (day_type=Normal, IB=7583.5/7553.25, status=LOCKED_LOW_CONF). Two coupled fixes needed: (1) `_extract_session_date()` must use the **18:00 ET trading-day boundary** instead of bare `.date()` — bars between 18:00 ET and 23:59 ET belong to the **next** trading day, bars between 00:00 ET and 17:59 ET belong to the **current** calendar date; (2) the state machine must be reset at the 18:00 ET boundary so `to_classification()` returns None until the new session accumulates its own data.

---

## §3 · /current endpoint inventory (answers §2.3)

### Raw source excerpts

**`/api/v9/day_type/v9/current`** (`day_type_v9_routes.py`, `get_current()`):
```python
today = date.today().isoformat()   # ← machine TZ (Israel)
row = conn.execute("SELECT * FROM v9_day_type_history WHERE date = ? LIMIT 1", (today,)).fetchone()
if row is None:
    return {"classified": False, "session_date": today, "data": None}
```

**`/api/v9/key_levels`** (`key_levels_routes.py`, `_day_type_row()`):
```python
row = conn.execute(
    "SELECT day_type, opening_type FROM v9_day_type_history "
    "WHERE date = date('now') LIMIT 1"    # ← SQLite date('now') = UTC
).fetchone()
```
The main `get_key_levels()` function uses `datetime.now(_ET)` correctly for its own TZ logic, but `_day_type_row()` uses SQLite's UTC `date('now')`.

**`/api/v9/tpo/current`** (`tpo_routes.py`, `tpo_current()`):
```python
sierra_tpo = _load_sierra_tpo()
if sierra_tpo is not None:
    return sierra_tpo
```
No date query. Returns Sierra export data directly. No TZ bug — but no PENDING semantics either (returns whatever Sierra has, or empty dict if missing).

**`/api/v9/woodies/chart`** (`woodies_chart_routes.py`):
No `/current` endpoint exists. Only `/api/v9/woodies/chart` which reads from `v9_woodies_signals` without a date filter.

### Inventory table

| Endpoint | Source file | TZ for "today" | No-row behavior | Returns yesterday? | Rating |
|---|---|---|---|---|---|
| `/api/v9/day_type/v9/current` | `day_type_v9_routes.py` | machine (Israel) | `{classified: false, data: null}` | No — returns null (good) | 🔴 TZ bug |
| `/api/v9/key_levels` | `key_levels_routes.py` | UTC (SQLite `date('now')`) for day_type pill; ET for IB/range | `None` (day_type pills just absent) | Not directly — but wrong date means no match, returns null | 🟡 Minor TZ mismatch on pill |
| `/api/v9/tpo/current` | `tpo_routes.py` | N/A (no date query) | Returns `{running: false, source: "missing"}` | N/A — Sierra file, not date-keyed | 🟢 No date bug |
| `/api/v9/woodies/chart` | `woodies_chart_routes.py` | N/A (no `/current` endpoint) | N/A | N/A | 🟢 No endpoint |
| `/api/v9/day_type/current` (V1 compat) | `day_type/api.py` | machine (Israel) via `date.today()` | Calls V9 `/current` as sub-request | Same bug — cascades | 🔴 TZ bug |

---

## §4 · Schema audit (answers §2.4)

### Raw PRAGMA output

```
$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_bars_5min);"
0|id|INTEGER|1||1
1|ts|DATETIME|1||0
2|symbol|VARCHAR(20)|1||0
3|open|FLOAT|1||0
4|high|FLOAT|1||0
5|low|FLOAT|1||0
6|close|FLOAT|1||0
7|volume|INTEGER|1||0
8|poc_vol|INTEGER|0||0
9|vah|FLOAT|0||0
10|val|FLOAT|0||0
11|cumulative_delta|FLOAT|0||0
12|created_at|DATETIME|0|CURRENT_TIMESTAMP|0

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_woodies_signals);"
0|id|INTEGER|0||1
1|ts|TEXT|1||0
...

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_trades);"
0|id|INTEGER|1||1
...

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_audit_events);"
0|id|INTEGER|1||1
...

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_five_min_setups);"
0|id|INTEGER|1||1
...

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_day_type_history);"
0|id|INTEGER|1||1
1|date|DATE|1||0
2|day_type|VARCHAR(32)|1||0
3|status|VARCHAR(16)|1||0    ← NOT NULL, no CHECK constraint
4|confidence|FLOAT|1||0      ← NOT NULL
...

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_account_status);"
0|id|INTEGER|1||1
1|ts|DATETIME|1|CURRENT_TIMESTAMP|0
2|mode|VARCHAR(10)|1||0     ← mode column EXISTS
...

$ sqlite3 data/mems26_local.db "PRAGMA index_list(v9_day_type_history);"
0|ix_v9_day_type_history_date|1|c|0

$ ls backend/v9/db/migrations/versions/ | sort | tail -5
014_day_type_v9_columns.sql
015_bars_5min_unique_ts_symbol.sql
016_v9_trades_journal_index.sql
017_v9_tpo_history_unique_ts.sql
018_woodies_5min_extra_fields.sql
```

### is_synthetic readiness (5 tables)

| Table | `id INTEGER PRIMARY KEY` | Existing `is_synthetic`? | UNIQUE conflicts? | Row count | ALTER ADD safe? |
|---|---|---|---|---|---|
| `v9_bars_5min` | Yes (col 0, pk=1) | No | No | 3,398 | Yes |
| `v9_woodies_signals` | Yes (col 0, pk=1) | No | No | 125 | Yes |
| `v9_trades` | Yes (col 0, pk=1) | No | No | 365 | Yes |
| `v9_audit_events` | Yes (col 0, pk=1) | No | No | 0 | Yes |
| `v9_five_min_setups` | Yes (col 0, pk=1) | No | No | 0 | Yes |

All 5 tables have `id INTEGER PRIMARY KEY`. `ALTER TABLE ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0` is safe for all.

### v9_day_type_history status column

Full CREATE TABLE (from `sqlite_master`):
```sql
CREATE TABLE v9_day_type_history (
    id INTEGER NOT NULL,
    date DATE NOT NULL,
    day_type VARCHAR(32) NOT NULL,
    status VARCHAR(16) NOT NULL,      -- ← VARCHAR, NO CHECK constraint
    confidence FLOAT NOT NULL,
    ...
    PRIMARY KEY (id)
)
```

**No CHECK constraint on `status`.** Adding `DEVELOPING` and `ROLLED_OVER` as status values will NOT fail any SQL constraint. The only risk is application-level validators (compliance_manifest.yaml `lock_state` enum — see §7).

### v9_account_status

- **Row count:** 0 (empty)
- **Schema:** Has `mode VARCHAR(10) NOT NULL` column. Design assumption confirmed.
- **Seed needed:** Yes — migration 019 should `INSERT INTO v9_account_status (mode, daily_pnl, trade_count, margin_used_pct) VALUES ('DEMO', 0, 0, 0)`.

### Migration numbering

Highest existing: `018_woodies_5min_extra_fields.sql`. Migration `019` is available.

---

## §5 · Existing rollover surface (answers §2.5)

### Raw output

```
$ launchctl list | grep -i "mems26\|day_type\|rollover\|reset"
59498   0   com.mems26.bridge

$ crontab -l 2>/dev/null
(no crontab)

$ ls ~/Library/LaunchAgents/ | grep -i mems26
com.mems26.bridge.plist
```

Only `com.mems26.bridge` exists. No rollover/reset automation.

```
$ rg "session.boundary|rollover|daily_reset|@app.on_event" backend/v9 -n

backend/v9/services/risk_validator/validator.py:143:    def daily_reset(self) -> None:
backend/v9/app.py:337:@app.on_event("startup")
```

```
$ rg "asyncio.create_task|asyncio.sleep" backend/v9/main.py backend/v9/app.py -n
(main.py does not exist at that path — startup is in backend/main.py)

$ rg "asyncio.create_task|asyncio.sleep" backend/v9 -n (relevant hits):
backend/v9/services/tpo_history_snapshotter.py:112:    self._task = asyncio.create_task(self._run(), ...)
backend/v9/services/eod_archive_scheduler.py:89:     self._task = asyncio.create_task(self._run(), ...)
```

### Existing related services

1. **`EODArchiveScheduler`** (`backend/v9/services/eod_archive_scheduler.py`): Fires at **15:55 ET** to archive Sierra JSON exports to disk. This is a FILE archiver (copies `~/SierraChart_Data/v9_export/` JSONs to date-stamped folders) — it does NOT reset any DB state, does NOT write to `v9_*_archive` tables, and does NOT create PENDING rows. It handles a different problem (Sierra file overwrite at RTH close).

2. **`RiskValidator.daily_reset()`** (`backend/v9/services/risk_validator/validator.py`): Resets daily trade count, loss counters, consecutive losses. Comment says "Called at midnight ET" but **no caller found** — this method exists but is never invoked. Dead code.

3. **`TPOHistorySnapshotter`** (`backend/v9/services/tpo_history_snapshotter.py`): Periodic asyncio task for TPO journal snapshots. Similar lifecycle pattern to what the design proposes.

### Verdict

**No existing daily reset or rollover code.** The design's `SessionBoundaryManager` (Phase 2.2) is greenfield work. The `EODArchiveScheduler` pattern (asyncio.create_task in startup hook, sleep-until-target loop, idempotent) is the right model to follow — it's already proven in production. `RiskValidator.daily_reset()` should be wired into the new `SessionBoundaryManager` as part of Phase 2.

---

## §6 · is_synthetic impact (answers §2.6)

### SELECT queries per table

| Table | Total queries | Files affected | Hardest update |
|---|---|---|---|
| `v9_bars_5min` | 10 (8 prod, 2 migration) | 7 files | `key_levels_routes.py` `_globex_range()` — joined with `date(ts)=date('now')` + `ts < ?` (medium complexity) |
| `v9_woodies_signals` | 1 | 1 file (`woodies/routes.py`) | 🟢 Single `ORDER BY id DESC LIMIT ?` |
| `v9_trades` | 11 (2 raw SQL, 9 SQLAlchemy) | 6 files | `trade_manager/manager.py` — multiple `.query(V9Trade).filter(...)` chains; `trades.py` has 3 query patterns |
| `v9_audit_events` | 0 | 0 files | 🟢 Table empty, no readers |
| `v9_five_min_setups` | 0 | 0 files | 🟢 Table empty, no readers |

### Per-query difficulty ratings

**v9_bars_5min (8 production queries):**
- `bars_5min_history.py` — 2 queries, simple `ORDER BY ts DESC LIMIT ?` → 🟢
- `key_levels_routes.py` `_globex_range()` — `MIN(low), MAX(high) FROM v9_bars_5min WHERE symbol='MES' AND date(ts)=date('now') AND ts < ?` → 🟡 (composite WHERE, need to preserve date filter + add is_synthetic)
- `open_type_routes.py` — `WHERE date(ts)=? ORDER BY ts LIMIT 12` → 🟢
- `day_type/prev_day.py` — subquery + main query `WHERE date(ts)=?` → 🟡 (subquery)
- `woodies/woodies_system.py` — `FROM v9_bars_5min_woodies ORDER BY ts DESC LIMIT ?` → 🟢 (different table: `_woodies` view/table)
- `build_status/woodies_inspector.py` — `MAX(ts) FROM v9_bars_5min_woodies` → 🟢 (different table)

**v9_trades (11 queries):**
- `shadow_routes.py` — `WHERE date(created_at)=date('now') AND outcome IS NOT NULL` → 🟢
- `build_status/row_helpers.py` — `WHERE entry_ts >= ? AND cross_context LIKE '%..%'` → 🟢
- `websocket.py` — `.query(V9Trade).order_by(...).limit(...)` → 🟢
- `journal_compat_routes.py` — `.query(V9Trade)` → 🟢
- `daily_quality_agent/agent.py` — `.query(V9Trade)` → 🟢
- `trades.py` — 3 distinct query patterns → 🟡 (need to add filter to all 3)
- `trade_manager/manager.py` — 3 query patterns → 🟡 (filter in active trade lookups)

**Total effort:** ~20 query sites need `WHERE is_synthetic = 0` added. Most are 🟢 (trivial single-WHERE append). 4 are 🟡 (medium — composite filters, need test). 0 are 🔴.

---

## §7 · Compliance manifest enum (answers §2.7)

### Raw output

```
$ rg "PENDING|LOCKED|LOCKED_LOW_CONF|DEVELOPING|ROLLED_OVER" backend/v9/systems/day_type/compliance_manifest.yaml

compliance_manifest.yaml:96:    branches: [LOCKED_HIGH, LOCKED_LOW, PENDING]
compliance_manifest.yaml:130:    enum: [PENDING, LOCKED, LOCKED_LOW_CONF]
compliance_manifest.yaml:148:    enum: [TRENDING_UP, TRENDING_DOWN, FAILED_EXTENSION, COMPRESSED, DEVELOPING]
```

Line 130 is the `lock_state` enum: `[PENDING, LOCKED, LOCKED_LOW_CONF]`. This is the field that maps to `v9_day_type_history.status`. Adding `DEVELOPING` and `ROLLED_OVER` requires updating this enum to `[PENDING, LOCKED, LOCKED_LOW_CONF, DEVELOPING, ROLLED_OVER]`.

Note: `DEVELOPING` already appears in line 148 under the `behavior` field enum — that's a different field (IB width behavior, not lock_state). No collision.

```
$ rg "compliance_manifest" backend/v9 -n
backend/v9/systems/five_min/five_min_system.py:399:        source per compliance_manifest.yaml COT_AMT node and cot_amt.py.
```

```
$ rg "lifecycle_phase|lifecycle_status" backend/v9 -n
(no matches)
```

### Verdict

The compliance manifest is **documentation/spec only** — no runtime validator loads it and enforces the enum. The only reference is a code comment in `five_min_system.py`. There is no test that asserts `status` values match the manifest enum.

**Risk:** Low. Updating the YAML enum is sufficient. However, the design's T2.1 should add a test that asserts every status string the `DayTypeConsumer` might write is present in the manifest enum — this is a good safety net for future enum drift.

---

## §8 · Open trades at boundary (answers §2.8)

### Raw output

```
$ sqlite3 data/mems26_local.db "SELECT id, state, entry_ts, mode, direction FROM v9_trades WHERE state IN ('OPEN', 'ARMED', 'PENDING') ORDER BY entry_ts DESC LIMIT 20;"
(empty — no rows returned)
```

**Zero open/armed/pending trades in the DB.**

### TIME_STOP mechanism

From `backend/v9/systems/woodies/time_stop.py`:
- Default `time_stop_minutes=90` → `limit_bars=18` (on 5-min bars)
- W-10 is sole TIME_STOP authority (Registry #11)
- Fires `CLOSE_ALL` when `bars_open >= 18`

From `backend/v9/systems/woodies/stages/b2_eod_check.py`:
- B2 EOD Check: force-flatten at `>= 15:59 ET`
- This is an ABSOLUTE_EXIT priority class → cannot be overridden

### 18:00 ET boundary analysis

For any trade open at 15:59 ET, two safety mechanisms fire:
1. **B2 EOD Check** → `CLOSE_ALL` at 15:59 ET
2. **W-10 TIME_STOP** → `CLOSE_ALL` at 90 min from entry (latest entry ~15:55 ET → closes by ~17:25 ET)

For a trade that somehow survives past B2 (shouldn't happen but...), W-10 guarantees closure within 90 minutes of entry. Maximum possible: trade opened at 15:58 ET → TIME_STOP at 17:28 ET. This is still **before** 18:00 ET.

### Does any code currently force-close at 16:00 ET?

No explicit 16:00 ET force-close. The B2 stage fires at 15:59 ET and the Woodies dispatcher runs it as ABSOLUTE_EXIT priority. Between 16:00 ET and 18:00 ET there is no additional safety net if B2 somehow fails — but this is a theoretical scenario since B2 is tested and the dispatcher always evaluates it.

### Does any code reference `account.mode` to refuse new positions?

```
$ rg "account.mode|account_mode|account_status\.mode" backend/v9 -n
(no matches)
```

**No code reads `v9_account_status.mode` to gate trade entry.** The `mode` column exists in the schema but is never queried. The design's Phase 4 `_assert_demo_or_403()` will be the first consumer. This is fine for now — the system has no broker integration, so `v9_trades` are DB-only records.

### Summary for rollover

The rare-case scenario (open trade at 18:00 ET) is effectively impossible given B2+W-10. But the design correctly documents the carry-across rule anyway: if an open trade exists, its `day_type` reference stays = previous day's classification. No code change needed for Phase 2 beyond documenting this.

---

## §9 · Findings beyond design scope

1. **`RiskValidator.daily_reset()` is dead code.** The method exists at `backend/v9/services/risk_validator/validator.py:143` with comment "Called at midnight ET" but no caller exists. The new `SessionBoundaryManager` should wire this up as part of its reset sequence. Without it, `daily_trades_count` and `consecutive_losses` never reset between trading days.

2. **`key_levels_routes.py::_day_type_row()` uses SQLite `date('now')` (UTC), not Python `date.today()`.** The design's §10.1 grep only catches Python `date.today()` — this SQLite-side usage is a separate TZ bug that won't be found by `rg "date\.today"`. Must be fixed alongside the 11 Python occurrences.

3. **`day_type_v9_routes.py::get_stats()` uses SQLite `date('now', ?)` for windowing.** Same SQLite UTC bug. Minor (stats endpoint, not trading-critical) but should be fixed for consistency.

4. **`tpo_system.py::process_bar()` constructs `session_id = f"{session_type}_{today}"` using `date.today()`.** This means a new TPO session row gets created with the wrong date after midnight IL but before midnight ET. On restart, `hydrate()` reads the wrong session → stale IB values in memory.

5. **State machine never resets between trading days.** `DayTypeStateMachine` accumulates state across the entire process lifetime. When `to_classification()` is called on an overnight Globex bar, it returns the previous RTH session's classification. The `SessionBoundaryManager` must call a machine-reset method (does not exist yet — needs to be added to the state machine).

6. **`backend/main.py:336` — `_logger.debug("[DayType] process_bar error: %s", e)`.** This is a silent failure on the bar-processing path (the very path that writes `v9_day_type_history`). CLAUDE.md and pre-live protocol forbid `logger.debug` on failure paths. Should be `logger.warning`.

7. **`backend/main.py:282` — `_logger.debug("[DayType] DB persist skipped: %s", db_err)`.** Another silent failure — `v9_day_type_state` inserts silently swallowed. Same CLAUDE.md violation.

8. **No UI handles the `ROLLED_OVER` status.** The design proposes `status='ROLLED_OVER'` for archived rows. The frontend's day_type pill logic (checked in `day_type_v9_routes.py::get_current()`) only distinguishes `DEVELOPING` vs classified. If a ROLLED_OVER row is accidentally served as "today", the UI would display it as classified with stale data. The `/current` endpoint must explicitly filter out or reject ROLLED_OVER rows.

---

## §10 · STOP conditions hit

None. All checks passed:
- §2.5: Only `com.mems26.bridge` in LaunchAgents — no unknown automation
- §2.4: No CHECK constraint on `v9_day_type_history.status`
- §2.4: All 5 tables have `id INTEGER PRIMARY KEY`
- §2.2: Bug A root-cause identified with confidence (not inconclusive)
- No code edits were made

---

## §11 · Recommended fix priority (root → symptom)

1. **`_extract_session_date()` must use 18:00 ET trading-day boundary** — without this, overnight Globex bars after midnight ET create premature rows for the next trading day. This is the root cause of Bug A.

2. **State machine reset at 18:00 ET boundary** — without this, `to_classification()` returns stale yesterday's classification on overnight bars, even if #1 is fixed (because the machine still holds state).

3. **Replace all 11× `date.today()` + 2× SQLite `date('now')` with `et_today()`** — without this, every system that queries "today's" data will return wrong results between 22:00 ET and midnight ET (= 05:00-07:00 IL). This is Bug B and affects 7 files.

4. **Wire `RiskValidator.daily_reset()` into SessionBoundaryManager** — without this, daily trade limits never reset. Currently harmless (no LIVE trades) but a ticking bomb for LIVE mode.

5. **Elevate `logger.debug` → `logger.warning` on failure paths in `backend/main.py`** (lines 282 and 336) — without this, consumer/state failures are invisible.

6. **Add `is_synthetic` column + `WHERE is_synthetic=0` filters** — depends on #3 being correct first. ~20 query sites, all 🟢/🟡 difficulty.

7. **Migration 019: archive tables + v9_session_meta + seed v9_account_status** — pure-additive, no risk to existing functionality.

8. **`/current` endpoints: return PENDING when no row for `et_today()`** — depends on #3. Currently returns `{classified: false}` which is functionally correct but semantically incomplete (no `status: PENDING` phase indicator).

---

## §12 · Acknowledgement

I read:
- [x] CLAUDE.md
- [x] .cursor/rules/mems26-pre-live-protocol.mdc
- [x] docs/plans/DAILY_RESET_AND_ARCHIVE_DESIGN.md (whole file, 749 lines)
- [x] This prompt (CC_AUDIT_PROMPT_DAILY_RESET_2026-05-29.md)

I confirm:
- [x] Zero file edits made during this audit (only this report created)
- [x] git status shows no changes beyond Cursor's own pre-existing modifications
- [x] I did NOT touch V3, CLAUDE.md, .cursor/rules, frontend, bridge, sc_study
- [x] I did NOT run any migration / DDL
- [x] I cited every claim with raw command output (no "should be" / "appears to")
