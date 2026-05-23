# P30 — Chart sync (bars alignment + axis visibility) + bridge wipe-today

**Date:** 2026-05-20
**Branch:** `stabilize/mems26-local-truth-2026-05-16`
**Status:** CODE GREEN — backend/bridge restart required for **C** only

Three independent cockpit issues addressed together because they share
file context (`ChartV5b.tsx`, `CvdChartPane.tsx`, bridge entrypoint).

| Fix | Surface | Restart needed |
|-----|---------|-----------------|
| **A.** Time axis always visible | Frontend (Next dev HMR picks it up) | Page reload |
| **B.** Pixel-perfect bars alignment | Frontend | Page reload |
| **C.** Bridge wipe-today opt-in flag | Bridge entrypoint + new module | Bridge restart (LaunchAgent reload) |

Backend code is unchanged. **No DLL / LaunchAgent / CLOUD_URL / bridge
token touched.**

---

## A — Time axis always visible

### Before
`ChartV5b` set `timeScale.visible: false`. The cockpit's only time axis
lived on the CVD pane. Collapsing or hiding the CVD pane in a future
build would leave the chart with **no time axis at all**.

### After
`ChartV5b.timeScale.visible: true` (default ON). A new effect watches
`cvdOwnsAxis` (derived from `cvdPanelPct` ≥ `CVD_AXIS_OWN_MIN_PCT = 14`)
and applies:

| `cvdPanelPct` | Owner | Price axis | CVD axis |
|---------------|-------|-----------|----------|
| ≥ 14% | CVD pane | hidden | visible |
| < 14% | price pane | visible | hidden |

Exactly one axis is rendered at any moment — no duplicate at the seam.

`cvdPanelPct` is tracked via `Panel.onResize` and persisted with the
existing `saveCvdPanelPct(pct)`.

### Risks / rollback
- Threshold mistuned → CVD pane shows no axis at 12% minSize. Set
  `CVD_AXIS_OWN_MIN_PCT` lower or higher; constant lives at the top of
  `ChartV5b.tsx`.
- Rollback: revert ChartV5b.tsx + CvdChartPane.tsx hunks (single
  commit). Restore `timeScale.visible: false` on the price chart.

---

## B — Pixel-perfect bars alignment

### Before
`cumOhlcSeries` returned **one candle per CVD point**, ignoring the
price-bar timeline entirely once CVD points carried their own `t`
field. If the CVD point set had fewer entries than the visible price
bars in the same range (first session of the day before CVD started,
DLL-skipped slot, history backfill mismatch), the two
`lightweight-charts` time scales computed **different `barSpacing` =
chartWidth / N**. The bottom pane bars no longer landed under their
matching price bar.

### After
`cumOhlcSeries` is now **bars-driven**: one entry per price-bar
timestamp, in the same order ChartV5b ships them. Carry-forward cum
from the latest CVD point ≤ bar's timestamp, OR `WhitespaceData` when
the bar is strictly before the first CVD point. Result: CVD candles
and price candles match cardinality and timestamps 1:1, so
`barSpacing` is identical in any shared visible range.

Other alignment guarantees pinned explicitly:
- `rightOffset: 0` on **both** timescales (was relying on
  lightweight-charts default for the price pane).
- `tsToUnix` is the single canonical converter — imported from
  `cvdMapping.ts` into `CvdChartPane.tsx`, replacing the inline
  `new Date(ts).getTime()` (no -04:00 anchor) that had silently
  shifted bars in the legacy no-`t` path.

### Risks / rollback
- `WhitespaceData` for pre-CVD slots leaves visible gaps on extreme
  history pans. Acceptable: those slots had no CVD data; alignment is
  preserved.
- If the API ever ships CVD points whose `t` is misaligned (not on a
  5-min boundary), the carry-forward stays last-known; visually
  identical to the prior behavior.
- Rollback: revert the body of `cumOhlcSeries` in CvdChartPane.tsx
  to the original points-driven `.map`.

---

## C — Bridge `V9_BRIDGE_WIPE_TODAY_ON_START`

### Behavior
- Default OFF — bridge identical to pre-P30.
- When env var is `1` / `true` / `yes` (case-insensitive), the bridge
  deletes rows from `v9_bars_5min` whose `ts >= TODAY 00:00 ET` (as
  UTC ISO, e.g. `2026-05-20 04:00:00` during DST or
  `2026-05-20 05:00:00` during EST). Cutoff matches
  `tpo_routes._rth_open_ts_today`'s timezone (`America/New_York`).
- Failure to wipe (missing DB, locked DB, non-SQLite URL, schema
  missing) is **swallowed with `logger.warning`** — the bridge always
  continues startup.
- Only `v9_bars_5min` is touched. `v9_tpo_sessions`,
  `v9_bars_5min_woodies`, footprint, imbalance — every other table
  stays intact. TPO + Day Type Engine multi-day windows preserved.

### Where the hook runs
`bridge/json_bridge.py::main` calls `wipe_today_bars_if_requested()`
**after** the bridge banner log line, **before** stream instances are
constructed and threads start. Both live-mode and `--history-only`
take the hook (history-only then re-backfills today from Sierra JSON).

### Risks / rollback
- User sets the flag accidentally → loses today's bars. Mitigation:
  default off, env var name explicit, log line is `WARNING` (not
  INFO) so the wipe always appears in `/tmp/bridge.err.log`.
- Bridge mass-deletes today's bars while the cockpit is open: cockpit
  poll re-fetches and shows the fresh slate within ≤ 5 s. No backend
  changes needed.
- Postgres / Render deployment: wipe is skipped with a `not SQLite`
  warning. Out of scope until we migrate off SQLite.
- Rollback: remove the `wipe_today_bars_if_requested()` call in
  `json_bridge.py::main`, delete `bridge/v9_startup.py` and the test
  file. No DB schema changes to reverse.

---

## Files modified

| File | Summary |
|------|---------|
| `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` | Price `timeScale.visible: true` + `rightOffset: 0`; `cvdPanelPct` state via `Panel.onResize`; effect toggles price axis based on `cvdOwnsAxis`; passes `axisVisible` down. |
| `frontend/v9/src/v9/components/chart/v5b/CvdChartPane.tsx` | New `axisVisible` prop wired through `applyOptions`; `cumOhlcSeries` rewritten bars-driven with `WhitespaceData` fallback; imports canonical `tsToUnix` from `cvdMapping`; header lookup tolerates trailing whitespace candles. |
| `bridge/json_bridge.py` | Imports `wipe_today_bars_if_requested`, calls it in `main()` before stream startup; wrapped in try/except (defense-in-depth — the module already swallows). |
| `bridge/v9_startup.py` | **NEW** — `wipe_today_bars_if_requested()`, `_resolve_sqlite_path()`, `_today_midnight_utc_iso()`. SQLite-only, default OFF, fails open. |
| `tests/v9/bridge/test_wipe_today_on_start.py` | **NEW** — 24 tests covering the four user-specified axes + helpers, falsy/truthy flag spellings, DST/EST timezone math, non-SQLite skip, sibling-table protection. |
| `docs/reports/PROMPT_P30_CHART_SYNC_AND_BRIDGE_CLEANUP.md` | **NEW** — this report. |

---

## Tests

```bash
$ pytest tests/v9/bridge/test_wipe_today_on_start.py -q
........................                                                 [100%]
24 passed in 0.25s
```

Cases mapped to the user's required matrix:

| Required case | Test |
|---------------|------|
| Flag off → no DELETE | `test_flag_off_does_not_open_db` (mocks `sqlite3.connect`, asserts not called) |
| Flag on, empty DB → "Wiped 0 bars" no error | `test_flag_on_empty_db_reports_zero` |
| Flag on, 5 today + 10 yesterday → only today's 5 wiped | `test_flag_on_today_5_yesterday_10_wipes_only_today` |
| Flag on, DB error → continue startup | `test_flag_on_db_error_continues_startup` |

Extra coverage:
- `test_resolve_sqlite_path_{absolute,relative,non_sqlite}` — URL parsing.
- `test_today_midnight_utc_iso_during_{edt,est}` — DST math sanity.
- `test_flag_on_db_missing_warns_and_continues` — missing file fails open.
- `test_flag_on_non_sqlite_url_skips_with_warning` — Postgres safety.
- `test_{falsy,truthy}_flag_values_*` — env-flag spelling matrix.
- `test_flag_on_does_not_touch_other_tables` — TPO / sibling tables protected.

Regression sweep:
- `pytest tests/v9/bridge/` → **74 passed** (50 prior + 24 new).
- `pytest tests/v9/bridge/ tests/v9/api/test_cumulative_delta_routes.py` → **83 passed**.
- Frontend `tsc --noEmit` against modified files: **clean** (pre-existing
  errors in `TopBar.tsx` and `PriceDebugConsole.tsx` are unrelated).

---

## Manual UAT (visual checks for Michael)

Backend / bridge: **no restart required for A & B** — Next dev reloads
on save; cockpit reload picks them up. **Restart bridge for C.**

1. Open cockpit → **time axis renders at the bottom in every state**.
2. Drag the CVD pane to its `minSize=12%`.
   - Expect: price-pane bottom shows the time axis (CVD axis hidden;
     price takes over because pane is < 14%).
3. Drag the CVD pane back to ~30%.
   - Expect: time axis on the CVD pane; price-pane bottom hidden;
     **never two axes simultaneously**.
4. Zoom price chart in/out (mouse wheel) and pan (drag).
   - Expect: every CVD bar lines up directly under its price bar; no
     compression or stretch when the visible range changes timeframe.
5. Switch TF 5m → 15m → 1h → back to 5m.
   - Expect: alignment holds at each TF (aggregation collapses cum
     into wider buckets, count still matches price bars at that TF).
6. (Bridge) ensure `.env` contains `V9_BRIDGE_WIPE_TODAY_ON_START=1`
   for a one-shot wipe:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.mems26.bridge.plist
   launchctl load   ~/Library/LaunchAgents/com.mems26.bridge.plist
   tail -n 50 /tmp/bridge.log /tmp/bridge.err.log
   ```
   Expect: `[BRIDGE STARTUP] Wiped N bars from today's session (table=v9_bars_5min, cutoff ts >= 'YYYY-MM-DD 04:00:00' UTC = 00:00 ET today)`.
   Cockpit auto-refreshes within ≤ 5 s and shows the fresh history.
7. **Important:** after the one-shot wipe, **unset** the flag
   (`V9_BRIDGE_WIPE_TODAY_ON_START=`) and reload — otherwise every
   subsequent launch wipes today again. Verify with another
   `launchctl unload && load` cycle that no `[BRIDGE STARTUP] Wiped`
   line appears.
8. Sanity check on yesterday's data after the wipe:
   ```bash
   sqlite3 data/mems26_local.db \
     "SELECT MIN(ts), MAX(ts), COUNT(*) FROM v9_bars_5min;"
   ```
   Expect: bars from yesterday and earlier survive; today's bars
   present only because Sierra has re-pushed them post-wipe.

---

## Pre-LIVE checklist

- [x] Code change is the smallest correct fix for each of A / B / C.
- [x] Backend untouched — no `/api/v9/bars/*` schema or contract drift.
- [x] No new `logger.debug` on failure paths (wipe uses `logger.warning`).
- [x] Regression test added under `tests/v9/bridge/`.
- [x] Targeted test suite passes (`pytest tests/v9/bridge/...` → 74 passed).
- [x] No DLL / LaunchAgent / CLOUD_URL / bridge token changes.
- [x] This report reflects post-implementation reality.

---

## Anything that needs a restart for the user?

| Component | When | Action |
|-----------|------|--------|
| Backend (`uvicorn`) | **No** | Frontend-only changes + bridge-side wipe; backend API unchanged. |
| Bridge | **Yes — only if using C** | `launchctl unload && launchctl load ~/Library/LaunchAgents/com.mems26.bridge.plist` (after setting `V9_BRIDGE_WIPE_TODAY_ON_START` in `.env`). |
| Frontend (Next dev) | Auto-reload | HMR picks up the chart changes; cockpit page reload safest. |
