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

## §4 · Decisions deferred / open questions

1. **Rollover trigger mechanism — launchd vs backend cron vs FastAPI startup-hook?**
   Recommendation: backend `asyncio.create_task` with sleep_until_18et loop.
   Pro: fewer moving parts, restarts with backend. Con: silent if backend
   is down at 18:00 ET — but the first-bar fallback handles that.

2. **Should open trades be force-closed at rollover or carry across?**
   §2.1 says carry. Michael's call.

3. **What happens to in-flight S2/S4 fire-records during rollover?**
   §2.1 says reset. But if a fire armed at 17:55 ET hasn't been confirmed by
   18:01 ET, do we drop it? Recommendation: yes, drop. Risk surface tighter.

4. **Archive of `build_status` — full JSON or only patterns that fired?**
   §2.4 says full JSON snapshot. ~2KB per day. Cheap.

5. **Demo chain `pattern_test`** — which pattern? Recommendation: FHB
   (simplest, deterministic, no day_type dependency).

---

## §5 · Out of scope (intentionally)

- LIVE-mode chain testing — DEMO only. Chain test refuses if mode=LIVE.
- Multi-symbol support. Single symbol (MES) only for now.
- Historical replay UI for previous month. Just the last week is enough.
- Risk-limit changes per day_type. Belongs in a different P-ID.
- TZ fix for `bridge_monitor.py` and other ad-hoc scripts. Phase 5 cleanup.

---

## §6 · Definition of Done (Phase 5 sign-off)

All 7 of these must be true for Pre-LIVE green-light:

1. ✅ `python3 scripts/sot_health.py --strict` exit 0
2. ✅ `GET /api/v9/demo_readiness` returns `overall=READY`
3. ✅ `POST /api/v9/demo_readiness/test_chain` (all 3 kinds) all PASS
4. ✅ `v9_*_archive` tables have rows for at least 2 past days
5. ✅ Pre-RTH `/day_type/v9/current` returns `status=PENDING, data=null`
6. ✅ At 18:00 ET observed: rollover fires, archive populated, new PENDING
   row inserted within 60s
7. ✅ `v9_account_status.mode='DEMO'` enforced — chain test refused if LIVE
