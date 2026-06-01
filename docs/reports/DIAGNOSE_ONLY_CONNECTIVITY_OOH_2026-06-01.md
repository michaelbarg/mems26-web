# DIAGNOSE_ONLY — Connectivity + OOH Bars + Bridge · 2026-06-01

**Date:** 2026-06-01 ~11:30 IL (04:30 ET) · **Author:** Claude Code (CC) · **Rev:** 2 (added §6-§8)
**Mode:** READ-ONLY DIAGNOSTIC — zero code changes, zero config changes, zero service restarts.
**Source:** Cowork dashboard screenshot ~03:58 ET showing: DISCONNECTED, Y IB dll_missing, 0 trades, SHADOW 0t, "1 Issue".

---

## Summary

| # | Symptom | Root Cause | Classification | Severity |
|---|---------|-----------|----------------|----------|
| 1 | DISCONNECTED (WS, both panels) | Backend (uvicorn) not running — no process on port 8000 | **BUG** (no auto-restart for backend) | P0 |
| 2 | Y IB dll_missing | `v9_tpo_sessions_archive` schema mismatch (19 cols vs 27) → archive_yesterday failed → prev-day IB never archived/loaded | **BUG** (DB migration gap) | P1 |
| 3 | "1 Issue" badge | Cascading from #1 — Woodies panel shows "Disconnected — retrying" when backend unreachable | **Cascading** from #1 | — |
| 4 | No candles outside RTH | Backend down + `timedelta` import bug + **Sierra exports are RTH-only for bar history** | **BUG** × 2 + **GAP-IN-SPEC** (DLL bar export scope) | P0 |
| 5 | Bridge streams STALE/DEAD | Bridge running ✅ but pushing to dead localhost:8000 → errors accumulate | **Expected behavior** given #1 | — |

---

## Symptom 1 — DISCONNECTED (frontend ↔ backend)

### (a) Evidence

```bash
$ curl -s localhost:8000/health
# (exit code 7 — connection refused)

$ lsof -i :8000
# No uvicorn process.

$ lsof -i :3000
# Node listening (frontend dev server via screen session mems26_frontend)

$ ps aux | grep uvicorn | grep -v grep
# (empty)

$ screen -ls
# Only: 11102.mems26_frontend (Detached)
# No mems26_backend screen session exists.

$ launchctl list | grep mems
# 638  0  com.mems26.bridge
# (no backend LaunchAgent)
```

**Backend log** (`/tmp/backend.log`):
- **Started:** Process 11024, startup at ~10:04 AM IL (03:04 ET).
- **Last activity:** 10:38:08 IL (03:38 ET) — `POST /api/v9/bars/5min 200 OK`.
- **No crash/error/signal at end of log** — the process disappeared silently.
- Startup error (non-fatal): `[SessionBoundary] archive_yesterday error: table v9_tpo_sessions_archive has 19 columns but 28 values were supplied`.
- Runtime error: `NameError: name 'timedelta' is not defined` in `bar_ingestion.py:74`.
- Redis warnings: `Error 61 connecting to localhost:6379. Connection refused` (no local Redis — WS pubsub disabled, polling fallback).

### (b) Root Cause

Backend was started via `scripts/start_all.sh` in a screen session (`mems26_backend`). That screen session is gone. **There is no backend LaunchAgent** — only the bridge has one (`com.mems26.bridge`). When the screen session died, nothing restarted it. No auto-recovery mechanism exists.

### (c) Spec Reference

**CLAUDE.md** §Architecture: Backend runs at `127.0.0.1:8000`. Bridge pushes to localhost:8000.
**`scripts/start_all.sh`**: Starts backend in screen session — no auto-restart.
The LaunchAgent pattern used for the bridge is NOT replicated for the backend.

### (d) Classification: **BUG** — infrastructure gap (GAP-IN-SPEC)

### (e) Recommended Fix (do not execute)

1. **Create `com.mems26.backend.plist`** LaunchAgent mirroring the bridge plist.
2. **Immediate**: Restart backend manually.

---

## Symptom 2 — Y IB dll_missing

### (a) Evidence

```python
# backend/v9/api/v9/key_levels_routes.py:229
"prev_day_ib": "dll_missing ..." if prev_ib_high is None and prev_ib_low is None
```

```bash
$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_tpo_sessions_archive);" | wc -l
# 19 columns

$ sqlite3 data/mems26_local.db "PRAGMA table_info(v9_tpo_sessions);" | wc -l
# 27 columns (8 new: ib_width, ib_class, ib_locked_ts, poc_migration,
#   hvn_zones, lvn_zones, volume_cluster, previous_poc, poc_stuck_since)
```

```
# /tmp/backend.log startup:
[SessionBoundary] archive_yesterday error: table v9_tpo_sessions_archive
  has 19 columns but 28 values were supplied
```

### (b) Root Cause

Schema drift: `v9_tpo_sessions` gained 8 columns, archive not updated. `_archive_yesterday` does `INSERT INTO archive SELECT * FROM sessions` → fails → prev-day IB never archived → `dll_missing`.

Pre-RTH TPO empty (poc=0, vah=0, val=0) is expected — no RTH session in progress.

### (c) Spec Reference

**CLAUDE.md** §SoT Rule 1: honest failure > synthetic value. `dll_missing` label is compliant.

### (d) Classification: **BUG** (DB migration gap) + **Expected** (pre-RTH TPO empty)

### (e) Recommended Fix

1. Fix `_archive_yesterday` to use explicit column list (not `SELECT *`).
2. OR: `ALTER TABLE v9_tpo_sessions_archive ADD COLUMN ...` for 8 missing columns.

---

## Symptom 3 — "1 Issue" Badge

Cascading from #1. `WoodiesCciPanel.tsx:1341`: "Disconnected — retrying…" when backend unreachable. Fix #1 → resolves.

---

## Symptom 4 — No Candles Outside RTH (CORE FINDING)

### (a) Evidence

**Sierra DLL exports — FRESH but bar history is RTH-only:**

```bash
$ python3 -c "... 5min.json ..."
# Total bars: 601
# First bar: 2026-05-20 11:15:00 UTC
# Last bar:  2026-05-29 15:55:00 UTC
# Span: 220.7 hours
# Hour distribution (UTC): ONLY hours 08-15 (= RTH 04-11 ET, Chicago-encoded)
# ZERO bars outside these hours → RTH-only export

$ python3 -c "... woodies_5min.json ..."
# history array: 200 bars
# First: 2026-05-27 14:20:00 UTC
# Last:  2026-05-29 15:55:00 UTC
# Also RTH-only, last data from Friday May 29

$ python3 -c "... woodies_30min.json ..."
# bars: 0 (empty during overnight)

$ python3 -c "... tick_reversal_12.json ..."
# bars: 75 (has data)
```

**Live tick data IS available during overnight:**
```bash
$ cat ~/SierraChart_Data/v9_export/mes_ai_data.json
# session_phase: "OVERNIGHT", current_price: 7590.50
# CVD, VWAP, Market Profile, Woodies Pivots all populated

$ cat ~/SierraChart_Data/v9_export/live_price.json
# {"price":7590.50,"ts":1780303081,"bid":7607.50,"ask":7607.75,"vol":1159}
```

**DB state — bar tables:**
```
v9_bars_5min:             7 rows,  last=2026-06-01 07:35:00 (timedelta bug blocks ingestion)
v9_bars_5min_woodies:     14,994,  last=2026-06-01T07:38:06 (HAS overnight data from today!)
v9_bars_30min_woodies:    13,020,  last=2026-06-01 06:05:00
v9_bars_cumulative_delta: 2,299,   last=2026-06-01T07:35:00
v9_bars_footprint:        2,190,   last=2026-06-01 07:38:03
v9_bars_tick_reversal:    13,777,  last=2026-06-01 07:38:05
v9_bars_volume_profile:   1,243,   last=2026-06-01T07:38:05
```

**Woodies 5min DB HAS overnight rows from today (07:xx UTC = 03:xx ET):**
```sql
-- 52 rows pushed during the 34 min the backend was alive (10:04-10:38 IL)
SELECT substr(ts, 12, 2) as hour_utc, COUNT(*) FROM v9_bars_5min_woodies
WHERE ts >= '2026-06-01' GROUP BY hour_utc;
-- 07|52  (= overnight session, UTC 07 = ET 03)
```

**`timedelta` import bug blocks `v9_bars_5min` ingestion:**
```python
# backend/v9/services/bar_ingestion.py
# Line 8:  from datetime import datetime, timezone    ← timedelta MISSING
# Line 74: if _ts_check > ... + timedelta(minutes=2): ← NameError
```

### (b) Root Cause (THREE layers)

| Layer | Bug | Effect |
|-------|-----|--------|
| **1. Backend down** | No process on :8000 | Bridge pushes fail 100% → zero bars ingested now |
| **2. `timedelta` import bug** | `bar_ingestion.py:8` missing `timedelta` | Even when backend ran (10:04-10:38), `v9_bars_5min` ingestion failed → only 7 rows |
| **3. Sierra DLL exports RTH-only bar history** | `5min.json` 601 bars, all UTC 08-15 | `history_loader.py` gap-fill at startup only has RTH bars to fill. Overnight gap-fill impossible from this source. |

**However**: The Woodies 5min stream pushes the DLL's CURRENT bar during overnight (not from the `history` array, but from the live study output). This is how `v9_bars_5min_woodies` got 52 overnight rows today.

### (c) Spec Reference

**`session_state.py`**: System is designed for 24/6 operation (Pre-market 18:00-09:30 defined).
**CLAUDE.md** §Sierra real-time data: "Source of truth: live values come from Sierra Chart exports."
**D-091/D-092**: Pattern detection is RTH-only (CONT/REV gated to RTH day types), but data collection should be continuous for context.
**BarRouter DB Replay**: "Startup warm-up uses DB replay (last 12h bars)" — depends on bars existing in DB.

### (d) Classification

- **Bug** (code): `timedelta` import missing.
- **Bug** (infrastructure): Backend has no auto-restart.
- **GAP-IN-SPEC**: Sierra DLL `5min.json` bar export is RTH-only. No spec decision exists for "how to get overnight bar history into the DB." The live study output provides current bars (proven by Woodies 5min), but the history arrays are RTH-gated by Sierra Chart configuration.

### (e) Recommended Fix (do not execute)

1. Fix `timedelta` import.
2. Fix backend auto-restart.
3. **For overnight bar history**: See §6 below (Michael's direction evaluation).

---

## Symptom 5 — Bridge Streams

All 11 data streams read Sierra exports successfully (FRESH, 0-3s data age). All fail on the push side (backend down). Bridge is local-only (`CLOUD_URL=http://localhost:8000` confirmed in plist). Cascading from #1.

**Additional TZ inconsistency found:**
- `bridge/v9_streams/base_stream.py:74`: uses `ZoneInfo("America/New_York")` ✅ (correct per Michael 2026-05-28)
- `bridge/v9_history.py:43`: uses `ZoneInfo("America/Chicago")` ❌ (stale — not updated to match)

This means live bar pushes use correct TZ, but startup history gap-fill uses wrong TZ → ~1h timestamp drift in summer for historically-loaded bars.

---

## §6 — Evaluation of Michael's Proposed Direction

### 6.1 — "Use Woodies 5-min table as OOH candle source"

**Verdict: PARTIALLY VIABLE — with critical caveats.**

**What works:**
- `v9_bars_5min_woodies` table DOES get overnight data. Evidence: 52 rows at `07:xx UTC` (03:xx ET) from today's overnight session, pushed while backend was alive.
- The bridge reads `woodies_5min.json` every ~3s and pushes the entire payload (including the DLL's current bar) to `/api/v9/bars/woodies_5min`.
- Schema is rich: OHLCV + CCI-14, TCCI, LSMA, SWI, CZI, EMA-34, trend_state, ZLR/HFE detection, proj_hi/proj_lo (25 columns).

**What doesn't work:**
- **The `history` array in `woodies_5min.json` is RTH-only** (200 bars, all from past RTH sessions, last data May 29).
- **The export is EMPTY during overnight** for the `bars` key (0 bars) — only the `history` key has data, and that's RTH-only.
- **Massive duplication**: 52 rows for ~34 minutes = ~20 rows per 5-min bar (bridge pushes every poll cycle, not per bar close). The table has no UNIQUE constraint on `(ts, symbol)`.
- **Date quality issue**: Of 14,994 total rows, 14,568 have NULL/malformed date values. Only recent rows have proper timestamps.

**The canonical table is:** `v9_bars_5min_woodies` (ingested by the backend from bridge pushes to `/api/v9/bars/woodies_5min`).

**For OOH current bar**: YES, this works — the DLL exports the live Woodies study output even during overnight, and the bridge pushes it. But it's the CURRENT bar only, not history.

**For OOH history**: NO — the DLL `history` array is RTH-only. The same is true for `5min.json` (601 bars, all RTH hours 08-15 UTC).

### 6.2 — "200 bars history depth"

**Verdict: AVAILABLE but RTH-only.**

```bash
# woodies_5min.json: 200 bars in history array (total_bars: 210)
# 5min.json: 601 bars
```

The 200 Woodies bars span 49.6 hours (May 27-29), all RTH. The 601 regular bars span 220.7 hours (~9 trading days), all RTH. **These are enough for RTH history replay but contain zero overnight bars.**

For a startup that happens during overnight: the history_loader will fill RTH gaps from these exports, but the overnight period since last RTH close will have no historical bars (only the current live bar from the bridge).

### 6.3 — "On startup: reload 200 bars + bridge reports health per-stream"

**What exists today:**

| Component | Startup Behavior | Source |
|-----------|-----------------|--------|
| `history_loader.py` | Gap-fills from Sierra JSON exports. Reads `5min.json` (601 bars), `cumulative_delta.json`, `volume_profile.json`, etc. INSERT OR IGNORE into DB. | Sierra export files |
| `historical_replay.py` | Reads last 12h of bars from DB, publishes through BarRouter in WARMUP mode. Systems fill their buffers. | DB tables |
| `bars_5min_stream.py` | On first push after startup, backfills bars since MAX(ts) in DB from the `5min.json` bar array. | Sierra `5min.json` |
| Bridge heartbeat | `[heartbeat] alive — streams=11/12 total_pushes=X total_errors=Y` every 30s. Per-stream heartbeat with push/error counts. | Bridge log |

**What's missing:**
- **History_loader fills RTH gaps only** (Sierra exports are RTH-only for bar history).
- **No overnight bar replay exists.** The 12h replay (`historical_replay.py`) works IF the DB has overnight bars — but since the exports are RTH-only, the DB rarely has them.
- **Bridge reports per-stream health**, but there's no structured startup report ("loaded N bars from Sierra, M gaps detected, filled K").
- **No verification step** after startup — the system doesn't check if the bar buffers are actually warm.

### 6.4 — "Full state hydration list for continuous restart"

**COMPLETE STATE INVENTORY — what is and isn't restored on restart:**

#### ✅ RESTORED on restart (exists today)

| State | Source | Mechanism | File |
|-------|--------|-----------|------|
| Day type (today) | `v9_day_type_state` DB | `hydration.py` loads last row for today | `backend/v9/systems/day_type/hydration.py` |
| IB values (mid-session restart) | Sierra `tpo.json` | `maybe_seed_ib_from_tpo()` seeds machine if after IB lock | `backend/main.py:246-254` |
| Previous day context | `v9_tpo_sessions` DB | `load_previous_day_context()` → pd_high/pd_low/pd_close | `backend/main.py:174-179` |
| Previous day VA (NeuE/NeuC) | `load_tpo_previous_day_summary()` | Feeds DayTypeStateMachine prev_day_summary | `backend/main.py:152-166` |
| 5min bar history (RTH) | Sierra `5min.json` + DB | `history_loader.py` gap-fill + `bars_5min_stream.py` backfill | `backend/v9/services/history_loader.py` |
| Woodies signals | `v9_woodies_signals` DB (352 rows) | WoodiesSystem `.hydrate()` | `backend/main.py:108-116` |
| FiveMinSystem state | `.hydrate()` | Loads buffers from DB | `backend/main.py:83-92` |
| FootprintSystem state | `.hydrate()` | Loads buffers from DB | `backend/main.py:95-104` |
| TPOSystem state | `.hydrate()` | Loads from DB + Sierra tpo.json | `backend/main.py:118-128` |
| Volume profile / footprint / tick_reversal bars | DB tables | 12h HistoricalReplay through BarRouter | `backend/v9/services/historical_replay.py` |

#### ❌ NOT RESTORED on restart (lost state)

| State | Why Lost | Impact | Reset-Aware? | Recommended Source |
|-------|----------|--------|--------------|-------------------|
| **CVD cumulative total** | CVD resets at session boundary (18:00 ET). DB has 2,299 rows but cumulative is session-scoped. | CVD chart shows 0 until enough bars accumulate | ⚠️ YES — resets at 18:00 ET. Must NOT load across session boundary. | `v9_bars_cumulative_delta` — load from today's session start only |
| **Woodies CCI buffer** (CCI-14 needs 14+ bars) | System needs bar history to compute CCI. If buffer is empty, first 14 bars produce unreliable CCI. | Wrong CCI → wrong trend_state (GRAY instead of BLUE/RED) → wrong pattern gates | No | `v9_bars_5min_woodies` — replay last 20+ bars through WoodiesSystem |
| **Woodies trend state (BLUE/RED/GRAY/YELLOW)** | Derived from CCI buffer. Not persisted. | S4 pattern firing gated on trend state | No | Cascading from CCI buffer fix |
| **5min bar buffer for FiveMinSystem** | Only 7 rows in `v9_bars_5min` (timedelta bug). Replay has nothing to feed. | S2 patterns can't detect (need N-bar lookback) | No | Fix timedelta bug → bars accumulate → replay works |
| **Chop score** | `v9_chop_score` table: 0 rows | Layer 0 chop gate disabled | No | Computed from bars — needs bar history first |
| **Killzone state** | `v9_killzone_log` table: 0 rows | Killzone gating disabled | No | Computed from clock + bars |
| **Overnight bar history** | DLL exports RTH-only bar arrays. DB doesn't accumulate overnight bars (backend down + ingestion bug). | No chart candles during overnight. 12h replay has nothing for 18:00-09:30 window. | ⚠️ Session-scoped (ON high/low, etc.) | **NEW MECHANISM NEEDED** — see §7 |
| **Active trade state** | `v9_trades` table: 0 rows (SHADOW mode, no trades) | N/A in SHADOW | N/A | N/A until LIVE |
| **Daily range (session high/low)** | In `mes_ai_data.json` live (session_high: 7611.75, session_low: 7577.50) but not persisted to DB on backend crash | Chart shows stale range markers | ⚠️ Resets at session boundary | `mes_ai_data.json` → ingest on startup |
| **POC/VAH/VAL (live)** | Sierra `tpo.json` has poc=0/vah=0/val=0 during overnight (no RTH session). | Key levels show "missing" pre-RTH | Expected pre-RTH | Previous day VA from archive (fix archive bug first) |

---

## §7 — Recommended Architecture for OOH Bar Continuity

Based on the diagnostic findings, here is the **quality root-cause fix** — not a band-aid:

### Problem Statement

The Sierra DLL exports two kinds of data:
1. **Live snapshot** (`mes_ai_data.json`, `live_price.json`): Updated every ~3s, includes current price, CVD, session range, etc. Available 24/6.
2. **Bar history arrays** (`5min.json:bars`, `woodies_5min.json:history`): Rolling tail of completed bars. **RTH-only** — the Sierra chart session is configured to show only RTH bars.

The system needs overnight bars for:
- Chart display (candles outside RTH)
- System buffer warm-up (CCI-14, pattern lookback)
- 12h replay on restart

### Root Fix Options (for Michael to decide)

**Option A: Configure Sierra Chart for 24h session (DLL-side)**
- Change the MES chart in Sierra from RTH to "Use Full 24-Hour Session" (or "Use Evening Session").
- The DLL would then export overnight bars in `5min.json:bars[]` and `woodies_5min.json:history[]`.
- **Pros**: No code changes. Immediate fix. All downstream systems work automatically.
- **Cons**: Requires Sierra Chart UI change. May affect how TPO, IB, and day-type classification interpret "session start." The DLL study would need testing to confirm it handles the longer session correctly.
- **Risk**: The `session_state.py` defines CLOSED as 17:00-18:00 ET. If Sierra exports bars during the 17-18 "maintenance" window, the backend would need to handle this.

**Option B: Accumulate overnight bars from live bridge pushes (backend-side)**
- The bridge already pushes the DLL's CURRENT bar every ~3s during overnight (proven: 52 rows in `v9_bars_5min_woodies` today).
- **Change**: Make the backend accumulate these into proper 5-min bars (close bar every 5 minutes, store in DB with session phase tag).
- The `five_min_aggregator.py` already exists for aggregating tick_reversal_15 into 5-min bars — extend this pattern for overnight.
- **Pros**: No Sierra config change. Works with current DLL.
- **Cons**: Requires code changes. Need to deduplicate (bridge pushes ~20× per bar). Need to distinguish bar-close from intermediate updates.

**Option C: Hybrid — use Woodies 5min DB as primary + fill from live (Michael's direction)**
- **Primary source**: `v9_bars_5min_woodies` (already has overnight data when backend is alive).
- **Gap-fill on startup**: Read last 200 bars from this table for system warm-up.
- **Deduplication**: Add UNIQUE constraint on `(ts, symbol)` to prevent the current ~20× duplication.
- **Pros**: Builds on what already works. Woodies table has richer schema (CCI, LSMA, etc.).
- **Cons**: Need to fix the duplication problem first. Need to ensure the Woodies stream's "current bar" updates are bar-close-only (not every 3s poll).

### CC Recommendation

**Option A is the cleanest** if Sierra Chart can be configured for 24h bars without breaking TPO/IB/day-type logic. This is a one-setting change that fixes everything downstream.

**If A is not feasible** (e.g., TPO study depends on RTH-only), **Option C** (Michael's direction) is viable with these prerequisites:
1. Fix `timedelta` import bug (so `v9_bars_5min` also works).
2. Add dedup to Woodies 5min ingestion (UPSERT instead of INSERT).
3. Tag bars with session phase (RTH/OVERNIGHT/POST_MARKET) for safety gating.
4. **CRITICAL**: Ensure no trading decisions fire on overnight data. D-091/D-092 gate ALL patterns to RTH day types — verify this gate is active.

---

## §8 — Cross-Reference: Spec Consistency

| Finding | Spec Cross-Ref | Status |
|---------|---------------|--------|
| Backend has no LaunchAgent | Not mentioned in any spec | **GAP-IN-SPEC** |
| `timedelta` missing import | Future-ts guard added without import | **BUG** (code) |
| Archive table schema drift | `v9_tpo_sessions` +8 cols, archive not updated | **BUG** (DB migration) |
| Sierra exports RTH-only bar history | Not documented anywhere — implicit in Sierra chart config | **GAP-IN-SPEC** |
| Overnight data flow (Sierra→Bridge) | `session_state.py` defines PRE_MARKET 18:00–09:30 | **Working as designed** (bridge reads 24/6) |
| `dll_missing` for Y IB | SoT Rule 1: honest failure > synthetic value | **Correct behavior** |
| Bridge local-only | `CLOUD_URL=http://localhost:8000` confirmed | **Compliant** |
| TZ inconsistency: `v9_history.py` uses `America/Chicago`, `base_stream.py` uses `America/New_York` | Memory note 2026-05-28 | **BUG** (history loader has wrong TZ) |
| Redis connection refused (localhost:6379) | WS pubsub over local Redis | **Known gap** (polling fallback active) |
| Woodies 5min table massive duplication | 14,568 of 14,994 rows have malformed dates | **BUG** (no dedup/UNIQUE constraint) |

---

## Prioritized Fix Recommendations (for Michael's approval)

### P0 — Must fix before next RTH session

| # | Fix | Root Cause | Effort |
|---|-----|-----------|--------|
| 1 | **Restart backend** (immediate) | Process dead, no auto-restart | 1 min |
| 2 | **Add `timedelta` import** to `bar_ingestion.py` line 8 | 5min bars not ingesting | 30 sec |
| 3 | **Create `com.mems26.backend.plist`** LaunchAgent | Prevent future backend-down | 15 min |
| 4 | **Fix `v9_history.py` TZ**: `America/Chicago` → `America/New_York` (line 43) | History gap-fill has 1h drift | 1 min |

### P1 — Should fix this week

| # | Fix | Root Cause | Effort |
|---|-----|-----------|--------|
| 5 | **Fix archive schema**: `_archive_yesterday` explicit column list OR migrate table | Y IB dll_missing | 30 min |
| 6 | **Add UNIQUE(ts, symbol)** to `v9_bars_5min_woodies` + dedup existing rows | ~20× duplication per bar | 30 min |
| 7 | **Decide Sierra 24h vs Option C** for overnight bars | No OOH bar history | Decision, then 1-4h implementation |

### P2 — Hydration improvements

| # | Fix | Root Cause | Effort |
|---|-----|-----------|--------|
| 8 | **CVD warm-up on restart**: load today's CVD rows (session-bounded) into cumulative buffer | CVD shows 0 after restart | 1h |
| 9 | **Woodies CCI buffer warm-up**: replay last 20+ bars through WoodiesSystem at startup | CCI unreliable for 14 bars after restart | 1h |
| 10 | **Startup verification**: after history_loader + replay, check buffer_size > 0 for each system | Silent warm-up failures | 2h |

---

## Verification Checklist (post-fix)

After applying fixes 1-5:

- [ ] `curl -s localhost:8000/api/v9/cockpit/heartbeat` returns 200
- [ ] `lsof -i :8000` shows uvicorn listening
- [ ] Frontend: LIVE/STALE (not DISCONNECTED)
- [ ] Woodies panel shows data (no "Disconnected — retrying")
- [ ] `SELECT COUNT(*) FROM v9_bars_5min` grows over time (timedelta fix)
- [ ] `/api/v9/key_levels` shows Y IB values after next archive
- [ ] `python3 scripts/sot_health.py` — no 🔴 MISSING for API endpoints
- [ ] `v9_history.py` TZ matches `base_stream.py` (both `America/New_York`)

---

*End of diagnostic. Zero code changes made. All recommendations require Michael's approval.*
