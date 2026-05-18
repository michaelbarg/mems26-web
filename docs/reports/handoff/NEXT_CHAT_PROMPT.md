**Status:** SUPERSEDED for sessions on/after 2026-05-17 — see [`NEXT_CHAT_PROMPT_2026-05-17.md`](./NEXT_CHAT_PROMPT_2026-05-17.md)
**Last updated:** 2026-05-16
**Author:** Cursor multitask session

> **Note:** This file is kept for history only. The canonical handoff for the **post-P27.5a/c/d/e** state, with **Master Index V2** properly referenced as authoritative spec, is `NEXT_CHAT_PROMPT_2026-05-17.md` in this same folder.

# NEXT_CHAT_PROMPT — MEMS26 autonomous trading

> Paste the whole block below verbatim into a fresh chat (any reasonable model) to continue exactly where session `2026-05-16` ended. Then read the three sibling documents in this folder before taking any action.

Sibling living documents (read in this order after this prompt):

1. [`SESSION_LOG_2026-05-16.md`](./SESSION_LOG_2026-05-16.md) — what was actually changed/decided today
2. [`GANTT_TO_LIVE.md`](./GANTT_TO_LIVE.md) — phase plan, exit criteria, mermaid timelines
3. [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md) — ordered P## prompts from now → LIVE
4. Existing roadmap files: [`../SYSTEM_COMPLETION_CONTROL_BOARD.md`](../SYSTEM_COMPLETION_CONTROL_BOARD.md), [`../PROMPT27_REPLAY_VALIDATION_PLAN.md`](../PROMPT27_REPLAY_VALIDATION_PLAN.md), [`../PROMPT28_REPLAY_SMOKE_RUN.md`](../PROMPT28_REPLAY_SMOKE_RUN.md)

---

## ╭──────────────── PASTE FROM HERE ────────────────╮

You are resuming work on **MEMS26**, an autonomous trading system for **MES** (micro-S&P 500) futures, owned by Michael (single user, single machine, single account). The project is mid-stabilization on `stabilize/mems26-local-truth-2026-05-16` and a long context session just ended. The previous session produced four living handoff documents under `docs/reports/handoff/`; **read all four fully before executing anything**.

### Project context (one paragraph)

MEMS26 is a local autonomous trading system that ingests **Sierra Chart** market data via a DLL → `bridge/json_bridge.py` → FastAPI backend → Next.js (App Router) frontend. There are **6 systems** that each play a role inside the trading decision tree:

- **S1 Day Type** (OBSERVING, advisory) — classifies the trading day (Trend / Variation / Nontrend / etc.)
- **S2 Five-Min T1** (FIRING) — 5-min number-bar / Woodies-aligned pattern detection
- **S3 Footprint / Tick Reversal T3** (FIRING) — order-flow patterns (absorption, stacked imbalance, sweep, exhaustion)
- **S4 Woodies T2** (FIRING) — Woodies CCI 5-minute (post D-074 migration); decision tree A1–A7 live, B1–B14 delegated
- **S5 TPO** (OBSERVING, advisory) — market profile, POC migration, HVN/LVN
- **S6 Killzone** (OBSERVING + GATE) — time-of-day quality + WEEKEND/CLOSED hard gate

All flow into a `TradingGateway` with three slots: **SHADOW** (log-only), **DEMO** (Sierra Sim via `trade_command.json`), **LIVE** (real money). Activation is strictly **SHADOW → DEMO → LIVE**, each gated by Michael's manual UAT approval and quantitative soak criteria.

### Repository

- Root: `/Users/michael/Downloads/mems26_web_git`
- Branch: `stabilize/mems26-local-truth-2026-05-16`
- Remote: `origin` (do **not** push during handoff)
- Last verified HEAD: `419f4cc` ("fix: stabilize bridge startup diagnostics")
- Working tree on handoff date had only intentional, uncommitted frontend + script hardening (see `SESSION_LOG_2026-05-16.md`); **review `git status` before committing anything**.

### Current runtime snapshot (end of session 2026-05-16)

| Service | How it runs | Port | Stability notes |
|---|---|---|---|
| Bridge | `bash scripts/start_all.sh` (screen `mems26_bridge`) → `python3 bridge/json_bridge.py` | n/a | Must run with `V9_DISABLE_WATCHDOG=1` (polling, not fsevents). `launchd` plist also keeps it alive (`~/Library/LaunchAgents/com.mems26.bridge.plist`). |
| Backend | `screen mems26_backend` → `uvicorn backend.main:app --host 127.0.0.1 --port 8000` | 8000 | Healthy: `/api/v9/health` → `{"status":"ok","version":"v9.0.0"}`. |
| Frontend | `screen mems26_frontend` → `npm run dev` → `next dev -H 127.0.0.1` | 3000 | Must run with `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000` and shell-level `ulimit -n 10240` to avoid macOS `EMFILE` flood. |

Restart everything: double-click `~/Desktop/MEMS26 Restart.command`, or `bash scripts/restart_all.sh`. Status: `bash scripts/check_status.sh` and/or `bash scripts/run_stage.sh status_check`.

### Hard rules (do not break, regardless of model)

1. **No SHADOW activation** until every system is wired and the three backend integrity bugs below are fixed. The user has been explicit: "I do not want SHADOW until everything is wired." Do not flip `MEMS26_MODE=shadow` or any per-system `enable_shadow=true` flag.
2. **`lightweight-charts` is the approved chart library** (not the TradingView widget). The user re-approved this after a TradingView/lightweight-charts confusion. The data path must remain **Sierra → Bridge → Backend → Frontend**, all local; **no third-party live-data dependency** is allowed.
3. **Resource-exhaustion preventions are mandatory** on every restart:
   - Shell `ulimit -n 10240` (macOS default 256 caused the EMFILE flood that crashed the machine).
   - Bridge env `V9_DISABLE_WATCHDOG=1` (otherwise each stream opens its own FSEvents watcher and floods FDs).
   - Frontend env `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000`.
   - Frontend `next.config.ts` must keep `turbopack.root: process.cwd()` (otherwise Next scans all of `/Users/michael`).
   - Frontend dev must use `-H 127.0.0.1` (avoids `uv_interface_addresses` failure inside sandboxed shells).
4. **Do not regress D-074** (5-min Woodies migration). `woodies_5min` is the canonical Woodies timeframe; 30-min path is legacy. The DLL emits `woodies_5min.json`, the backend persists to `v9_bars_5min` and routes via `bar_router`.
5. **No Constitution / Master Index / MEMS26_FIRST decisions** may be added or modified without a fresh `D-###` decision number. The handoff documents themselves never contain new decisions; they only reference existing ones.
6. **No Sierra command writes** (`trade_command.json`) unless explicitly inside DEMO/LIVE work, which requires Michael's gate.

### Three critical backend issues that block SHADOW

Identified at the end of session 2026-05-16, **not yet fixed**. They block SHADOW activation because data integrity is non-negotiable (see `REQ-GOVERN-001..003` in `MEMS26_REGISTRY.yaml`).

| # | Endpoint / symptom | What we observed | Likely cause | Fix prompt |
|---|---|---|---|---|
| 1 | `GET /api/v9/chart/bars5min` returns rows with bad OHLC | bars with `low≈7172.5`/`7180.25` while the surrounding window is `~7440–7476` (~300-pt cliff). Client now filters them (`looksOk` in `ChartV5b.tsx`) but they should never leave the backend. | Suspected bad rows in `v9_bars_5min` ingestion (per-window aggregator or a leftover stale upsert). Check `bar_ingestion`/aggregator UPSERT logic. | **P27.5a** |
| 2 | `GET /api/v9/live_price` returns `age_ms ≈ 64 minutes` | Live current-price feed is stale by an hour+. The client now drops anything `> 60 000 ms` old, but the source pipeline must produce fresh prices during RTH. | Bridge stream for live tick is not pushing to the live_price topic, or the backend cache isn't being refreshed. | **P27.5b** |
| 3 | `GET /api/v9/tpo/current` reports `bars_processed_today=0` | Daily TPO aggregator never ran for "today" — POC/VAH/VAL may be carried-over or stale. | Aggregator's day-roll trigger or feed of 5-min bars into TPO is broken; possibly tied to issue #2 (no fresh data). | **P27.5c** |

All three must be GREEN before any SHADOW work. See `PROMPT_LIST_TO_LIVE.md` for the exact P27.5a/b/c specifications.

### What was done in this session (highlights)

- Frontend chart restored to **`ChartV5b`** (lightweight-charts) after an unrequested swap to `ChartV5a` + new poll hook had broken it. `V9Dashboard.tsx` simplified to a single chart pane (Volume panel + SystemPanelsBar removed per user direction).
- `ChartV5b.tsx` hardened: `attributionLogo: false`, UTC-safe `tsToUnix`, client-side `looksOk` outlier filter on bars, stale-price guard on live polling.
- `scripts/start_all.sh` hardened with `ulimit -n 10240` (shell + each screen session), backend bound to `127.0.0.1`, frontend launched with `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000`.
- `frontend/v9/next.config.ts` pinned `turbopack.root: process.cwd()`; `package.json` `dev` script forced `-H 127.0.0.1`.
- Desktop `MEMS26 Restart.command` created and hardened with `ulimit -n 10240`.
- Replay clock smoke (Prompt 28) ran 11/11 PASS (see `../PROMPT28_REPLAY_SMOKE_RUN.md`). System reliability still 6/6 READY per `../SYSTEM_COMPLETION_CONTROL_BOARD.md`.
- The 3 backend issues above were identified but explicitly **not fixed in this session** to stay surgical and avoid backend regressions during a frontend recovery.

Full details: [`SESSION_LOG_2026-05-16.md`](./SESSION_LOG_2026-05-16.md).

### Next action for the new chat

> **Read all four documents in `docs/reports/handoff/` fully, then execute the next prompt from [`PROMPT_LIST_TO_LIVE.md`](./PROMPT_LIST_TO_LIVE.md).** At the time of this handoff the next prompt is **P27.5a — Backend bad-bar fix** (followed by P27.5b live price freshness and P27.5c TPO aggregator). Do not jump to P28/P29/P29.5 until all three P27.5 prompts are GREEN.

### Do NOT

- Do **not** enable SHADOW / DEMO / LIVE.
- Do **not** modify `bridge/` or `backend/` files unless the active prompt explicitly directs it.
- Do **not** swap `lightweight-charts` for TradingView widget or any other charting source.
- Do **not** modify Constitution V3 / Master Index V2 / `MEMS26_FIRST.md` (if present) without a brand-new `D-###` decision and Michael's approval.
- Do **not** regress **D-074** (5-min Woodies migration); `woodies_5min` stays canonical.
- Do **not** remove `ulimit -n 10240`, `V9_DISABLE_WATCHDOG=1`, `WATCHPACK_POLLING=true`, `-H 127.0.0.1`, or `turbopack.root=cwd`.
- Do **not** delete `ChartV5b.tsx` or rewire `V9Dashboard.tsx` to a different chart component.
- Do **not** start spawning subagents for trivial steps; prefer a single focused worker per backend integrity fix.
- Do **not** commit/push without a green status check, a clean stage run report, and (where applicable) Michael's explicit go.

### Verification commands (safe, read-only)

```bash
cd /Users/michael/Downloads/mems26_web_git
git status -sb
bash scripts/check_status.sh
bash scripts/run_stage.sh status_check
curl -s http://127.0.0.1:8000/api/v9/health
curl -s http://127.0.0.1:8000/api/v9/clock/state
curl -s http://127.0.0.1:8000/api/v9/tpo/current     # check bars_processed_today
curl -s http://127.0.0.1:8000/api/v9/live_price      # check age_ms < 60000
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=50"  # eyeball OHLC sanity
```

## ╰──────────────── PASTE TO HERE ────────────────╯

---

## Conflicts to resolve

When you read existing roadmap files alongside the session transcript, you will find a few real conflicts. They must be reconciled (most likely by trusting the transcript and patching the older docs) before moving past P27.5:

1. **`SYSTEM_COMPLETION_CONTROL_BOARD.md` says "Bridge — GREEN — Running, 11 streams configured, pushing bars".** Transcript shows that during the resource-exhaustion incident the bridge fell over with `Cannot start fsevents stream` and `Cannot add watch ... already scheduled`, then was restarted with `V9_DISABLE_WATCHDOG=1`. It is GREEN again **only when started via the hardened `start_all.sh`**; the board entry should be footnoted accordingly.
2. **Board says all 6 systems "READY".** That status is for **system-internal correctness**, not end-to-end data integrity. The three backend issues above (bad bars, stale live_price, `bars_processed_today=0`) are *pipeline* issues that the board does not currently surface. They must be tracked as SHADOW blockers and the board updated after P27.5c.
3. **`SYSTEM_COMPLETION_CONTROL_BOARD.md` "Remaining Blockers → Before SHADOW"** lists "RTH live validation", "Replay Clock Mode" (now DONE per Prompts 26a/26b/27/28), and "SHADOW/DEMO/LIVE not enabled". It does **not** list the three P27.5 backend bugs — please add them after they have P-IDs assigned.
4. **Constitution / Master Index V2 / `MEMS26_FIRST.md`** are referenced as authoritative across the codebase but were **not found at the repository root** during this session. They likely live on Michael's Drive or are still being migrated locally. The transcript treats decisions D-001..D-074 as established. If a future chat cannot find them locally either, treat the local artefacts (`MEMS26_REGISTRY.yaml`, `compliance_manifest.yaml` per system, `SYSTEM_COMPLETION_CONTROL_BOARD.md`) as ground truth and ask Michael before authoring any new `D-###`.
5. **Replay Validation Plan (`PROMPT27_REPLAY_VALIDATION_PLAN.md`)** assumes the data path is healthy. Run P27.5a/b/c first or the replay scenarios will pass on bad data.
6. **`AGENTS.md` / `CLAUDE.md` (in `frontend/v9/`)** — if those files describe an older chart component (e.g., `ChartV5a`), reconcile with the live `V9Dashboard.tsx` that now uses `ChartV5b` exclusively.

---

*Sibling living docs cross-reference each other; keep them in sync as the project advances.*
