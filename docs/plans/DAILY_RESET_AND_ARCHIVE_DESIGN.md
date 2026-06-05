# Daily Reset, Archive, and Demo-Readiness — Design Document

**Status:** DRAFT — pending Michael approval before Phase 2
**Author:** Cursor agent
**Date:** 2026-05-29
**Related:** `docs/reference/SOT_HEALTH.md`, `scripts/sot_health.py`

---

## §0 · TL;DR

We need three coupled capabilities, all triggered at the **18:00 ET Globex
boundary**:

1. **Daily Reset** — every system starts each new trading day from a clean
   `PENDING` state. No values from the previous day leak forward.
2. **Archive** — yesterday's state (day_type, TPO, Woodies signals, trades,
   build_status, raw bars) is snapshot to immutable `*_archive` tables so we
   can retrospectively answer "what did the system see on date X".
3. **Demo Readiness Panel** — Status Board surface that aggregates SOT_HEALTH
   + bridge + backend + day_type-appropriate-for-time + DEMO mode, with three
   buttons to test the full chain (single-bar / pattern-test / replay).

Michael's decisions on 2026-05-29:

- **Boundary = 18:00 ET** (Globex open of next trading day)
- **Archive scope = all_state + raw bars** (full replay capability)
- **Test chain = all three** (single-bar, pattern-test, full RTH replay)
- **DEMO/LIVE safety = rely on existing `v9_account_status`** (verify the
  existing mechanism is enforced; do not introduce a new ENV var)
- **Phase 1 today = diagnose + design + pending fix** (Cursor agent)

---

## §1 · Current state — what we have today

### §1.1 The bug Michael saw on 2026-05-29 09:00 IL

**Symptom:** Pre-RTH on Friday 29/5, dashboard showed
`day_type=Normal, ib_h=7583.5, ib_l=7553.25, ib_locked=true`. These are
**yesterday's values** (28/5 RTH session).

**Raw evidence:**
```
sqlite3> SELECT date, day_type, status, ib_high, ib_low, last_updated_at
         FROM v9_day_type_history WHERE date >= '2026-05-26' ORDER BY date DESC;

2026-05-29  Normal      LOCKED_LOW_CONF  7583.5  7553.25  2026-05-29 05:00:03  ← wrong
2026-05-28  Normal      LOCKED_LOW_CONF  7583.5  7553.25  2026-05-28 23:55:04
2026-05-27  Trend_Normal LOCKED_LOW_CONF ...
```

The 29/5 row has `last_updated_at = 05:00:03 IL = 02:00 UTC = 22:00 ET 28/5`.
Some code path created a row keyed on `date=2026-05-29` while ET wall-clock
was still 22:00 ET on 28/5. **There is no Globex boundary trigger and no
reset mechanism.**

### §1.2 Two confirmed root-causes

**Bug A — `consumer._extract_session_date` is correct, so a different
write-path is responsible.** The DayTypeConsumer correctly converts
timestamps to ET, but the row exists with the wrong date. Phase 2 must trace
the actual call-site (likely `state_machine.to_classification()` is invoked
by an overnight loop or by `hydration.py`).

**Bug B — `/api/v9/day_type/v9/current::date.today().isoformat()`** uses the
machine's TZ (Israel = UTC+3) instead of ET. After 22:00 ET (= 05:00 IL),
this endpoint queries `WHERE date = tomorrow_in_ET`, finding the
prematurely-written row.

```30:30:backend/v9/api/v9/day_type_v9_routes.py
    today = date.today().isoformat()
```

**Pending fix applied 2026-05-29:**
- Updated row 29/5 to `day_type='UNKNOWN', status='PENDING',
  ib_width_class='DEVELOPING', ib_*=NULL`.
- Backup at `/tmp/v9_day_type_29may_backup.txt`.
- API now returns `classified=false, developing=true` — UI should show
  "טרום־מסחר" / "מתפתח".

### §1.3 What the codebase already has

| Surface | Exists? | Used as |
|---|---|---|
| `v9_day_type_history` | ✅ | UPSERT one-row-per-date — serves both "today" and "history" |
| `v9_tpo_history` | ✅ | Append-only TPO journal |
| `v9_trades` | ✅ | Trades with `state` (OPEN/CLOSED/...) — closed trades stay |
| `v9_audit_events` | ✅ | Audit log (currently empty) |
| `v9_build_status_*` | ❌ | Build status is **computed on every `/pattern-status` call** — never persisted |
| Any `*_archive` table | ❌ | None exist |
| Snapshotter / rollover task | ❌ | No 16:00 ET / 18:00 ET trigger |
| `v9_account_status` | ✅ | Has `mode` field — Phase 4 must verify it's enforced |
| Pre-RTH "PENDING" semantics | ❌ | API returns last UPSERT regardless of time-of-day |

### §1.4 What's missing

Five gaps:

1. **No session-boundary detection.** Backend has no concept of "trading day
   ended, reset state."
2. **No archive layer.** Yesterday's data only survives if it happens to be
   in a journal table; build_status, signals, fires history are lost.
3. **No PENDING semantics.** API returns yesterday's classification verbatim
   when today hasn't classified yet.
4. **No demo-readiness aggregator.** Status Board doesn't tell you "the chain
   is ready, you can flip to demo."
5. **No end-to-end chain test.** No way to verify `bridge → bar → S2 →
   trade → DB → UI` works without actually waiting for a real fire.

---

## §2 · Design — the target architecture

### §2.1 Boundary semantics (Michael's decision: 18:00 ET)

```text
                       ┌─────────── trading day N ───────────┐
─── Globex N-1 ──────●──── 09:30 ET ───── 16:00 ET ─────────●──── Globex N+1 ────
   (yesterday)       │          RTH today                   │       (tomorrow)
                  18:00 ET                                18:00 ET
                  ═════                                    ═════
                  ROLLOVER N-1→N                           ROLLOVER N→N+1
```

A "trading day" = `[18:00 ET previous day, 18:00 ET this day)`.

**Rollover at 18:00 ET = atomic transaction:**
1. Snapshot finalized state of day N-1 → `*_archive` tables.
2. Mark day N-1 row → `status='ROLLED_OVER'` (immutable thereafter).
3. INSERT row for day N → `status='PENDING', day_type='UNKNOWN'`.
4. Reset in-memory state of S1, S2, S4, Trade Manager (clear caches,
   buffers, fire-records — but NOT open trades).
5. Open trades carry across the boundary. Their day_type for risk decisions
   is `previous_day` until the new classification arrives.

### §2.2 Hybrid trigger (idempotent)

```python
# Triggered at 18:00 ET (clock-driven via launchd or backend cron)
def session_rollover_at_18et():
    rollover_if_needed(now_et=datetime.now(ET))

# Triggered on first 5-min bar with ts >= 18:00 ET (data-driven fallback)
def on_bar(bar):
    rollover_if_needed(now_et=bar.ts.astimezone(ET))
    process_bar(bar)

def rollover_if_needed(now_et):
    today = trading_day_for(now_et)  # 18:00 ET defines boundary
    if last_rollover_date == today:
        return  # already rolled — idempotent
    with db.transaction():
        snapshot_to_archive(yesterday=last_rollover_date)
        insert_pending_row(today)
        reset_in_memory_state()
        last_rollover_date = today
```

The `last_rollover_date` is persisted in `v9_session_meta` (new tiny table).
Both triggers are safe to call repeatedly.

### §2.3 PENDING / DEVELOPING / CLASSIFIED state machine

Every "current" endpoint follows the same response shape:

```python
def get_current(system: str, today_et: date) -> dict:
    row = query(f"SELECT * FROM v9_{system}_history WHERE date={today_et}")
    if row is None:
        return {"status": "PENDING", "data": None, "phase": "before_rollover"}
    if row.status == "PENDING":
        return {"status": "PENDING", "data": None, "phase": "pre_RTH"}
    if row.status == "DEVELOPING":
        return {"status": "DEVELOPING", "data": partial(row), "phase": "RTH_active"}
    if row.status == "CLASSIFIED" or row.status == "LOCKED":
        return {"status": "CLASSIFIED", "data": full(row), "phase": "complete"}
    if row.status == "ROLLED_OVER":
        return {"status": "PENDING", "data": None, "phase": "stale_row"}  # treat as no row
```

Frontend renders:
- `PENDING + before_rollover/pre_RTH` → "טרום־מסחר · אין סיווג עדיין"
- `DEVELOPING` → "מתפתח (IB עדיין נבנה)"
- `CLASSIFIED` → today's day_type pill

### §2.4 Archive schema

```sql
-- Migration 019_session_archive.sql

-- Tracks rollover boundaries (one row per trading day)
CREATE TABLE v9_session_meta (
    trading_date DATE PRIMARY KEY,
    rollover_at  DATETIME NOT NULL,        -- when the boundary fired (UTC)
    rollover_kind TEXT NOT NULL CHECK (
        rollover_kind IN ('clock', 'first_bar', 'manual')
    ),
    backend_pid INTEGER,
    notes TEXT
);

-- Archive: day_type
CREATE TABLE v9_day_type_archive (
    trading_date DATE PRIMARY KEY,
    snapshot_data JSON NOT NULL,            -- full row at snapshot time
    snapshot_at DATETIME NOT NULL,
    rolled_over_at DATETIME,
    final_status TEXT NOT NULL              -- LOCKED / LOCKED_LOW_CONF / NO_DATA
);

-- Archive: TPO / IB
CREATE TABLE v9_tpo_sessions_archive (
    id INTEGER PRIMARY KEY,
    trading_date DATE NOT NULL,
    session_type TEXT NOT NULL,             -- CASH / GLOBEX
    snapshot_data JSON NOT NULL,
    snapshot_at DATETIME NOT NULL,
    UNIQUE(trading_date, session_type)
);

-- Archive: Woodies signals (compressed by pattern × direction)
CREATE TABLE v9_woodies_signals_archive (
    id INTEGER PRIMARY KEY,
    trading_date DATE NOT NULL,
    pattern TEXT NOT NULL,
    direction TEXT NOT NULL,
    fires_count INTEGER NOT NULL,
    blocks_count INTEGER NOT NULL,
    sample_data JSON,                       -- first 5 fires with full details
    snapshot_at DATETIME NOT NULL
);

-- Archive: build_status snapshot (full pattern-status response)
CREATE TABLE v9_build_status_archive (
    trading_date DATE PRIMARY KEY,
    snapshot_data JSON NOT NULL,            -- full /pattern-status response
    snapshot_at DATETIME NOT NULL
);

-- Raw bars are already in v9_bars_5min — no archive copy needed.
-- We add a view for replay:
CREATE VIEW v9_bars_5min_for_date AS
    SELECT * FROM v9_bars_5min
    WHERE strftime('%Y-%m-%d', ts, '-18 hours') = ?;  -- placeholder for date
```

**Storage estimate:** ~5 KB/day for snapshots × 365 days = ~2 MB/year.
Negligible. After 1 year, optional rollup to S3/external.

### §2.5 Demo Readiness Panel — backend

New endpoint:

```python
GET /api/v9/demo_readiness  →  {
    "overall": "READY" | "PARTIAL" | "BLOCKED",
    "checks": [
        {"id": "sot_health",         "status": "READY", "detail": "all green"},
        {"id": "bridge_alive",       "status": "READY", "detail": "heartbeat 12s ago"},
        {"id": "backend_alive",      "status": "READY", "detail": "200 OK"},
        {"id": "db_writable",        "status": "READY", "detail": "v9_audit_events insert ok"},
        {"id": "day_type_appropriate", "status": "READY",
         "detail": "PENDING (pre-RTH) — expected for current ET time"},
        {"id": "account_mode",       "status": "READY", "detail": "DEMO"},
        {"id": "open_trades",        "status": "READY", "detail": "0 open"},
        {"id": "last_archive",       "status": "READY", "detail": "yesterday archived 18:00 ET"}
    ],
    "trade_chain_test_available": true,
    "last_test_at": "2026-05-28T20:15:00Z",
    "last_test_result": "PASS"
}
```

Two write endpoints for chain testing:

```python
POST /api/v9/demo_readiness/test_chain  →  {
    "request": {
        "kind": "single_bar" | "pattern_test" | "replay_yesterday",
        "speed_multiplier": 10  # for replay
    },
    "trace": [
        {"step": "bridge_post",      "status": "OK", "elapsed_ms": 12},
        {"step": "5min_persist",     "status": "OK", "rows_written": 1},
        {"step": "S2_detector",      "status": "OK", "patterns_evaluated": 5},
        {"step": "S4_detector",      "status": "OK", "patterns_evaluated": 9},
        {"step": "trade_open",       "status": "OK", "trade_id": 9999},
        {"step": "trade_monitor",    "status": "OK", "ticks": 18},
        {"step": "trade_close",      "status": "OK", "reason": "TIME_STOP", "pnl": +12.50},
        {"step": "ui_websocket",     "status": "OK", "frame_received": true}
    ],
    "duration_ms": 215
}
```

Test chains MUST refuse to execute if `account_mode != "DEMO"`. Hardcoded.

### §2.6 Demo Readiness Panel — frontend

```text
┌────────────────────────────────────────────────────────────┐
│ DEMO READINESS — ALL SYSTEMS                       🟢 READY│
├────────────────────────────────────────────────────────────┤
│ ✅ SOT Health           (all 7 systems FRESH)              │
│ ✅ Bridge alive         (heartbeat 12s ago)                │
│ ✅ Backend alive                                           │
│ ✅ DB writable                                             │
│ ✅ Day type             PENDING — expected (pre-RTH 02:51)│
│ ✅ Account mode         DEMO                               │
│ ✅ Open trades          0                                  │
│ ✅ Last archive         yesterday 18:00 ET                 │
├────────────────────────────────────────────────────────────┤
│ [ Send single bar ]  [ Test pattern fire ]  [ Replay 10x ] │
│                                                            │
│ Last test: 2026-05-28 20:15 ET  · PASS  · 215ms           │
└────────────────────────────────────────────────────────────┘
```

Below this card, an `ArchivedDaysStrip`:

```text
Past trading days  ◀ 23 24 25 26 27 28 ▶
                                     ▲
                                  click → modal with full state of 28/5
```

---

## §3 · Phase plan (the 5-phase / 13-task breakdown)

### Phase 1 — Diagnose + Design + Pending Fix (Cursor — TODAY)

| Task | Owner | Status |
|------|-------|--------|
| T1.1 Diagnose: who wrote the 29/5 row at 22:00 ET 28/5? | Cursor | 🟡 Partial — found `date.today()` ET bug; full call-path TBD by CC |
| T1.2 Audit: every "current" endpoint TZ + fallback handling | Cursor | 🟡 Partial — `/day_type/v9/current` confirmed buggy |
| T1.3 Inventory: existing archive surfaces | Cursor | ✅ Done — only `v9_day_type_history` and `v9_tpo_history` exist |
| T1.4 Pending fix: reset 29/5 row to PENDING/DEVELOPING | Cursor | ✅ Done — backup at `/tmp/v9_day_type_29may_backup.txt` |
| T1.5 Design doc (this file) | Cursor | ✅ This file |

### Phase 2 — Backend: Daily Reset + Archive (CC — after Michael approves §2)

| Task | Owner | Deliverable |
|------|-------|-------------|
| T2.1 Migration `019_session_archive.sql` | CC | 5 archive tables + `v9_session_meta` + view |
| T2.2 `SessionBoundaryManager` service | CC | New module `backend/v9/services/session_boundary/manager.py` with hybrid 18:00 ET clock + first-bar fallback |
| T2.3 Snapshotter | CC | Module that writes `*_archive` rows during rollover |
| T2.4 Fix `/current` endpoints — PENDING/DEVELOPING semantics | CC | `day_type_v9_routes`, `key_levels_routes`, `tpo_routes`, `woodies_chart_routes` all return PENDING when no `today` row |
| T2.5 Fix Bug B — `date.today()` → ET-aware | CC | Replace 4 occurrences I found in audit; pre-flight grep for more |
| T2.6 Regression tests | CC | 4 tests minimum: (a) 22:00 ET 28/5 — no row for 29/5 created; (b) 18:00 ET trigger — archive populated; (c) idempotent rollover; (d) PENDING when no row |
| T2.7 Manual UAT — wait for 18:00 ET, verify rollover live | CC | Pasted output of DB before/after, archive row contents, in-memory state reset |

### Phase 3 — Backend: Archive Endpoints (CC — after Phase 2)

| Task | Owner | Deliverable |
|------|-------|-------------|
| T3.1 `GET /api/v9/archive/days?from=&to=` | CC | List of past trading days + summary per day |
| T3.2 `GET /api/v9/archive/day/:date` | CC | Full state of a past day (joins all `*_archive` tables) |
| T3.3 Tests | CC | 2 tests: (a) yesterday accessible; (b) day with no data returns 404 not crash |

### Phase 4 — Frontend: Demo Readiness + Archive Strip (CC — after Phase 3)

| Task | Owner | Deliverable |
|------|-------|-------------|
| T4.1 `GET /api/v9/demo_readiness` aggregator | CC | New endpoint with 8 checks per §2.5 |
| T4.2 `POST /api/v9/demo_readiness/test_chain` — single_bar | CC | Synthetic bar through full chain |
| T4.3 `POST /api/v9/demo_readiness/test_chain` — pattern_test | CC | Synthetic pattern → trade → close |
| T4.4 `POST /api/v9/demo_readiness/test_chain` — replay | CC | Last 6h of bars replayed at 10× |
| T4.5 `DemoReadinessCard.tsx` | CC | Status Board card matching §2.6 mockup |
| T4.6 `ArchivedDaysStrip.tsx` | CC | Bottom strip with day picker + modal |
| T4.7 Day Type pill — render PENDING/DEVELOPING text | CC | "טרום־מסחר" / "מתפתח" instead of `Normal` when row PENDING |

### Phase 5 — UAT + Pre-LIVE Sign-off (Michael + Cursor)

| Task | Owner | Verification |
|------|-------|--------------|
| T5.1 Pre-market 08:30 ET — SOT_HEALTH + DemoReadiness all green | Michael runs `python3 scripts/sot_health.py --strict` | exit 0 |
| T5.2 09:30 ET — day_type pill transitions PENDING → DEVELOPING | Michael watches UI | Visual confirm |
| T5.3 10:30 ET — IB locks, day_type pill → CLASSIFIED | Michael watches UI | `ib_locked=true` in API |
| T5.4 16:00 ET — RTH close (no rollover yet) | Cursor checks DB | Today's row still mutable |
| T5.5 18:00 ET — rollover fires | Cursor checks `v9_session_meta` + `v9_day_type_archive` | New rows |
| T5.6 18:01 ET — current row | API check | `status='PENDING'`, fresh row for next trading day |
| T5.7 Test chain end-to-end in DEMO | Michael clicks button | Trace shows all 8 steps PASS |

---

## §4 · Decisions confirmed by Michael (2026-05-29)

1. **Rollover trigger = FastAPI startup-hook + first-bar fallback.**
   Backend's `app.on_event("startup")` calls `rollover_if_needed(now_et)`,
   then registers an `asyncio` watchdog that re-calls it every 60s. The
   first-bar fallback in `on_bar()` is the safety net for backend-down at
   18:00 ET. **No launchd plist changes** needed.

2. **Open trades carry across the 18:00 ET boundary.** This is a rare case
   — once W-10 (90 min flat) is fixed, no trade should be open past 16:00
   ET, and definitely not past 18:00 ET. If one is, its `day_type` reference
   stays = the previous day's classification until W-10 closes it.

3. **In-flight S2/S4 fire-records are dropped at rollover.** Tighter risk
   surface. If a fire armed at 17:55 ET wasn't confirmed by 18:01 ET, it
   gets dropped — the next session re-evaluates fresh.

4. **`build_status` archive = full JSON snapshot.** ~2KB/day × 365 = 730KB.
   Cheap. Worth retaining for retrospective debugging of "why didn't
   pattern X fire on date Y".

5. **Demo chain `pattern_test` = Reactive Long.** Tests the full Long path:
   volume + delta + day_type confluence + 5min state machine. Most
   representative of real LIVE conditions.

---

## §5 · Out of scope (intentionally)

- LIVE-mode chain testing — DEMO only. Chain test refuses if mode=LIVE.
- Multi-symbol support. Single symbol (MES) only for now.
- Historical replay UI for previous month. Just the last week is enough.
- Risk-limit changes per day_type. Belongs in a different P-ID.
- TZ fix for `bridge_monitor.py` and other ad-hoc scripts. Phase 5 cleanup.

---

## §6 · Definition of Done (Phase 5 sign-off)

All 8 of these must be true for Pre-LIVE green-light:

1. ✅ `python3 scripts/sot_health.py --strict` exit 0
2. ✅ `GET /api/v9/demo_readiness` returns `overall=READY`
3. ✅ `POST /api/v9/demo_readiness/test_chain` (all 3 kinds) all PASS
4. ✅ `v9_*_archive` tables have rows for at least 2 past days
5. ✅ Pre-RTH `/day_type/v9/current` returns `status=PENDING, data=null`
6. ✅ At 18:00 ET observed: rollover fires, archive populated, new PENDING
   row inserted within 60s
7. ✅ `v9_account_status.mode='DEMO'` enforced — chain test refused if LIVE
8. ✅ All blast-radius checks in §7 pass (compliance_manifest, callers,
   migration rollback, UI states) — no orphan/dead code paths

---

## §7 · Blast radius + rollback (Cursor critical review 2026-05-29)

After Cursor reviewed the design, these are the surfaces that change and the
plan to keep them safe.

### §7.1 What this design touches

| Surface | Change | Risk if mishandled |
|---|---|---|
| `v9_day_type_history.status` enum | Add `DEVELOPING`, `ROLLED_OVER` | `compliance_manifest.yaml:130` enum throws validation error |
| `v9_day_type_history` UPSERT | New rule: only `INSERT` on rollover; in-day = UPDATE | If old code path still UPSERTs at 22:00 ET, the bug returns |
| `v9_account_status` table | Currently EMPTY (0 rows, no callers) — needs seed | Without seed → chain test always 403 (which is the safer default) |
| `/day_type/v9/current` & `/key_levels` | Return `PENDING/data:null` when no row | UI verified ✅ — already handles `classified=false` |
| 4× `date.today().isoformat()` in routes | → `et_today().isoformat()` | If missed, the 22:00 ET → 05:00 IL bug stays |
| Migration 019 (5 tables + 1 view) | Pure additive | Rollback = `DROP TABLE v9_*_archive; DROP VIEW v9_bars_5min_for_date;` |
| FastAPI startup hook + 60s watchdog | New asyncio task | If hook crashes → backend won't boot. **Wrap in try/except + log.warning, never raise** |
| First-bar fallback in `on_bar()` | New idempotent check | Race with startup hook? Both call `rollover_if_needed` which is guarded by `last_rollover_date` in `v9_session_meta` (DB-locked) |
| `v9_day_type_state` overnight pollution (§14, audit 04 finding) | Truncate stale rows at rollover; S2 `hydrate()` uses 24h sliding window | If `SessionBoundaryManager` doesn't truncate, S2 picks up yesterday's `Normal` from `v9_day_type_state` for first hours after reset |
| `RiskValidator.daily_reset()` dead code (§7 risk #5, audit §9.1) | Wire into `SessionBoundaryManager.rollover()` | If unwired, `daily_trades_count` and `consecutive_losses` never reset. Currently harmless (shadow mode), **LIVE-mode time bomb** |
| Consumer write gate (§14, NEW MECHANISM from CC consult) | `DayTypeConsumer.consume()` refuses UPSERT when `day_type==UNKNOWN` and `lock_state==PENDING` | Without this, every overnight Globex bar between midnight ET and RTH open writes a stale-prefilled row. State-machine reset (§2.2) alone is not enough — the consumer must also gate. |

### §7.2 Per-phase rollback procedure

| Phase | Rollback command | Recovery time |
|---|---|---|
| Phase 2 (migration only) | `git revert <commit>` + `sqlite3 ... "DROP TABLE v9_session_meta; DROP TABLE v9_day_type_archive; DROP TABLE v9_tpo_sessions_archive; DROP TABLE v9_woodies_signals_archive; DROP TABLE v9_build_status_archive; DROP VIEW v9_bars_5min_for_date;"` + restart backend | 2 min |
| Phase 2 (code only — endpoints PENDING) | `git revert <commit>` + restart backend. Old `/current` returns yesterday's row (= the bug, but not crash) | 1 min |
| Phase 3 (archive endpoints) | `git revert <commit>` — pure-additive. Frontend graceful degrades (no archive strip) | 30s |
| Phase 4 (UI + chain test) | `git revert <commit>` — pure-additive. SOT_HEALTH still works via existing scripts/sot_health.py | 30s |

### §7.3 Tests that must run green before each phase merges

```bash
# Phase 2 minimum
pytest tests/v9/api/test_day_type_routes_pending_semantics.py -q
pytest tests/v9/services/session_boundary/ -q
pytest tests/v9/db/test_migration_019.py -q
pytest tests/v9/systems/day_type/test_compliance_manifest_enum.py -q
pytest tests/v9/api/ -q                        # full API suite no regressions

# Phase 3 minimum
pytest tests/v9/api/archive/ -q

# Phase 4 minimum
pytest tests/v9/api/test_demo_readiness.py -q
pytest tests/v9/services/test_chain_refuses_in_live.py -q
npm test --prefix frontend/v9                  # frontend tests no regression
```

### §7.4 Manual smoke checklist (before declaring phase done)

- [ ] `curl /api/v9/day_type/v9/current` after backend restart at 03:00 ET — must return `classified=false, developing=false, status='PENDING'`
- [ ] `curl /api/v9/key_levels` same time — `today.day_type` must be `null` (not yesterday's value)
- [ ] DB query `SELECT changes() FROM v9_day_type_history WHERE date=tomorrow_in_ET` after midnight UTC → must be 0
- [ ] At T+18:00 ET, watch backend logs for `[SessionBoundary] rollover fired for date=YYYY-MM-DD`
- [ ] After rollover, `SELECT * FROM v9_day_type_archive WHERE trading_date=yesterday` → 1 row
- [ ] Chain test `POST /api/v9/demo_readiness/test_chain` while `v9_account_status` is empty → 403 "no DEMO mode confirmed"

---

## §8 · Account safety (chain-test only — full LIVE order enforcement deferred)

Michael's decision 2026-05-29: full LIVE order enforcement is deferred to a
separate P-ID. This phase only needs to ensure the **chain-test endpoints
cannot trigger anything in LIVE mode**.

### §8.1 What we DO build in this phase

```python
# backend/v9/api/v9/demo_readiness.py
def _assert_demo_or_403():
    """Refuse if account is not in DEMO mode. Empty table = 403 (safe default)."""
    with db_session() as s:
        row = s.execute(
            "SELECT mode FROM v9_account_status ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row is None or row[0] != "DEMO":
            raise HTTPException(
                status_code=403,
                detail="Chain test refused: account not in DEMO mode. "
                       "v9_account_status either empty or mode != 'DEMO'."
            )

@router.post("/test_chain")
async def test_chain(req: TestChainRequest):
    _assert_demo_or_403()                  # ← guard 1
    if not os.environ.get("V9_ALLOW_DEMO_CHAIN_TEST"):
        raise HTTPException(403, "V9_ALLOW_DEMO_CHAIN_TEST not set")  # ← guard 2
    ...
```

Migration 019 includes a seed:
```sql
INSERT INTO v9_account_status (mode, daily_pnl, trade_count, margin_used_pct)
VALUES ('DEMO', 0, 0, 0);
```

### §8.2 What we explicitly DO NOT build (deferred to next P-ID)

- Order routing to broker (no `order_router` exists yet — `TradeManager` only writes `v9_trades` rows; no broker integration)
- LIVE → DEMO toggle UI
- ENV var `V9_ENABLE_LIVE_ORDERS` enforcement on `TradeManager.open_trade`
- Risk-limit gates per `account.mode`

These belong in **next P-ID = "Pre-LIVE Order-Router Integration"** — separate
work after this design is shipped.

### §8.3 Why this is enough for now

The system has **no broker integration**. The only side-effect of
`open_trade()` is an `INSERT INTO v9_trades`. So a chain test cannot trade
real money even if the safety check fails. The 403 is belt-and-braces — it
prevents misleading entries in the trades table when `mode=LIVE` is later
introduced.

---

## §9 · Updates to task list (after §7+§8 review)

These tasks supersede the entries in §3:

### Phase 2 — additions

- **T2.0 NEW** — Migration 019 seeds `v9_account_status` with `mode='DEMO'`.
- **T2.1 UPDATED** — Migration 019 must include update to
  `compliance_manifest.yaml:130` enum: `[PENDING, LOCKED, LOCKED_LOW_CONF, DEVELOPING, ROLLED_OVER]`.
  Validation test asserts every status string the consumer might emit
  passes the manifest enum.
- **T2.2 UPDATED** — `SessionBoundaryManager.rollover()` wrapped in
  try/except. If it raises, log `error` (not `debug`), backend continues to
  serve traffic. Failed rollover is recoverable on next 60s tick.
- **T2.6 UPDATED** — Add 3 regression tests:
  - 22:00 ET on date N → no row exists for date N+1 (Bug A regression)
  - `et_today()` returns N at 22:00 ET (= 05:00 IL) (Bug B regression)
  - Migration 019 down-migration succeeds without orphan rows
- **T2.7 UPDATED** — UAT must verify §7.4 manual smoke checklist.

### Phase 4 — additions

- **T4.8 NEW** — `_assert_demo_or_403()` guard on **all** chain-test
  endpoints (single_bar / pattern_test / replay). Refuses if
  `v9_account_status.mode != 'DEMO'`. Tested with empty table (= safe
  default refuse) and with `mode='LIVE'` (= explicit refuse).
- **T4.9 NEW** — Frontend banner: if `account.mode != 'DEMO'`, hide the 3
  chain-test buttons and show "DEMO required". Don't rely on backend 403
  alone.

---

## §10 · Pre-flight checks (CC must paste raw output before touching code)

CC's Phase 2 consultation doc
(`docs/reports/CC_AUDIT_DAILY_RESET_CONSULTATION_2026-05-29.md`) MUST contain
raw paste of these commands. Each section gates the next:

```bash
# §10.1 — Every TZ-naive date/time use in backend (Bug B blast radius)
rg "date\.today\(\)|datetime\.now\(\s*\)" backend/v9 -n
# Expected: 13 matches (current count). Each becomes a fix in T2.5.

# §10.2 — Every writer of v9_day_type_history (Bug A root-cause hunt)
rg "v9_day_type_history" backend/v9 -n
rg "DayTypeHistory|day_type_history" backend/v9 -n
git log -p --all backend/v9 -- "*day_type*" | head -200
# Goal: identify the call-path that wrote 29/5 row at 22:00 ET 28/5.

# §10.3 — All readers of /current endpoints (= callers of buggy logic)
rg "day_type/v9/current|/key_levels|/woodies/current|/tpo/current" backend/v9 frontend/v9/src -n

# §10.4 — All UPSERT/INSERT into the 5 archive-source tables
rg "INSERT.*v9_woodies_signals|INSERT.*v9_tpo_sessions|INSERT.*v9_audit_events|INSERT.*v9_bars_5min" backend/v9 -n

# §10.5 — Confirm no LaunchAgent / cron currently does daily reset
launchctl list | grep -i "mems26\|day_type\|rollover"
crontab -l 2>/dev/null | grep -i mems26
ls ~/Library/LaunchAgents/ | grep -i mems26
# Expected: only com.mems26.bridge. Anything else → STOP and ask.

# §10.6 — Confirm migration ≥ 019 doesn't already exist
ls backend/v9/db/migrations/versions/ | sort | tail -5
# Expected: 018 is the highest. 019 is ours.

# §10.7 — Confirm v9_account_status state (so we know what seed needs)
sqlite3 data/mems26_local.db "SELECT * FROM v9_account_status;"
# Expected: empty or 1 row. If many rows → schema needs UNIQUE constraint.

# §10.8 — Confirm WoodiesSignals/Trades/AuditEvents schemas have rowid INTEGER PRIMARY KEY (= safe to ALTER ADD COLUMN)
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_bars_5min);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_woodies_signals);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_trades);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_audit_events);"
sqlite3 data/mems26_local.db "PRAGMA table_info(v9_five_min_setups);"
# Expected: each has `id INTEGER PRIMARY KEY`. ALTER ADD is safe.
```

**STOP conditions (CC pauses + asks Michael):**
- §10.5 returns anything beyond `com.mems26.bridge` → unknown automation
- §10.2 git-blame is inconclusive → CC must NOT guess; ask
- §10.8 any table missing `id INTEGER PRIMARY KEY` → schema needs migration
  redesign, not just ALTER ADD

---

## §11 · Sandbox boundary — `is_synthetic` flag (Michael decision: option A)

**Schema rule (mandatory T2.1):**

```sql
ALTER TABLE v9_bars_5min        ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0;
ALTER TABLE v9_woodies_signals  ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0;
ALTER TABLE v9_trades           ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0;
ALTER TABLE v9_audit_events     ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0;
ALTER TABLE v9_five_min_setups  ADD COLUMN is_synthetic INTEGER NOT NULL DEFAULT 0;

-- Indices for fast filter
CREATE INDEX idx_v9_bars_5min_synthetic   ON v9_bars_5min(is_synthetic, ts);
CREATE INDEX idx_v9_woodies_signals_synth ON v9_woodies_signals(is_synthetic, ts);
CREATE INDEX idx_v9_trades_synth          ON v9_trades(is_synthetic, entry_ts);
```

**Production-query rule (mandatory T2.x — every endpoint):**

Every `SELECT` from these 5 tables MUST include `WHERE is_synthetic = 0`
(or equivalent named-arg filter in SQLAlchemy). Default behavior is "show
production data only". Test endpoints opt-in with `?include_synthetic=1`.

```python
# backend/v9/db/filters.py — new module
def production_filter(query):
    return query.where(text("is_synthetic = 0"))

# Every existing query updated:
query = production_filter(select(V9Bars5min).order_by(V9Bars5min.ts.desc()))
```

**Test-chain rule (mandatory T4.2-T4.4):**

All 3 chain-test endpoints write rows with `is_synthetic=1`. Response body
returns the new row IDs:

```python
@router.post("/test_chain")
async def test_chain(req: TestChainRequest) -> TestChainResponse:
    _assert_demo_or_403()
    ...
    return TestChainResponse(
        trace=[...],
        synthetic_row_ids={
            "v9_bars_5min": [bar_id],
            "v9_woodies_signals": [sig_id, ...],
            "v9_trades": [trade_id],
            "v9_audit_events": [evt_id, ...],
        },
        cleanup_command=f"python3 scripts/clean_synthetic.py --ids {bar_id},...",
    )
```

**Archive rule (mandatory T2.3 / T3.x):**

Snapshotter at 18:00 ET filters `is_synthetic=0` on every source query. No
synthetic row ever reaches `v9_*_archive`. Backfill script for existing
data: `UPDATE v9_X SET is_synthetic = 0 WHERE is_synthetic IS NULL` (run
once during migration 019 deploy).

**Cleanup utility (mandatory T2.x):**

`scripts/clean_synthetic.py` — removes ALL `is_synthetic=1` rows from all
5 tables. Idempotent. Used after manual chain testing or for periodic
hygiene. Output:

```
$ python3 scripts/clean_synthetic.py
Removed 1 row from v9_bars_5min
Removed 5 rows from v9_woodies_signals
Removed 1 row from v9_trades
Removed 12 rows from v9_audit_events
Removed 0 rows from v9_five_min_setups
Total: 19 synthetic rows cleaned.
```

**SOT_HEALTH rule (mandatory T2.6):**

`scripts/sot_health.py` adds `is_synthetic = 0` filter to every DB freshness
query so synthetic test data never satisfies a freshness check.

**Tests (mandatory T2.6):**
- Insert `is_synthetic=1` row into `v9_bars_5min`. Production query must
  return ZERO rows. Synthetic-included query must return 1.
- Run snapshotter end-to-end with mixed real+synthetic rows. Archive must
  contain ONLY real.
- Run `clean_synthetic.py` after a chain test. All synthetic rows removed,
  no production rows touched.

---

## §12 · Final risk consolidation (Cursor 2026-05-29 final review)

| # | Original risk | Section that mitigates it | Status |
|---|---|---|---|
| R1 | 22:00 ET write recurs tonight | §10.2 root-cause hunt; T2.5 priority | Tracked |
| R2 | 13× `date.today()` / `datetime.now()` no TZ | §10.1 grep gate; T2.5 fix all | Tracked |
| R3 | startup hook crashes backend | §7.1 wrap in try/except; §9 T2.2 update | Tracked |
| R4 | legacy `status` enum collision | §9 T2.1 update — extend manifest enum | Tracked |
| R5 | test chain pollutes prod DB | §11 `is_synthetic` flag | Tracked |
| R6 | CC scope creep | §10 STOP conditions; §9 commit-per-task | Tracked (process) |
| R7 | sot_health cross-checks break | §11 includes sot_health update | Tracked |
| R8 | no backout if Phase 2 breaks | §7.2 per-phase rollback procedure | Tracked |

**Plaster check:** zero plasters remain in this design. Every fix addresses
root cause. Every behavioral change has a regression test. Every schema
change is reversible.

**Confidence:** if CC follows this design strictly, no regression in
existing functionality, no new latent bug surface, and the daily reset
behavior emerges cleanly.

---

## §13 · ADDITION (Michael 2026-05-29) — Tiered Fire Status (Plan A++)

**Status:** Decision deferred until CC's audit returns. Could land as Phase
2.5 (between Phase 2 and Phase 3) or as a separate P-ID after the
daily-reset work merges.

**Goal (Michael's words, translated):** "For every pattern not
day-type-dependent, show in build_status whether it WOULD have fired given
no other gates (trading hours, day_type). I want to see the chain working
and where things are stuck."

### §13.1 — Architecture (4-tier evaluation)

For every pattern (FHB, Reactive Long/Short, Initiative Long/Short, Quiet,
ZLR, TLB, TT, GB100, VEGAS, GHOST, FAMIR, HTLB, HFE), the inspector
evaluates four independent tiers:

```text
Tier 1 — Bar primitives        (always evaluable)
  • CCI thresholds
  • Volume ratios vs avg
  • Delta cumulative sign
  • EMA / LSMA / VWAP relative position
  • Range / ATR ratios

Tier 2 — Pattern logic         (multi-bar, depends on Tier 1)
  • N of last M bars satisfy condition X
  • Breakout above bar-K's high
  • Reversal candle confirmed
  • Divergence detected
  • CCI zero-line cross

Tier 3 — Time / Killzone gates (orthogonal to data)
  • RTH active (09:30–16:00 ET)
  • Killzone class (NY_OPEN, MIDDAY, POWER_HOUR, OFF)
  • First-hour eligibility (FHB only)

Tier 4 — Day-type authorization (depends on S1)
  • auth_table[day_type, pattern] = ALLOWED / SKIP
  • Risk-budget remaining for this pattern
  • Confluence requirements per day_type
```

**Status pill per pattern:**

| Tier reached | Status | UI color |
|---|---|---|
| Tier 1 not met | `🔴 INTRINSIC_BLOCKED` (data not there) | red |
| Tier 1 met, Tier 2 not met | `🟠 BUILDING` (close but not confirmed) | orange |
| Tier 1+2 met, Tier 3 blocked | `🟡 SHADOW_FIRE` ⭐ (would fire if not for time/killzone) | yellow |
| Tier 1+2 met, Tier 4 blocked | `🟡 AUTH_DENIED` (would fire if day_type allowed) | yellow |
| All 4 tiers met | `🟢 LIVE_FIRE` (real fire) | green |

The **`SHADOW_FIRE` pill** is the answer to Michael's question: "is the
chain working?" If a pattern hits `SHADOW_FIRE` during off-hours, you know
the bridge → bars → primitives → multi-bar logic chain is healthy.

### §13.2 — Numeric distance to fire (Plan A+ component)

Each Tier 1 / Tier 2 condition exposes a `progress` ratio (0–1):

```python
{
  "tier": 1,
  "condition": "volume_ratio",
  "current": 1.4,
  "threshold": 1.5,
  "progress": 0.93,   # 1.4 / 1.5
  "met": False
}
```

UI renders a tiny progress bar per condition. Patterns approaching fire
become visible at a glance.

### §13.3 — Shadow Fires journal (Plan A++ component)

New table `v9_shadow_fires` (added in a follow-up migration, e.g. 020):

```sql
CREATE TABLE v9_shadow_fires (
    id INTEGER PRIMARY KEY,
    ts DATETIME NOT NULL,
    pattern TEXT NOT NULL,
    direction TEXT NOT NULL,
    tier_blocked INTEGER NOT NULL CHECK (tier_blocked IN (3, 4)),
    block_reason TEXT NOT NULL,           -- "RTH_NOT_ACTIVE", "DAY_TYPE_AUTH", etc.
    bar_ts DATETIME NOT NULL,
    bar_close FLOAT,
    primitives_snapshot JSON NOT NULL,    -- Tier 1 conditions at fire moment
    pattern_logic_snapshot JSON NOT NULL, -- Tier 2 conditions at fire moment
    is_synthetic INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_shadow_fires_ts ON v9_shadow_fires(ts);
CREATE INDEX idx_shadow_fires_pattern ON v9_shadow_fires(pattern, direction, ts);
```

Every time a pattern reaches `SHADOW_FIRE` (T1+T2 met, T3 or T4 blocked),
a row is inserted. Production query default: `WHERE is_synthetic = 0`
(per §11).

**Backtest-for-free use case:**
End-of-day Michael runs:
```bash
sqlite3 data/mems26_local.db "
  SELECT pattern, direction, COUNT(*) as shadow_count, block_reason
  FROM v9_shadow_fires
  WHERE date(ts) = date('now')
  GROUP BY pattern, direction, block_reason
  ORDER BY shadow_count DESC;
"
```
→ Sees: "Reactive Long shadow-fired 7× today, all blocked at Tier 3 (RTH
not active)." Knows the pattern logic is healthy, just gated.

### §13.4 — Frontend impact

`frontend/v9/src/v9/components/build_status/`:
- `ComponentTable.tsx` — add 4 columns (Tier 1 / 2 / 3 / 4) with progress
  bars per condition
- New row pill renderer for `SHADOW_FIRE` (yellow with ⭐ icon)
- New `ShadowFiresStrip.tsx` — yesterday's + today's shadow fire counts
  per pattern, click → modal with per-fire detail

Estimated: ~4 hours frontend work, ~3 hours backend (inspector
restructuring), ~1 hour migration.

### §13.5 — Decision matrix (after CC's audit)

CC's audit will tell us:
1. How structured is the existing inspector? (Tier-1 vs Tier-2 already
   separated, or all jumbled?)
2. Are pattern detectors already pure (returning `met / not met`) or do
   they short-circuit on gate failures?
3. How many places in the codebase short-circuit on day_type / killzone
   before evaluating pattern logic? (= work needed to refactor)

Based on those answers, we'll choose:

| If CC reports... | Then... |
|---|---|
| Inspector already tier-aware, detectors pure | **Phase 2.5** — small extension, lands inside this work |
| Inspector tightly coupled to gates, refactor needed | **Separate P-ID** — clean redesign, ~3 days CC |
| Detectors short-circuit deeply | **Separate P-ID** — bigger refactor, ~5 days CC |

### §13.6 — Out of scope for §13 (always)

- Auto-trading on shadow fires (NEVER — they're informational only)
- Backtesting with historical data (separate effort, requires bar replay)
- Cross-symbol shadow fires (single symbol = MES)

---

## §14 · Consumer write gate — NEW MECHANISM (CC consult 2026-05-29)

> **Origin:** `docs/reports/CC_CONSULT_P31_2026-05-29.md` §1.4. CC reversed
> his audit recommendation (`et_trading_day_18`) after walking the
> 7 readers of `v9_day_type_history.date`. The actual root-cause of Bug A
> is **NOT** in `_extract_session_date` — the calendar-date semantic is
> correct. The bug is that the consumer accepts `UNKNOWN/PENDING`
> classifications and UPSERTs them, pre-filling tomorrow's row with
> stale state. **`570f10d` stays.** P31 builds on it; no revert.

### §14.1 The 3-case walk (why `et_trading_day_18` would NOT help)

| Case | Bar (ET) | UTC | `570f10d` writes `date=` | Premature row? |
|------|----------|-----|--------------------------|----------------|
| 1 | 14:00 ET 29/5 (RTH) | 18:00 UTC 29/5 | `2026-05-29` | No — RTH, real classification |
| 2 | 20:00 ET 28/5 (Globex) | 00:00 UTC 29/5 | `2026-05-28` | No — `570f10d` fixed this |
| 3 | **01:00 ET 29/5** (Globex) | 05:00 UTC 29/5 | `2026-05-29` | **YES — stale row written here** |

In Case 3, `_extract_session_date` is correct (calendar ET = 29/5). The
`et_trading_day_18` alternative would also return `2026-05-29` (already
past 18:00 ET on 28/5 = next trading day = 29/5). Both functions agree
on Case 3 — yet the bug still manifests, because the **state machine
holds 28/5's classification** (Normal, IB 7583.5/7553.25 from RTH 28/5).

### §14.2 Why `et_trading_day_18` is dangerous (not just "not helpful")

All 7 readers use calendar-date semantics:

```
day_type_v9_routes.get_current()        — date.today()
day_type_inspector.inspect()            — date.today().isoformat()
aggregator._get_current_day_type()      — date.today().isoformat()
woodies_inspector._day_type_context()   — date.today().isoformat()
key_levels_routes._day_type_row()       — date('now')   ← SQLite UTC bug
hydration.hydrate_day_type()            — date.today()
day_type/api.get_current()              — date.today().isoformat() (V1 compat)
```

If the writer keys on `et_trading_day_18` while readers query on
`et_today()` (calendar), there is a **6-hour window every day** (18:00 ET
→ midnight ET) where the writer stores under `date=tomorrow` while
readers look for `date=today`. UI shows PENDING for 6 hours despite a
classification existing. **Migrating all 7 readers to trading-day
semantics is a much larger blast radius than fixing the consumer gate.**

### §14.3 The fix — two locks together

**Lock 1 — State machine reset at 18:00 ET (T2.2 in Phase 2):**

`SessionBoundaryManager.rollover()` calls `day_type_machine.reset()` at
the boundary. After reset, `to_classification()` returns `None` until
new RTH data arrives.

**Lock 2 — Consumer write gate (NEW, T2.2b in Phase 2):**

```python
# backend/v9/systems/day_type/consumer.py — DayTypeConsumer.consume()
def consume(self, event: dict) -> None:
    day_type = event.get("day_type")
    lock_state = event.get("lock_state", "LOCKED")  # default for back-compat
    # Refuse non-classifications. Don't pollute v9_day_type_history with PENDING/UNKNOWN.
    if day_type in (None, "", "UNKNOWN") and lock_state == "PENDING":
        logger.debug(
            "[DayTypeConsumer] gated write: day_type=%s lock_state=%s ts=%s",
            day_type, lock_state, event.get("timestamp")
        )
        return
    # … existing UPSERT logic unchanged
```

**Why both locks are required:** Lock 1 alone is not enough — even with
a reset state machine, edge cases exist where `to_classification()` is
called before a meaningful classification is available (e.g. mid-IB,
mid-stage-A1). Lock 2 is the defensive backstop. Lock 2 alone is also
not enough — without reset, the state machine continues feeding yesterday's
classification on overnight bars, and Lock 2 (which only blocks
`UNKNOWN/PENDING`) wouldn't catch a `Normal/LOCKED` carry-over.

### §14.4 Test matrix

```python
# tests/v9/systems/day_type/test_consumer_write_gate.py
def test_gate_refuses_unknown_pending():
    # before fix: UPSERT happens; after fix: no DB change
    consumer.consume({"day_type": "UNKNOWN", "lock_state": "PENDING", ...})
    assert query_count("SELECT COUNT(*) FROM v9_day_type_history WHERE date=?", today) == 0

def test_gate_allows_locked_classification():
    consumer.consume({"day_type": "Normal", "lock_state": "LOCKED", "probability": 0.68, ...})
    assert query_count("SELECT COUNT(*) FROM v9_day_type_history WHERE date=?", today) == 1

def test_gate_allows_locked_low_conf():
    consumer.consume({"day_type": "Normal", "lock_state": "LOCKED_LOW_CONF", ...})
    assert query_count(...) == 1

def test_gate_does_not_swallow_real_classifications_on_first_bar_of_rth():
    # The gate must NOT block the first valid classification after RTH open
    # Sets up state machine → first valid event → consumer.consume → row written
    ...
```

---

## §15 · `570f10d` overlap — what it fixed, what P31 extends

> **Status:** `570f10d` is **on HEAD as of 2026-05-29 09:40 IL**. P31
> does NOT revert it. P31 extends it with §14 (consumer write gate)
> + §2.2 (state machine reset).

### §15.1 What `570f10d` did

```python
# backend/v9/systems/day_type/consumer.py::_extract_session_date
return ts.astimezone(ZoneInfo("America/New_York")).date()  # was: ts.date()
```

Removed: `🕐 History` label workaround in `day_type_inspector.py` (patch-on-patch).

Deleted: stale `2026-05-29` row from `v9_day_type_history`.

### §15.2 What it fixed (Case 2)

UTC→ET calendar conversion. `bar @ 20:00 ET 28/5 = 00:00 UTC 29/5` no
longer writes a row for `date=2026-05-29`. ✅

### §15.3 What it left open (Case 3 — the actual bug Michael saw)

Overnight Globex bars **after midnight ET** still produce premature
rows. The bar `01:00 ET 29/5` returns `2026-05-29` correctly, but the
state machine still holds 28/5's classification. The consumer accepts
the (UNKNOWN or stale Normal) event and writes a row.

### §15.4 P31 is additive — no revert needed

P31's mechanism stack:

```
┌─────────────────────────────────────────────┐
│ Mechanism 1 (570f10d, ALREADY ON HEAD):     │
│   _extract_session_date uses ET calendar    │
│   → fixes Case 2 (UTC→ET bug)               │
├─────────────────────────────────────────────┤
│ Mechanism 2 (P31 §2.2, NEW):                │
│   State machine reset at 18:00 ET           │
│   → to_classification() returns None        │
│     until new data arrives                  │
├─────────────────────────────────────────────┤
│ Mechanism 3 (P31 §14, NEW):                 │
│   Consumer write gate                       │
│   → refuses UNKNOWN/PENDING UPSERTs         │
│     (defensive backstop)                    │
└─────────────────────────────────────────────┘
```

All 3 must be present for the bug to be fully closed. Each compensates
for failure modes of the others.

---

## §16 · Bug 04 — `five_min_system.hydrate()` overnight early-return

> **Origin:** `docs/reports/sot_health_audit/04_DAY_TYPE_API_NONE.md`.
> Audit 04 found `current_day_type=None` in `/api/v9/five_min/current`
> despite `v9_day_type_history` having a row for today.
> **Scope:** Item F in P31 task list (audit confirmed F belongs in P31).

### §16.1 Root cause

`backend/v9/systems/five_min/five_min_system.py::hydrate()`:

```python
def hydrate(self, db_session) -> HydrationResult:
    session = self._classify_session(now_et)
    if session in (Session.OVERNIGHT, Session.PRE_MARKET, Session.AFTER_HOURS):
        self.mode = FiveMinMode.OVERNIGHT_MODE
        self._hydrated = True
        return HydrationResult(...)   # ← EARLY RETURN
    # ↓ day_type hydrate is HERE — never reached during overnight
    latest = db.query(V9DayTypeState).order_by(V9DayTypeState.id.desc()).first()
    if latest and latest.day_type:
        self.current_day_type = latest.day_type
```

The `current_day_type` field stays at `__init__` default of `None` for
all overnight/pre-market/after-hours sessions. When backend restarts at
e.g. 03:00 ET, S2 starts up with `current_day_type=None`.

### §16.2 Impact (which patterns are blocked?)

| Pattern class | Source | Blocked by `None`? |
|---------------|--------|----------------------|
| S2 Reactive | `Reactive.evaluate()` checks `current_day_type == "Nontrend"` | No — `None != "Nontrend"` → passes (negative gate) |
| S2 Initiative | Same negative gate | No |
| S2 Chart H&S | `current_day_type in ("Neutral_Extreme", "Normal", ...)` | **YES — blocked** |
| S2 Chart DblBT | Same positive gate | **YES — blocked** |
| S2 Flags Bull/Bear | `current_day_type in ("Trend_Normal", "Normal", ...)` | **YES — blocked** |
| S4 (Woodies) | Does not read `current_day_type` | No |

So during pre-RTH **even after S1 classifies during RTH**, S2 chart
patterns and flags are blocked **until the first `_on_day_type_update`
event handler fires** (line 266-272). That event arrives only after S1
locks classification — typically at 10:30 ET (post-IB-lock).

**Effective UX:** between RTH open (09:30 ET) and IB lock (10:30 ET),
S2 chart + flag patterns are silently blocked even though they could
theoretically fire on Reactive/Initiative criteria. ~1 hour of dead
detection every morning.

### §16.3 Fix (one-line reorder)

Move the day_type hydrate block to **before** the session-type early
return:

```python
def hydrate(self, db_session) -> HydrationResult:
    # Hydrate day_type FIRST — works for all session types
    latest = db.query(V9DayTypeState).order_by(V9DayTypeState.id.desc()).first()
    if latest and latest.day_type and latest.day_type != "UNKNOWN":
        self.current_day_type = latest.day_type
    # Now classify session and do session-specific hydrate
    session = self._classify_session(now_et)
    if session in (Session.OVERNIGHT, Session.PRE_MARKET, Session.AFTER_HOURS):
        self.mode = FiveMinMode.OVERNIGHT_MODE
        self._hydrated = True
        return HydrationResult(...)
    # … existing RTH hydrate ...
```

### §16.4 Coupling with §14 consumer gate

The day_type hydrate reads from `v9_day_type_state`, NOT from
`v9_day_type_history`. Audit 04 found 122 `Normal` rows + 133 `UNKNOWN`
rows for today in `v9_day_type_state` (overnight pollution). After the
consumer gate (§14) is in place, only valid classifications flow into
`v9_day_type_state` — but historical pollution remains.

**Action:** `SessionBoundaryManager.rollover()` (T2.2) must also
truncate or mark stale `v9_day_type_state` rows older than
`et_today() - 1d`. This couples §16 to §2.2.

### §16.5 Test

```python
# tests/v9/systems/five_min/test_hydrate_day_type_overnight.py
def test_hydrate_picks_up_day_type_during_overnight():
    # Insert v9_day_type_state row with day_type=Normal at 14:00 ET yesterday
    # Backend restart at 03:00 ET (overnight)
    # hydrate() → mode=OVERNIGHT_MODE AND current_day_type='Normal'
    ...

def test_hydrate_skips_unknown_day_type():
    # Insert v9_day_type_state row with day_type=UNKNOWN at 02:00 ET today
    # hydrate() → current_day_type stays None (don't pick up garbage)
    ...
```

---

## §17 · CC consult acceptance summary (2026-05-29)

CC's consult report (`docs/reports/CC_CONSULT_P31_2026-05-29.md`)
delivered 5 actionable changes. Cursor accepts all 5:

| # | CC recommendation | Cursor action |
|---|-------------------|---------------|
| 1 | Keep `et_calendar_date` for writes (do NOT switch to `et_trading_day_18`) | §14 + §15 added; `570f10d` stays |
| 2 | Add consumer write gate (refuse UNKNOWN/PENDING) | §14 added (NEW MECHANISM) |
| 3 | Split P31 (A–H) and P32 (I–L) is clean — no hidden dependency | Confirmed — 2 separate prompts |
| 4 | Task order A → B → C → G → E → D → F → H | Adopted in P31 prompt |
| 5 | F (`five_min_system.hydrate()` early-return) belongs in P31, not P32 | §16 added; F kept in P31 |

**Latent bug confirmed by CC's STOP condition:** `key_levels_routes::_day_type_row()` SQLite `date('now')` (UTC) breaks the day_type pill for 4 hours every evening. Item C (in P31 task list) **must** land atomically with item A — not as a follow-up commit.
