# CC Report — DB Root Fix + sc_study v9.4.5 Diagnose | 2026-06-03

---

## A. DB Root Fix (4 Phases)

### Phase 1 — bars.py ORM writes -> safe_writer | DONE

| Endpoint | Before | After |
|----------|--------|-------|
| `/5min` | `db.add()` + `db.commit()` | `safe_executemany("INSERT OR REPLACE ...")` |
| `/volume_profile` | ORM update + `db.execute(text)` | `safe_execute("UPDATE ...")` + `safe_execute("INSERT OR REPLACE ...")` |
| `/imbalance` | `db.add(V9SystemSignal)` + `db.execute(text)` | `safe_execute("INSERT ...")` x2 |
| `/stacked_imbalance` | `db.add(V9SystemSignal)` + `db.execute(text)` | `safe_execute("INSERT ...")` x2 |
| `/cumulative_delta` | ORM row update + `db.execute(text)` | `safe_execute("UPDATE ...")` + `safe_execute("INSERT OR REPLACE ...")` |
| `/woodies` | `db.add(V9Bar30MinWoodies)` | `safe_executemany("INSERT ...")` |
| `/woodies_5min` | **raw `sqlite3.connect`** (!) | `safe_execute("INSERT OR REPLACE ...")` |
| `/tpo` | `db.add(V9TpoBar)` | `safe_executemany("INSERT ...")` |
| `bar_ingestion.py` | `SessionLocal()` + `db.add` + `db.commit` | `safe_execute("INSERT OR REPLACE ...")` |

- `/tick_reversal` + `/footprint` — disabled, left as-is per instructions.
- ORM `get_db()` kept for **read-only** queries (enrichment lookups).
- `safe_writer.py` DB_PATH default changed to runtime lookup (testable).
- 8 anti-tautological tests — all green.

**Gate:** `grep 'db\.(add|commit|flush)' bars.py` -> 4 hits, all in disabled endpoints.
**Regression:** 486 passed (8 new), same 3 pre-existing failures.
**Commit:** `d38444d`

---

### Phase 2 — mode=ro + zero raw-write connects | DONE

17 raw `sqlite3.connect(path)` read-only calls converted to `sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)`:

| File | Connects fixed |
|------|---------------|
| `footprint/routes.py` | 1 |
| `woodies/routes.py` | 1 |
| `admin_routes.py` | 1 |
| `reversal_routes.py` | 1 |
| `open_type_routes.py` | 1 |
| `bars_5min_history.py` | 1 |
| `day_type_v9_routes.py` | 3 |
| `shadow_routes.py` | 1 |
| `woodies_chart_routes.py` | 1 |
| `tpo_routes.py` | 5 |
| `historical_replay.py` | 1 |
| `session_boundary/manager.py` | 1 |
| `footprint_system.py` | 1 |
| `tpo_system.py` | 1 |
| `woodies_system.py` | 1 |
| `day_type/prev_day.py` | 2 |
| `day_type/api.py` | 2 |

Already safe (untouched): `key_levels_routes.py`, `build_status/*` (all had `mode=ro&immutable=1`).

**Gate:** `grep sqlite3.connect backend/v9/ | grep -v mode=ro|safe_writer|migrations|tests` -> 0 writers.
**Regression:** 486 passed, no new failures.
**Commit:** `edab3c0`

---

### Phase 3 — Journal isolation | NOT-DONE (with plan)

**Why not done:** v9_tpo_bars has 4 ORM readers (bars.py GET, tpo/api.py x2, websocket.py). v9_system_signals is a shared table (Woodies system_id=4, imbalance system_id=3). Moving requires dual-engine ORM routing — complex, high regression risk.

**Root cause already closed by Phase 1+2.** Journal isolation is defense-in-depth.

**Plan for future session (2-3 hours):**
1. `JOURNAL_DB_PATH = data/mems26_journals.db` + `journal_engine` in `session.py`
2. Move write paths for `cumulative_delta/imbalance/stacked_imbalance/volume_profile` to `safe_execute(..., db_path=JOURNAL_DB)`
3. v9_system_signals: keep in main DB (shared), add FIFO cap via scheduled DELETE
4. v9_tpo_bars: requires dedicated ORM session — deferred
5. Update `HistoricalReplay` + `BridgeInspector` for dual-DB reads

---

### Phase 4 — Rebuild + integrity soak | DONE

#### Pre-rebuild integrity (backend stopped):
```
v9_bars_5min_woodies:      CORRUPT — 100+ "Rowid out of order" errors
v9_bars_cumulative_delta:  CORRUPT — 100+ "Rowid out of order" errors
All other 42 tables:       ok
```

#### Rebuild:
```
v9_bars_5min_woodies:      13,631 -> 30,167 rows (hidden rows recovered)
v9_bars_cumulative_delta:  51,803 -> 492 rows (51,289 duplicates removed)
VACUUM + WAL checkpoint complete
```

#### Post-rebuild integrity (backend stopped):
```
PRAGMA integrity_check = ok
```

#### Load soak (10 minutes):
```
Endpoints: /5min, /cumulative_delta, /imbalance, /woodies_5min, /tpo
Duration:  600 seconds
Threads:   5 concurrent writers + live bridge pushes
Result:    21,726 pushes, 0 errors

  [  30s] pushes=  1,111  errors=0
  [  60s] pushes=  2,212  errors=0
  [ 120s] pushes=  4,420  errors=0
  [ 300s] pushes= 10,997  errors=0
  [ 570s] pushes= 20,658  errors=0
  FINAL:  pushes= 21,726  errors=0
```

#### Post-soak integrity (backend stopped):
```
PRAGMA wal_checkpoint(TRUNCATE) = (0, 0, 0)
PRAGMA integrity_check = ok
```

**Commit:** `9255bfa`

---

## B. sc_study v9.4.5-wc-fix Diagnose (read-only)

### Fact 1 — Which version is running?

| Check | Result | Evidence |
|-------|--------|----------|
| Export JSON version | `v9.4.5-wc-fix` | All 13 export JSONs show `v9.4.5-wc-fix` |
| Deployed source | v9.4.5 monolith | `~/SierraChart/ACS_Source/MES_AI_DataExport.cpp` header: `v9.4.5-wc-fix`, generated `2026-06-02 11:09:14` |
| DLL build | Success | DLL mtime `Jun 2 11:14:18` > source `Jun 2 11:09:14` |
| Repo vs deployed | Repo has split files (uncommitted), deployed has monolith | Content equivalent — same v9.4.5-wc-fix code |

**v9.4.5-wc-fix is LIVE and has been collecting data since June 2.**

---

### Fact 2 — SG mapping correct?

| Mapping | Old (v9.4.4) | New (v9.4.5) | Correct? |
|---------|-------------|-------------|----------|
| TrendUp | `(wc, 1, 0)` = SG1 = CCI value | `(wc, 1, 3)` = SG4 = TrendUp | **Yes** — verified in CHART12_STUDY_MAP |
| TrendDown | `(wc, 1, 1)` | `(wc, 1, 1)` | Unchanged, correct |
| TrendNeutral | `(wc, 1, 2)` | `(wc, 1, 2)` | Unchanged, correct |
| SWI | `(wc, 6, 5)` = ACSIL 5 = does not exist! | Local compute: `v9_calc_sidewinder()` | **Workaround** — correct because Study 6 has no numeric SWI subgraph |

**Contradiction resolved:** The v9_types.h comment says "SWI SG4" but this is **misleading** — SWI is not read from any subgraph. The code reads `(wc, 6, 0)` in `MES_AI_DataExport.cpp:614` but `v9_woodies_export.h:544` ignores that value and computes locally. The comment should say "SWI local-computed".

**Live SWI values confirm local compute is working:**
```
swi=38.49  cci14=-158.52  (reasonable CCI-derived value, not +200/-200 ref line)
swi=152.85 cci14=7.49
swi=-46.24 cci14=-38.75
```

**Other changes in v9.4.5 (v9_woodies_export.h, ~165 lines):**

| Change | Impact on S4 |
|--------|-------------|
| Bars from chart #12 direct (OHLC) | Eliminates frozen-tail from cross-chart mapping. **Affects S4.** |
| TrendUp SG4 fix | trend_state now correct (was reading CCI instead of TrendUp). **Affects S4.** |
| SWI local compute | SWI was previously reading non-existent SG5 = garbage. Now correct. **Affects S4.** |
| CCIDiff native from Woodies Panel | HUD field, does not affect S4 logic |
| mapIdx simplified | No behavior change when bars_from_wc=true |

---

### Decision Framework

**You are here: v9.4.5-wc-fix is LIVE + mappings are verified correct.**

| Option | When | Action |
|--------|------|--------|
| **Commit** | Mappings verified, data collecting since June 2 | `git add sc_study/ && git commit` — repo matches reality |
| Revert to v9.4.4 | Only if v9.4.5 data is suspect | `build_monolithic_cpp.sh --deploy` from v9.4.4 checkout + Remote Build — loses June 2-3 data integrity |
| Keep uncommitted | Not recommended | Repo lies about what's running; risk of accidental overwrite |

**Recommendation:** Commit. Fix the "SWI SG4" comment in v9_types.h to "SWI local-computed" during commit.

---

## Open Items

| Item | Owner | Notes |
|------|-------|-------|
| sc_study commit decision | Michael | This report provides the facts; decision is yours |
| CLAUDE.md DB Write-Safety section update | Michael | Should describe safe_writer-only arch (no get_db lock) |
| Phase 3 journal isolation | Future session | 2-3 hours, not a blocker |
| Backend restart | Michael | Currently stopped. `scripts/start_all.sh` or LaunchAgent bootstrap |
