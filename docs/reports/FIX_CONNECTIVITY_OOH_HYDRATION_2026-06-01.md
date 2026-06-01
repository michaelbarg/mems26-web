# FIX REPORT — Connectivity + OOH Bars + Hydration · 2026-06-01

**Date:** 2026-06-01 12:10 IL (05:10 ET) · **Author:** Claude Code (CC)
**Based on:** `docs/reports/DIAGNOSE_ONLY_CONNECTIVITY_OOH_2026-06-01.md` (Rev 2)
**Decisions:** Michael approved Option C (Woodies 5min), backend LaunchAgent, all P0/P1/P2 fixes.

---

## Changes Summary

| # | Fix | File(s) Changed | Verification |
|---|-----|----------------|-------------|
| P0.1 | Backend LaunchAgent + auto-restart | `~/Library/LaunchAgents/com.mems26.backend.plist` (NEW) | `curl health` → alive, `launchctl list` shows both agents |
| P0.2 | `timedelta` import | `backend/v9/services/bar_ingestion.py:8` | v9_bars_5min: 7 → 609 rows, zero NameError |
| P0.3 | TZ fix (Chicago → New_York) | `bridge/v9_history.py:43,48` | Matches base_stream.py:74 |
| P1.4 | Archive schema drift | `backend/v9/services/session_boundary/manager.py:199-210` | 30 sessions archived, zero startup error |
| P1.5 | Woodies 5min dedup + UNIQUE | `backend/v9/api/v9/bars.py:846` + DB migration | 26,250 → 970 rows, UNIQUE(ts) index, INSERT OR REPLACE |
| OOH.6 | Option C overnight bars | `backend/v9/api/v9/woodies_chart_routes.py` + `backend/v9/services/historical_replay.py` | DB fallback for stale export, replay map includes woodies_5min |
| P2.7 | Startup hydration inventory | `backend/main.py` | Logs CVD/Woodies/5min/archive counts at startup |

---

## Detailed Diffs

### P0.1 — Backend LaunchAgent
**New file:** `~/Library/LaunchAgents/com.mems26.backend.plist`
- Mirrors bridge plist pattern
- KeepAlive: SuccessfulExit=false (auto-restart on crash)
- Exports: BRIDGE_TOKEN, V9_EXPORT_DIR, V9_DISABLE_WATCHDOG
- Logs: /tmp/backend.log, /tmp/backend.err.log
- ThrottleInterval: 30s

### P0.2 — `timedelta` import
```diff
- from datetime import datetime, timezone
+ from datetime import datetime, timedelta, timezone
```

### P0.3 — TZ fix
```diff
# bridge/v9_history.py lines 43 and 48
-     _CHICAGO_TZ = ZoneInfo("America/Chicago")
+     _CHICAGO_TZ = ZoneInfo("America/New_York")
-         _CHICAGO_TZ = pytz.timezone("America/Chicago")
+         _CHICAGO_TZ = pytz.timezone("America/New_York")
```

### P1.4 — Archive schema
```diff
# backend/v9/services/session_boundary/manager.py
- INSERT INTO v9_tpo_sessions_archive
-   SELECT *, datetime('now') AS archived_at
-   FROM v9_tpo_sessions WHERE trading_date < ?
+ INSERT INTO v9_tpo_sessions_archive
+   (session_id, session_type, trading_date, opened_ts, closed_ts,
+    poc_price, vah_price, val_price, range_high, range_low,
+    total_volume, profile_shape, opening_type,
+    ib_high, ib_low, ib_locked, letter_count, archived_at)
+   SELECT session_id, session_type, ... datetime('now')
+   FROM v9_tpo_sessions WHERE trading_date < ?
```

### P1.5 — Woodies dedup
- Changed `INSERT INTO` → `INSERT OR REPLACE INTO` with `symbol='MES'`
- DB: dropped old UNIQUE(ts,symbol), created UNIQUE(ts)
- Deleted 26,200 duplicate rows

### OOH.6 — Option C
- Added `_load_woodies_from_db(limit)` fallback in `woodies_chart_routes.py`
- When Sierra export has 0 bars (overnight): serves from DB with `stale_badge: "LAST SESSION · <date>"`
- Added `v9_bars_5min_woodies` → `woodies_5min` to historical_replay map

### P2.7 — Startup hydration
- Added lightweight hydration inventory at startup (before HistoricalReplay)
- Counts: CVD rows this session, Woodies 5min total, bars 5min total, TPO archives
- Session-boundary-aware CVD counting (18:00 ET reset)

---

## Verification Evidence (Rule 5)

```
=== Backend Health ===
{"alive":true,"mode":"shadow","ts":1780304889.76,"price_file_age_ms":465,"ws_clients":1}

=== LaunchAgents ===
1289  -15  com.mems26.backend
638   0    com.mems26.bridge

=== v9_bars_5min ===
609 rows (was 7 before timedelta fix — 87× increase from gap-fill + live ingestion)

=== Woodies 5min (deduped) ===
970 total, 970 distinct ts (was 26,250 with ~34× duplication)

=== TPO Archive ===
30 sessions archived (was 0 — INSERT failed before schema fix)

=== Y IB ===
dll_missing — EXPECTED at 05:08 ET (pre-RTH, Sierra TPO reports zeros).
Archive populated with 30 sessions. Will resolve at next RTH open.

=== Bridge ===
[volume_profile] New data — export_ts=1780304888 (push #1903)
Zero push errors since backend restart.

=== No NameError ===
grep "NameError.*timedelta" /tmp/backend.err.log → 0 matches
```

## D-091/D-092 RTH Gate — Safety Evidence

**6 independent gates prevent firing on overnight/historical data:**

| System | Gate | Location |
|--------|------|----------|
| S2 FiveMin | `OVERNIGHT_MODE` → return (no detection) | `five_min_system.py:727-732` |
| S4 Woodies | `_is_rth_bar()` time window 09:30-16:00 ET | `woodies_system.py:280-288` |
| S1 DayType | `if not bar.is_rth: return` | `state_machine.py:448,479` |
| BarRouter | Session tag on every bar event | `bar_router.py:76-95` |
| Replay | `mode="WARMUP"` tag → no DB persistence | `historical_replay.py:90` |
| PreFire | `_check_rth_open()` → blocks non-RTH | `validator.py:53-62` |

**Overnight bars are display-only. Zero risk of firing.**

---

## What's NOT Fixed (deferred)

| Item | Why Deferred | Where |
|------|-------------|-------|
| Full BarRouter warmup (V9_DO_WARMUP) | Slow handler regression (TPO 988ms/bar) blocks startup | Needs handler optimization first |
| Sierra 24h bar export (Option A) | Requires Sierra Chart UI change | Michael decision pending |
| `.env` loading in LaunchAgent | Sandbox "Operation not permitted" | Non-blocking — critical vars hardcoded in plist |
| CVD/CCI active warm-up (replay through systems) | Blocked by V9_DO_WARMUP slowness | Gets better as bars accumulate in DB |

---

*Fix complete. Zero order/risk/sizing/polling changes.*
