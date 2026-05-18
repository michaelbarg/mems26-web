**Status:** living document — supersedes `NEXT_CHAT_PROMPT.md` for sessions on/after 2026-05-17
**Last updated:** 2026-05-18 (P27.5f closeout + P27.5z docs sync)
**Author:** Cursor (Opus 4.7) + Claude Code

# NEXT_CHAT_PROMPT — MEMS26 → SHADOW (post P27.5a/c/d/e/f)

> Paste the block under "PASTE FROM HERE" verbatim into a fresh chat (any reasonable model). The agent must read the four authoritative spec docs (see §0 below) **before** acting. Do not skip §0; it is the source of every naming / scope / governance decision.

Sibling living documents (read in this exact order after this prompt):

1. `docs/reports/handoff/SESSION_LOG_2026-05-16.md` — what was changed/decided on 2026-05-16
2. `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md` — P27.5a bad-bar fix + slice-bug regression (GREEN)
3. `docs/reports/PROMPT_27_5D_BAR_DISPATCH_LATENCY.md` — bar dispatch latency hardening (GREEN)
4. `docs/reports/PROMPT_27_5C_5MIN_DISPATCH_FIX.md` — `5min` topic dispatch + `5min.partial` topic (GREEN)
5. `docs/reports/POST_REBOOT_BRINGUP_2026-05-17.md` — bring-up after reboot
6. `docs/reports/SYSTEM_COMPLETION_CONTROL_BOARD.md` — per-system readiness (NOT pipeline)
7. `docs/reports/handoff/NEXT_CHAT_PROMPT.md` — older (2026-05-16) version, kept for context

---

## ╭──────────────── PASTE FROM HERE ────────────────╮

You are resuming work on **MEMS26**, an autonomous trading system for **MES** (micro-S&P 500) futures, owned by Michael (single user, single machine, single account). The repo is `/Users/michael/Downloads/mems26_web_git`, branch `stabilize/mems26-local-truth-2026-05-16`. We are in the **pre-LIVE** discipline phase: every change is small, tested, and reported. The cost of a mistake is real money.

### §0. Authoritative spec — read first, ask if missing

The authoritative spec for MEMS26 is, in priority order:

1. **Master Index V2** — the source of truth for taxonomy, system scope, the 21-stage Woodies decision tree, and the D-### decision authority.
2. **Constitution V3** — governance, the SHADOW → DEMO → LIVE mode rules, and risk caps (LIVE: $250/day, 5 trades, 2 contracts, no entries after 14:30 ET).
3. **`MEMS26_FIRST.md`** — D-### decision log (e.g. **D-074** locks Woodies to the 5-min timeframe).

These three live on Michael's Google Drive and are **not** in the repo.

Local mirrors / dependents (treat as derived, never as primary):

- `docs/MASTER_BUILD_CHECKLIST.md` — Terminal 1 build checklist (backend + systems).
- `docs/MASTER_BUILD_CHECKLIST_T2.md` — **"Master Index 2"** — Terminal 2 build checklist (DLL + Woodies + Layer 3). Tracks waves T2.1–T2.16.
- `MEMS26_REGISTRY.yaml` — requirements registry (REQ-…).
- `backend/v9/systems/*/compliance_manifest.yaml` — per-system specs (S1–S6).
- `.claude/MASTER_DEV_SKILL.md` — project skill, locked decisions, bug log.

**Hard rule:** if your task touches naming, taxonomy, system scope, governance, or proposes a new `D-###`, and Master Index V2 is **not** in your context, **STOP and ask Michael to paste it** before proceeding. Do not infer from the local mirrors alone. Do not invent a D-###; if you need one, write `(DRAFT — needs governance review)` and stop.

### §1. Pre-LIVE Agent Protocol (mandatory)

Full text: `.cursor/rules/mems26-pre-live-protocol.mdc` and the "Pre-LIVE Discipline" section of `CLAUDE.md`. Summary you must internalise:

1. **Diagnose first, fix second.** Verify the hypothesis with data (DB query, log read, probe) BEFORE touching code.
2. **Read the current code** before proposing any change. No edits from memory.
3. **Smallest correct change.** No "while I'm here" refactors. Add a regression test for every bug fix.
4. **4 UAT axes** for any data/chart endpoint:
   - **Quality** — the bad-data condition is gone (`bad_count=0`).
   - **Recency** — `endpoint.latest_ts == MAX(ts) FROM DB`.
   - **Cardinality** — `len(rows) == requested_limit`.
   - **Latency** — response time under documented threshold.
5. **No silent failures.** `logger.warning` (rate-limited) on push/connect errors, never `logger.debug`.
6. **One thread at a time.** Finish + report before opening the next P-ID.
7. **Update reports immediately** when state changes — `docs/reports/PROMPT_*.md` must not lag reality.
8. **Strategic stops.** Stop and ask Michael at phase gates, on plan contradictions, or before any change that affects trading logic, risk surface, or the SHADOW/DEMO/LIVE flag.

### §2. Project context

Data flow: **Sierra Chart (ACSIL DLL) → `bridge/json_bridge.py` → FastAPI `backend.main:app` (port 8000) → Next.js `frontend/v9` (port 3000)**. Local-only — the bridge **must not** push to any cloud URL. `CLOUD_URL` is hard-set to `http://localhost:8000` in three places (LaunchAgent, `scripts/start_all.sh`, `bridge/v9_streams/base_stream.py`); the latter raises `RuntimeError` at startup if not local.

6 systems (no cross-gating):

- **S1 Day Type** (OBSERVING, advisory) — Trend / Variation / Nontrend classification.
- **S2 Five-Min T1** (FIRING) — 5-min number-bar / Woodies-aligned patterns.
- **S3 Footprint / Tick Reversal T3** (FIRING) — order-flow patterns.
- **S4 Woodies T2** (FIRING) — Woodies CCI **5-min** (D-074); decision tree A1–A7 live, B1–B14 delegated.
- **S5 TPO** (OBSERVING, advisory) — market profile.
- **S6 Killzone** (OBSERVING + GATE) — time-of-day + WEEKEND/CLOSED hard gate.

Modes (strict order, no jumps): **SHADOW** (log-only) → **DEMO** (Sierra Sim, ONE slot first-wins) → **LIVE** (real money, ONE slot, hard caps).

### §3. Live status (verified 2026-05-17 23:50 UTC+3)

| Component | State | Evidence |
|---|---|---|
| Backend `:8000` | ✅ Running | `/api/v9/health` 200 OK |
| Frontend `:3000` | ✅ Running | screen `mems26_frontend` |
| Bridge | ⚠️ **STOPPED** | quiet baseline after P27.5d/c soak; restart before any RTH or replay validation |
| `live_price` | ⚠️ Stale `age_ms ≈ 46 min` | expected because bridge stopped; will recover on bridge restart |
| `chart/bars5min?limit=240` | ✅ Quality + Recency + Cardinality verified | `count=240`, `last_ts = DB MAX(ts) = 2026-05-17 16:15:00` |
| `tpo/current.bars_processed_today` | ✅ `2` (was `0`) | proves P27.5c `publish_threadsafe` actually delivers |
| Tests | ✅ 20/20 pass | `pytest tests/v9/services/test_bar_router_threadsafe.py tests/v9/services/test_aggregator_partial_publish.py tests/v9/api/test_chart_bars5min_integrity.py tests/v9/services/test_bar_integrity.py` |
| DB | 556 rows in `v9_bars_5min`, 7 today | sqlite query |
| Branch | `stabilize/mems26-local-truth-2026-05-16` | 12 modified + 6 untracked since `cfd5796` |

### §4. What shipped in the P27.5* series

- **P27.5a** — Backend bar integrity (`bar_is_valid` filters bad OHLC; `_fetch_bars_5min` over-fetches and slices `[-limit:]` to keep the **newest** rows). Regression test added. Report: `docs/reports/PROMPT_27_5A_BAD_BAR_FIX.md`.
- **P27.5d** — Bar dispatch latency. `FootprintSystem.process_bar` reuses a persistent WAL connection instead of `sqlite3.connect()` per bar. `BarRouter` instrumented (`SLOW handler` warning >100ms; total dispatch warning >50ms). Report: `docs/reports/PROMPT_27_5D_BAR_DISPATCH_LATENCY.md`.
- **P27.5c** — `5min` topic dispatch fix. `BarRouter.bind_main_loop()` + `BarRouter.publish_threadsafe()` (uses `asyncio.run_coroutine_threadsafe`). All callers (`bars.py:_route_bar`, `bar_aggregator_5min:_on_bar_close_default`) switched. Proof: `tpo.bars_processed_today` increments. Tests: `tests/v9/services/test_bar_router_threadsafe.py` (2). Report: `docs/reports/PROMPT_27_5C_5MIN_DISPATCH_FIX.md`.
- **P27.5e** — Live partial-bar topic. `FiveMinAggregator.on_tick` publishes `"5min.partial"` at 1 Hz (`is_partial=True`) for the in-progress bar; no subscribers yet (opt-in for Phase 6 decision engine). Tests: `tests/v9/services/test_aggregator_partial_publish.py` (2).
- **P27.5f** — Five-min route instance fix. `routes.py` rewired to use `request.app.state.five_min_system` instead of a separate module-level `FiveMinSystem()`. Returns 503 if system not initialized. 8 regression tests added. Report: `docs/reports/PROMPT_27_5F_FIVE_MIN_ROUTE_INSTANCE_FIX.md`.
- **Local-only bridge enforcement** — `LaunchAgent`, `start_all.sh`, `base_stream.py` all hard-set `CLOUD_URL=http://localhost:8000`; `URLError` promoted from `debug` to rate-limited `warning`.

Git note: verify `git status -sb` before any new work. Do not assume this handoff's file list is current after a commit/push.

### §5. Known pre-existing issues (NOT in current scope)

1. ~~`/api/v9/five_min/current` route uses a separate `FiveMinSystem()` instance`~~ — **FIXED in P27.5f** (GREEN). Route now uses `request.app.state.five_min_system`. Report: `PROMPT_27_5F_FIVE_MIN_ROUTE_INSTANCE_FIX.md`.
2. ~~`SYSTEM_COMPLETION_CONTROL_BOARD.md` does not yet surface the P27.5* fixes~~ — **FIXED in P27.5z** (GREEN). Pipeline integrity section added.
3. **P27.5b `live_price.age_ms < 60000`** — DEFERRED. Requires RTH with bridge running. Cannot validate during weekend.

### §6. Outstanding work to SHADOW (7 phases)

Order is fixed. Do **not** skip a gate.

1. **P27.5b — Live-price freshness during RTH.** Start bridge only when Michael explicitly asks for RTH/live validation; verify `/api/v9/live_price age_ms < 60000` for 10 consecutive checks. If it fails, diagnose bridge stream/cache root cause before editing.
2. **Phase 1 — Replay Smoke (P28).** After P27.5b is GREEN and Michael approves the Phase 0 gate, run Sierra Replay across one full RTH session, verify all 4 UAT axes on every endpoint, verify `tpo.bars_processed_today` increments to expected count, verify `BarRouter` logs no `SLOW handler` warnings.
3. **Phase 2 — Replay Scenario Pack (10 scenarios).** Trend, range, gap, lunch chop, FOMC, etc. Each scenario produces a numbered report. Stop and ask Michael at any anomaly.
4. **Phase 3 — Data Collection Package.** Wire SHADOW-mode logs that capture every signal + decision tree state for Michael's review. No orders.
5. **Phase 4 — Frontend Design for SHADOW supervision.** Dashboard fit for genuine human supervision (not "looks fine"). Define what Michael needs to see: live signals, near-misses, decision-tree stage, system votes, gate state.
6. **Phase 4.5 — SHADOW Readiness Gates** (all three required, GREEN, signed off):
   - **Accuracy Gate** — every data path validated end-to-end on at least 2 sessions of replay.
   - **Decision Tree Gate** — A1–A7 + B-stages firing per Master Index V2 spec; signal log inspectable.
   - **Design Gate** — dashboard approved by Michael for genuine supervision.
7. **Phase 5 — SHADOW Activation.** Flip mode, log only, run for the agreed soak period. Strategic review (Phase 6.0 in the master plan) before extending.

After SHADOW passes its soak: **Phase 6 (DEMO)** then **Phase 7 (LIVE)** — both gated by Michael.

### §7. Hard rules — never break

1. **No SHADOW / DEMO / LIVE activation** until all gates above are GREEN and Michael has signed off. Do not flip `MEMS26_MODE=shadow` or any per-system `enable_shadow=true` flag.
2. **Bridge is local-only.** The bridge must push to `http://localhost:8000` only. Never `mems26-web.onrender.com` or any external host. Never relax the `localhost` enforcement in `base_stream.py`.
3. **Resource-exhaustion preventions are mandatory** on every restart:
   - Shell `ulimit -n 10240`.
   - Bridge env `V9_DISABLE_WATCHDOG=1`.
   - Frontend env `WATCHPACK_POLLING=true CHOKIDAR_USEPOLLING=true CHOKIDAR_INTERVAL=1000`.
   - Frontend `next.config.ts` keeps `turbopack.root: process.cwd()`.
   - Frontend dev uses `-H 127.0.0.1`.
4. **Do not regress D-074** (5-min Woodies). `woodies_5min` is canonical.
5. **No new D-### decisions** without Michael's explicit approval and Master Index V2 review.
6. **No `trade_command.json` writes** outside DEMO/LIVE work, which requires Michael's explicit gate.
7. **`lightweight-charts` is the approved chart library**. Do not swap to TradingView widget. Data path stays Sierra → Bridge → Backend → Frontend, all local.
8. **No `git push`** during a handoff or fix unless the user explicitly says "push". Commit only when the user asks.
9. **No subagents for trivial steps.** Prefer one focused worker per P-ID.

### §8. Verification commands (safe, read-only)

```bash
cd /Users/michael/Downloads/mems26_web_git
git status -sb
git log --oneline -10

# Service health
curl -s http://127.0.0.1:8000/api/v9/health
curl -s http://127.0.0.1:8000/api/v9/clock/state

# 4-axis UAT (P27.5a/c/e)
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=240" | python3 -c "import sys,json; d=json.load(sys.stdin); rows=d if isinstance(d,list) else (d.get('data') or d.get('bars') or []); print('count=', len(rows), 'last_ts=', rows[-1].get('ts') if rows else 'EMPTY')"
curl -s http://127.0.0.1:8000/api/v9/tpo/current | python3 -c "import sys,json; d=json.load(sys.stdin); print('bars_processed_today=', d.get('bars_processed_today'))"
curl -s http://127.0.0.1:8000/api/v9/live_price

# DB ground truth
python3 -c "import sqlite3; c=sqlite3.connect('data/mems26_local.db').cursor(); c.execute('SELECT COUNT(*), MAX(ts) FROM v9_bars_5min'); print(c.fetchone())"

# Tests
pytest -q tests/v9/services/test_bar_router_threadsafe.py tests/v9/services/test_aggregator_partial_publish.py tests/v9/api/test_chart_bars5min_integrity.py tests/v9/services/test_bar_integrity.py
```

### §9. First action for the new chat

> P27.5a/c/d/e/f are GREEN. P27.5z docs sync is complete. The remaining Phase 0 item is **P27.5b** (live_price freshness), which requires RTH with bridge running.
>
> **Next step:** Wait for RTH (Sunday evening futures open or Monday 9:30 ET). Start bridge, then run P27.5b UAT: `curl -s http://127.0.0.1:8000/api/v9/live_price` must return `age_ms < 60000` for 10 consecutive checks. If P27.5b passes, Phase 0 is complete and Phase 1 (Replay Smoke) can begin.

If any §8 result disagrees with §3, **stop** and produce a discrepancy report — do not patch silently.

## ╰──────────────── PASTE TO HERE ────────────────╯

---

## Notes for the operator (Michael)

- This file is the canonical handoff for sessions starting **on/after 2026-05-17**. The older `NEXT_CHAT_PROMPT.md` (2026-05-16) is preserved for history.
- If you need an even shorter handoff for a tight context window, paste only §0 + §1 + §3 + §6 + §9. The rest can be read on demand.
- After the next bridge-running RTH soak, **revise §3 and §6** to reflect the new state. Don't let this file lag behind reality.
