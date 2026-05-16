**Status:** living document — update as the project advances
**Last updated:** 2026-05-16
**Author:** Cursor multitask session

# SESSION_LOG — 2026-05-16

Companion documents:

- [`NEXT_CHAT_PROMPT.md`](./NEXT_CHAT_PROMPT.md)
- [`GANTT_TO_LIVE.md`](./GANTT_TO_LIVE.md)
- [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md)
- [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md)
- [`../PROMPT27_REPLAY_VALIDATION_PLAN.md`](../PROMPT27_REPLAY_VALIDATION_PLAN.md)
- [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md)

> Branch: `stabilize/mems26-local-truth-2026-05-16` · Last commit on branch at end of session: `419f4cc` ("fix: stabilize bridge startup diagnostics") · Working tree at end of session contains intentional uncommitted hardening (see "Files touched" below).

---

## Chronological narrative (high level)

| Approx. local time | What happened |
|---|---|
| Morning (≤13:00 ET) | Re-read of Master Index, registry, compliance manifests; planning what to send to CC (Claude Code). |
| 13:00–14:30 | Prompt 23 + Prompt 24 series completed (CC): Woodies runtime contract proven, Control Board reconciled. |
| 14:30–16:30 | Prompts 25, 25b, 26a, 26b completed: cross-system integration proof; replay clock mode wired (`MarketClock` + consumers `TPO` + `TradeManager`). |
| 16:30–18:00 | Prompt 27 — replay validation plan + stage runner; Prompt 28 — replay smoke run **11/11 PASS** (see [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md)). |
| 18:00–19:00 | Bridge startup diagnostics stabilized (commit `419f4cc`). |
| 19:00–19:40 | **Resource-exhaustion incident**: machine ran out of file descriptors (`EMFILE` flood from Next.js Watchpack + bridge fsevents); shell wedged with `forkpty: Resource temporarily unavailable`. User restarted Mac. |
| 19:40–20:10 | Recovery: identified root causes; hardened `start_all.sh`, `next.config.ts`, `package.json`, created Desktop `.command`. Brought bridge + backend + frontend back online with `ulimit -n 10240`, `V9_DISABLE_WATCHDOG=1`, `WATCHPACK_POLLING=true`. |
| 20:10–20:20 | Frontend chart restored: `ChartV5b` (lightweight-charts) re-instated; `V9Dashboard` simplified to single pane; `VolumePanel` + `SystemPanelsBar` removed per user direction; `attributionLogo: false`, UTC `tsToUnix`, `looksOk` outlier filter, stale-price guard added. **Three backend data integrity bugs identified** and explicitly **not** fixed in-session (kept for P27.5a/b/c). |
| 20:20–20:21 | User requested this handoff package. |

---

## Code changes (file : what changed : why)

| File | What changed | Why |
|---|---|---|
| `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx` | Added `attributionLogo: false` to chart layout; rewrote `tsToUnix` to force UTC (`+ 'Z'` when no TZ suffix present); added `looksOk(b)` outlier filter applied to `loadBars`, the 3-bar polling refresh, and the pan-to-load history fetcher; added stale-price guard (drop `live_price` if `age_ms > 60 000`). | Restore chart that the user remembered ("lightweight-charts table that worked"); remove the two duplicate "T7" watermarks; defend against the bad backend data found at the end of session (until P27.5a/b lands). |
| `frontend/v9/src/v9/components/layout/V9Dashboard.tsx` | Removed all `useState`/`useEffect`/drag-handle/preset logic for resizable `chartH`; removed `VolumePanel` import and render block; removed `SystemPanelsBar` render block; left layout: `TopBar → Layer0Strip → flex-1 ChartV5b → TradeHistoryStrip → ShadowSoakStrip → SidePanel → BannerStack`. | User asked for a single-pane chart (no second pane with second watermark and empty volume). |
| `frontend/v9/next.config.ts` | Added `turbopack: { root: process.cwd() }`. | Prevent Next/Turbopack from indexing `/Users/michael` (root) when launched from the wrong cwd — was a contributor to the file-watcher flood. |
| `frontend/v9/package.json` | Changed `"dev": "next dev"` → `"dev": "next dev -H 127.0.0.1"`. | Avoid `uv_interface_addresses` failure inside sandboxed shells; pin frontend to localhost. |
| `scripts/start_all.sh` | Added top-level `ulimit -n 10240`; `bridge` start script (`/tmp/start_bridge.sh`) also calls `ulimit -n 10240`; backend `screen` session now runs `ulimit -n 10240` then `uvicorn --host 127.0.0.1 --port 8000`; frontend `screen` session now runs `ulimit -n 10240` then `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000 npm run dev`. | Eliminate the EMFILE root cause (macOS default `ulimit -n` is 256, far too low for Next.js Watchpack + bridge fsevents). |
| `~/Desktop/MEMS26 Restart.command` (created) | Bash script that `cd`s into the repo, `ulimit -n 10240`, prints git status, runs `restart_all.sh`, `check_status.sh`, `run_stage.sh status_check`. Marked executable. | Single double-click recovery path requested by the user. |
| `bridge/v9_streams/__pycache__/...` | Pycache regenerated; no source changes. | Side effect of bridge restarts. |

Note: previous-session commit `419f4cc` ("fix: stabilize bridge startup diagnostics") landed in this session **before** the resource-exhaustion incident; it is the last commit on the branch.

---

## Architectural decisions confirmed (no new D-### created)

| Decision | Restated as | Notes |
|---|---|---|
| Chart library | `lightweight-charts` (open-source Apache 2.0 library from TradingView Inc.) is the approved charting library. | Explicitly **not** the TradingView widget; **no** third-party data feed. Data flow is `Sierra → Bridge → Backend → Frontend`. |
| Chart component | `ChartV5b` is the canonical chart; `ChartV5a` and `DashboardLayout` are legacy and must not be re-wired. | `ChartV5b.tsx` exists at `frontend/v9/src/v9/components/chart/v5b/`. |
| Dashboard panes | Single-pane layout: chart fills the center column; `VolumePanel` (separate pane) and `SystemPanelsBar` (bottom S1–S6 strip) are **removed from `V9Dashboard`**. | Volume histogram, if desired, must be **overlaid inside `ChartV5b`** to avoid a second chart instance / second watermark. |
| Resource caps | Mandatory environment on every restart: `ulimit -n 10240`, `V9_DISABLE_WATCHDOG=1`, `WATCHPACK_POLLING=true`, `CHOKIDAR_USEPOLLING=true`, `CHOKIDAR_INTERVAL=1000`, `next dev -H 127.0.0.1`, `turbopack.root=cwd`. | Encoded in `scripts/start_all.sh` and the Desktop `.command` so a human can't forget. |
| SHADOW preconditions | SHADOW is not enabled until **every** system is wired AND the three backend integrity bugs are fixed. | Explicit user requirement reiterated several times in chat. |
| Replay clock | `MEMS26_CLOCK_MODE=REPLAY` is the supported test mode; `MarketClock` injects replay timestamps; consumers (TPO, TradeManager, Killzone, DayType) honor it. | Wired in commits `e09ecaf` (P26a) and `fd626dd` (P26b); proven in `../PROMPT28_REPLAY_SMOKE_RUN.md`. |
| Sierra command path | Only `DemoExecutor` and `LiveExecutor` may write `trade_command.json`. SHADOW is record-only. | "First-wins" gating across SHADOW/DEMO/LIVE preserved (`REQ-S-060`). |
| D-074 | 5-min Woodies migration is canonical; 30-min path is legacy. | DLL emits `woodies_5min.json`; backend persists to `v9_bars_5min`; `bar_router` routes `woodies_5min`. Must not be regressed. |

---

## Bug fixes done in this session

| Bug | Symptom | Fix |
|---|---|---|
| `EMFILE: too many open files, watch` flood from Next.js Watchpack | Frontend wedged; chain reaction to backend; eventually `forkpty: Resource temporarily unavailable` from any shell. | `ulimit -n 10240` (shell + each `screen` session) + `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000` for the frontend `screen`. |
| Bridge `Cannot start fsevents stream`/`Cannot add watch ... already scheduled` cascade | Bridge crashed / leaked FDs when each of 11 streams opened its own fsevents watcher on the same Sierra export folder. | Bridge runs with `V9_DISABLE_WATCHDOG=1` (polling mode); `scripts/start_all.sh` exports it explicitly. |
| `next dev` failing with `uv_interface_addresses` | Frontend crashed on launch in sandboxed shells. | `frontend/v9/package.json` `dev` script forces `-H 127.0.0.1`. |
| `next dev` scanning `/Users/michael` as Turbopack root | Frontend opened thousands of watchers immediately. | `frontend/v9/next.config.ts` pinned `turbopack: { root: process.cwd() }`. |
| `ChartV5b` was deleted and `V9Dashboard` was re-wired to `ChartV5a` + a new poll hook by an unrequested change | Chart/panels appeared broken to the user. | Restored `ChartV5b.tsx` and `V9Dashboard.tsx` to working state; deleted the unrequested `usePriceRestPoll` hook file. |
| Two lightweight-charts watermarks visible | Two chart instances were rendering (`ChartV5b` + `VolumePanel`); each carried its own `attributionLogo`. | `attributionLogo: false` added inside `ChartV5b.tsx`; `VolumePanel` removed from `V9Dashboard`. |
| Chart showing 3 wildly off-band candles dipping to ~7160 | Backend returned bars with broken `low`/`close` fields. | Client-side `looksOk` filter added (defense in depth) — **backend fix tracked as P27.5a** because the bad rows still leave the API. |
| `tsToUnix` parsing backend timestamps as local time | Candles "clustered" on the right edge after polling refreshes. | `tsToUnix` now appends `'Z'` when no TZ marker is present. |
| Live polling sometimes pushed 64-min-old `live_price` into the forming bar | "Outlier" wicks; bar appearing to move when it shouldn't. | Client-side stale guard (`age_ms > 60000` → drop) — **backend fix tracked as P27.5b**. |
| Bridge launchd plist resurrected old daemons after a kill | After `pkill` the bridge came back immediately and reconsumed the leaking watchers. | `launchctl unload ~/Library/LaunchAgents/com.mems26.bridge.plist` documented in recovery runbook; bridge restarted only via the hardened `start_all.sh`. |

---

## Infrastructure hardening

| Item | Detail |
|---|---|
| `scripts/start_all.sh` | Now sets `ulimit -n 10240` at the top, inside the bridge starter, inside the backend `screen`, and inside the frontend `screen`. Backend host changed to `127.0.0.1`. Frontend env set to `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000`. |
| `~/Desktop/MEMS26 Restart.command` | New executable bash script: `ulimit -n 10240` → `cd repo` → print git status → `bash scripts/restart_all.sh` → `bash scripts/check_status.sh` → `bash scripts/run_stage.sh status_check` (if present). |
| `frontend/v9/next.config.ts` | `turbopack: { root: process.cwd() }` — prevents Turbopack from scanning the user home. |
| `frontend/v9/package.json` | `dev` script pinned to `next dev -H 127.0.0.1`. |
| Bridge launchd | `~/Library/LaunchAgents/com.mems26.bridge.plist` still in place; KeepAlive=true. Recovery runbook documents how to `launchctl unload` it when needed to investigate. |
| Status visibility | `bash scripts/check_status.sh` and `bash scripts/run_stage.sh status_check` are the canonical health probes. Both detect HTTP listeners; `pgrep`-only detection was unreliable inside Cursor's sandbox. |

---

## Bugs identified but NOT fixed in this session

These three are the **only** identified items that block SHADOW. They are scheduled as **P27.5a / P27.5b / P27.5c** in [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md):

1. **`GET /api/v9/chart/bars5min` returns outlier OHLC rows.** Observed bars with `low≈7172.5`/`7180.25` while the surrounding window was `~7440–7476`. Client-side `looksOk` filter masks it but the backend should never emit these rows. Suspect: per-window 5-min aggregator UPSERT or stale rows surviving the session-cumulative cleanup. See `REQ-W5.4`.
2. **`GET /api/v9/live_price` returns `age_ms ≈ 64 minutes`.** Live-price pipeline is not delivering fresh prices. Client now drops anything `> 60 s`, but RTH must produce fresh data. Suspect: a bridge stream isn't pushing to the live-price topic, or the backend cache is stuck.
3. **`GET /api/v9/tpo/current` reports `bars_processed_today=0`.** Daily TPO aggregator is not running for "today"; POC/VAH/VAL may be carried over or stale. Suspect: `MarketClock` day-roll trigger or wrong feed source.

All three remain **OPEN** at the end of session 2026-05-16.

---

## Files touched (review with `git diff HEAD`)

Confirmed uncommitted on `stabilize/mems26-local-truth-2026-05-16`:

```text
 M bridge/v9_streams/__pycache__/__init__.cpython-39.pyc
 M bridge/v9_streams/__pycache__/base_stream.cpython-39.pyc
 M frontend/v9/next.config.ts
 M frontend/v9/package.json
 M frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx
 M frontend/v9/src/v9/components/layout/V9Dashboard.tsx
 M scripts/start_all.sh
?? docs/reports/stage_runs/status_check_20260516_175609.log
?? docs/reports/stage_runs/status_check_20260516_181530.log
?? docs/reports/stage_runs/status_check_20260516_200030.log
```

Plus the four handoff documents created at end-of-session under `docs/reports/handoff/` (this file is one of them).

Per-file line-range hot spots in the modified frontend chart (relative to HEAD):

- `frontend/v9/src/v9/components/chart/v5b/ChartV5b.tsx`
  - `tsToUnix` rewritten (lines ~11–15)
  - new `looksOk` helper (lines ~17–28)
  - `layout.attributionLogo: false` (~line 54)
  - `looksOk` filter applied at `loadBars` (line ~109), live polling (~line 153), 3-bar refresh (~line 182), pan-to-load fetcher (~line 207)
  - stale-price guard in live polling (~line 155)

- `frontend/v9/src/v9/components/layout/V9Dashboard.tsx`
  - removed lines that imported `useState`, `useCallback`, `useRef`, `useEffect` (line 2)
  - removed local constants `STORAGE_KEY`, `MIN_H`, `DEFAULT_H`, `MAX_H`, `PRESETS`, `clamp`
  - removed `chartH`/`hydrated`/drag-handle state and effects
  - removed `VolumePanel` render block (resizable split, presets row)
  - removed `SystemPanelsBar` render block
  - final layout: TopBar / Layer0Strip / center column with `ChartV5b` flex-1 + `TradeHistoryStrip` + `ShadowSoakStrip` / SidePanel / BannerStack

- `scripts/start_all.sh`
  - `ulimit -n 10240` after `set -a; source .env; set +a` (top of file)
  - bridge starter (`/tmp/start_bridge.sh` heredoc) gains `ulimit -n 10240`
  - backend `screen` command gains `ulimit -n 10240` + `--host 127.0.0.1`
  - frontend `screen` command gains `ulimit -n 10240` + `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000`

- `frontend/v9/next.config.ts` — `turbopack: { root: process.cwd() }` added.

- `frontend/v9/package.json` — `dev` script gains `-H 127.0.0.1`.

---

## Outstanding from previous sessions still in play

| Item | State | Reference |
|---|---|---|
| D-074 Woodies 5-min migration | DONE end-to-end; must not regress | commits `ca286b6`, `7e73f64`; tracked across `MEMS26_REGISTRY.yaml` |
| Replay clock mode | DONE in P26a (`e09ecaf`) + P26b (`fd626dd`); proven in Prompt 28 11/11 PASS | [`../PROMPT26A_REPLAY_CLOCK_MODE.md`](../PROMPT26A_REPLAY_CLOCK_MODE.md), [`../PROMPT26B_REPLAY_CLOCK_CONSUMERS.md`](../PROMPT26B_REPLAY_CLOCK_CONSUMERS.md), [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md) |
| Cross-system integration proof | DONE in P25 + P25b | [`../PROMPT25_CROSS_SYSTEM_INTEGRATION_PROOF.md`](../PROMPT25_CROSS_SYSTEM_INTEGRATION_PROOF.md) |
| S1 Day Type `/current` canonical V9 source + V1 demotion | DONE (Prompt 20b); `pd_high/pd_low/pd_close` wired from `v9_bars_5min` (Prompt 21/21b/21c) | [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md) §S1 |
| S4 Woodies runtime contract proof | DONE (Prompt 23); A1–A7 live, B1–B14 delegated | [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md) §S4 |
| Stage runner + replay validation plan | DONE (Prompt 27) | [`../PROMPT27_REPLAY_VALIDATION_PLAN.md`](../PROMPT27_REPLAY_VALIDATION_PLAN.md) |
| Per-trade DB schema (separate from terminals) — P1 backlog | Still pending | listed in transcript "P1 — לפני LIVE" |
| Real DLL pattern reads for non-HFE Woodies patterns (8 patterns still Python-only?) | Still pending | listed in transcript "P1 — לפני LIVE" |
| `pre_fire_validator` Wave 2 (cool-down, daily cap, stop-range checks) | Still pending | listed in transcript "P1 — לפני LIVE" |
| B6 `news_calendar.next_window()` implementation | Logic written; service existence unverified | listed in transcript |
| Slack `SLACK_WEBHOOK_URL` end-to-end | Plumbing exists, webhook config inconsistent in some commits | listed in transcript |
| `scripts/daily_check.sh`, `scripts/shadow_status.sh` | Pending | listed in transcript |
| Predicted vs Actual interface per system (`REQ-DATA-004..006`) | SPECIFIED, not implemented | `MEMS26_REGISTRY.yaml` |
| Admin/Operator console (`REQ-ADMIN-001..005`) | SPECIFIED, not implemented | `MEMS26_REGISTRY.yaml` |
| Constitution V3 / Master Index V2 / `MEMS26_FIRST.md` | Referenced as authoritative across the codebase but not found locally during this session — likely on Drive | check before any new `D-###` |

---

## Verification (read-only) at end of session

```bash
cd /Users/michael/Downloads/mems26_web_git
git status -sb                       # see "Files touched" table above
bash scripts/check_status.sh         # bridge + backend + frontend GREEN
bash scripts/run_stage.sh status_check
curl -s http://127.0.0.1:8000/api/v9/health                     # {"status":"ok",...}
curl -s http://127.0.0.1:8000/api/v9/clock/state                # REALTIME / READY
curl -s http://127.0.0.1:8000/api/v9/tpo/current                # WARNING bars_processed_today=0
curl -s http://127.0.0.1:8000/api/v9/live_price                 # WARNING age_ms very large
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=50"  # WARNING outliers present
```

---

*No SHADOW / DEMO / LIVE was enabled during this session. No push.*
