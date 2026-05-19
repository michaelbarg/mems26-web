# P30.9 — Sierra Screen Parity Data Contract

**Date:** 2026-05-19
**Status:** PARTIAL — Sierra exports live, TPO API wired, overlay shipped. CVD pane + stepped VAH/VAL open.
**No SHADOW/DEMO/LIVE enabled. No trade_command writes.**

---

## Source Of Truth

Michael provided 5 Sierra screenshots showing the visual contract:

1. **5-min chart** — TPO VAH/VAL (magenta dashed), POC (magenta solid), IB Mid/Low (cyan), Cumulative Delta Bars below
2. **TPO Profile** — Letter-based market profile A-M, volume histogram, POC arrow, IB lines (blue)
3. **Woodies CCI 5m** — CCI-14 (black), TCCI (yellow), histogram bars, ZLR markers, data values column
4. **Tick Reversal 15** — Numbers bars with delta/volume/cumulative delta
5. **3-min chart** — Two sets of TPO levels (period-scoped), IB, Cumulative Delta

---

## What Was Implemented

### Backend

| Item | File | Status |
|------|------|--------|
| Sierra `tpo.json` → `/api/v9/tpo/current` | `tpo_routes.py` | LIVE — `source=sierra_tpo_json`, max age 30s |
| `periods[]` from DB (interim) | `tpo_routes.py` `_load_tpo_periods()` | Wired — returns 0 periods pre-market (expected) |
| Woodies 5m `current_bar` POST | `bars.py` `Woodies5MinPayload` | Ready — awaits bridge stream |
| 5min POST: no erroneous cumulative_delta dispatch | `bars.py` `post_bars_5min` | Fixed in P30.9 commit |

### Sierra DLL (v9.4.0-p30.9)

| Export File | Status | Content |
|-------------|--------|---------|
| `tpo.json` | **NEW** — LIVE | `session{poc,vah,val}`, `ib{high,mid,low}`, `prior_day{high,low,close}` |
| `woodies_5min.json` | **FIXED** — LIVE | Full CCI/TCCI/ZLR/HFE per 5m bar |
| `5min.json` | LIVE | OHLCV (poc_vol/vah/val zeros — not TPO truth) |
| `cumulative_delta.json` | LIVE | Points with delta/cum/price |
| All other streams | LIVE | tick_reversal, footprint, volume_profile, etc. |

### Frontend

| Item | File | Status |
|------|------|--------|
| Stepped POC overlay | `SierraLevelsOverlay.tsx` | Shipped — magenta POC steps from `periods[]` |
| Cyan IB lines | Same | Shipped — `#06b6d4` (not green) |
| White prior-day levels | Same | Shipped — dashed white |
| Removed old full-width price lines | `ChartV5b.tsx` | Done |

---

## UAT 2026-05-19 (pre-market session)

### Tests

```
pytest tests/v9/api/test_tpo_routes_sierra_contract.py \
       tests/v9/api/test_woodies_5min_payload.py \
       tests/v9/db/test_api.py \
       tests/v9/bridge/test_streams.py -q
→ 40 passed

pytest tests/v9/ -q
→ 1304 passed, 1 skipped, 1 failed (pre-existing flaky: test_publish_threadsafe_warns_when_unbound from P27.5)
```

### Sierra Export Freshness

```
tpo             age_s=2.7  version=v9.4.0-p30.9
5min            age_s=2.7  version=v9.4.0-p30.9
cumulative_delta age_s=2.7  version=v9.4.0-p30.9
woodies_5min    age_s=2.7  version=v9.4.0-p30.9
woodies_30min   age_s=2.7  version=v9.4.0-p30.9
```

### /api/v9/tpo/current

| Axis | Check | Result |
|------|-------|--------|
| Quality | source=sierra_tpo_json, poc/vah/val non-null | **PASS** — poc=7401.75, vah=7407.25, val=7397.75 |
| Recency | tpo.json age < 30s | **PASS** — 2.7s |
| Cardinality | periods >= 1 if DB has sessions | **PASS (documented)** — 0 periods pre-market, expected |
| Latency | < 500ms | **PASS** — 1.3ms |

IB = 0.0 / found=false — correct: pre-market, IB hasn't formed.
prior_day: high=7454.25 low=7372.75 close=7411.25 — matches yesterday's range.

### /api/v9/chart/bars5min?limit=600

| Axis | Check | Result |
|------|-------|--------|
| Quality | bad_count=0, OHLCV valid | **PASS** — 0 bad bars |
| Recency | latest_ts == DB MAX(ts) | **PASS** — both 2026-05-19 02:50:00 |
| Cardinality | count=600 | **PASS** — 600 |
| Latency | < 2s | **PASS** — 692ms |

### Visual (ChartV5b)

- Overlay component `SierraLevelsOverlay.tsx` is shipped
- Full visual UAT requires RTH session (IB forms, periods populate)
- CVD pane: NOT YET IMPLEMENTED — gap documented below

---

## Gap Classification

| Gap | Status | Recommendation |
|-----|--------|----------------|
| `tpo.json` lacks native `periods[]` | DEFER | Keep DB interim in API until Sierra DLL exports periods |
| `bridge/v9_streams/tpo_stream.py` old contract | DEFER | Adapt when full bridge approved |
| `post_tpo()` old `bars[]` schema | DEFER | Adapt when bridge ingests new tpo.json |
| Cumulative Delta pane in ChartV5b | **NEXT: P30.9b** | GET from Sierra file or enrich 5m bars |
| VAH/VAL stepped overlay | DEFER | After POC UAT passes during RTH |
| Woodies 5m live in UI | DEFER | Needs bridge stream + panel component |
| Full 12-stream bridge | DEFER | Stay bars-only until stability proven |
| Pre-existing flaky test | KEEP | `test_publish_threadsafe_warns_when_unbound` race condition from P27.5 |

---

## How Michael Proceeds

1. **Sierra is live** — study shows `v9.4.0-p30.9`, all exports fresh every ~3s.
2. **Backend + frontend running** — port 8000 and 3000 confirmed.
3. **Bridge** — narrow `--bars-5min-only` mode only. Do NOT start full 12-stream bridge.
4. **During RTH** — verify `/api/v9/tpo/current` shows `ib.found=true` with correct IB levels. Compare to Sierra screenshot.
5. **ChartV5b overlay** — open cockpit, verify stepped magenta POC / cyan IB / white prior-day appear. Visual compare vs Sierra at same timestamp.
6. **If data axes pass during RTH** → P30.9 upgrades to GREEN for data contract.
7. **Next single thread: P30.9b** — Cumulative Delta pane + GET API from Sierra `cumulative_delta.json`.
8. **Do NOT advance to LIVE trading** until full P30 phase gate passes.

---

## P30.9c — Chart Sierra Alignment (2026-05-19)

### Changes (Cursor)

- **CVD**: Moved from separate `CumulativeDeltaPane` below chart to inline CVD scale
  on the same lightweight-charts instance. `cvdMapping.ts` tail-aligns Sierra points
  to loaded bars. Green/red histogram + cyan cumulative line on shared time axis.
- **TPO overlay**: z-index: 10. Session POC/VAH/VAL (magenta). Previous-day
  POC/VAH/VAL from `/api/v9/tpo/previous_day` (silver dashed). Prior-day high/low (white).
  IB only when `ib_locked=true` and price > 0.
- **Backend**: `ib_*` returns null when `ib.found=false`. `periods[]` filtered to last 48h.
- **Removed**: Separate `CumulativeDeltaPane` component (not time-aligned).

### Gap Status

| ID | Gap | Status | Notes |
|----|-----|--------|-------|
| G1 | IB lines missing | **DEFERRED** | `ib.found=false` pre-market; verify after 10:30 ET RTH |
| G2 | CVD index `i` alignment | **DONE (interim)** | Tail-align via `mapCvdToBarTimes`; ideal: Sierra exports `ts` per point |
| G3 | Stepped POC | **DONE** | DB `v9_tpo_sessions` periods; 3 periods visible pre-market |
| G4 | DISCONNECTED top bar | **SEPARATE** | WebSocket/Redis issue, not chart parity |
| G5 | RTH visual UAT | **DEFERRED** | Needs market hours + Michael screenshot compare |

### UAT (2026-05-19 pre-market)

```
/api/v9/tpo/current: source=sierra_tpo_json, poc=7401.75, ib=null (pre-market), periods=3
/api/v9/tpo/previous_day: found=true, poc=7420.25, vah=7420.75, val=7420.25
/api/v9/cumulative_delta/current: 10 points, source=sierra_cumulative_delta_json, stale=false
Tests: test_tpo_routes_sierra_contract + test_cumulative_delta_routes → 7 passed
Frontend lint: cvdMapping.ts + SierraLevelsOverlay.tsx → 0 errors
```

---

## Safety

- No SHADOW/DEMO/LIVE enabled
- No trade_command.json written
- Bridge remains local-only (`CLOUD_URL=http://localhost:8000`)
- Full bridge NOT started — narrow `--bars-5min-only` mode only
- No LaunchAgent or plist changes
