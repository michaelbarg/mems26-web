# P31 — Journal P&L (range / MFE / MAE / legs) + S2 Five-Min

**Date:** 2026-05-21 (afternoon)
**Owner:** Cursor (verification + report); Michael (UI eyeball + RTH); CC (delegated future bridge/RTH ops)
**Scope:** Single thread — journal/excursion/legs/context backend + UI; S2 BarRouter UPDATE code path. **No** bridge/DLL/LaunchAgent changes.

---

## TL;DR

- **P31-04 Journal mehir + naxon (code):** ✅ `/trades/log` returns range, MFE/MAE, T1 proximity, ordered legs (ENTRY/T1/T2/T3/STOP/EXIT), partial vs realized P&L. **0.02s** at `limit=50` post-restart.
- **P31-01 P&L UAT (one trade verified):** ✅ trade **697** — DB `pnl_usd=56.25` ↔ API `pnl_usd=56.25`; Hi/Lo/MFE/MAE consistent with 5m bars in window. Awaiting Michael UI eyeball + a second exit in RTH.
- **P31-09 prev_day extraction:** ✅ committed `5b75101` — `backend/v9/systems/day_type/prev_day.py` (136 LOC, was untracked) + 5 pytest cases.
- **P31-02 S2 five-min — root cause identified, fix applied (dormant until restart):**
  - 🔴 `FiveMinSystem.process_bar` was ~8s/bar because of 5–9 synchronous `requests.get` self-calls to `localhost:8000` (footprint/tpo). 93-thread leak + backend hang were downstream symptoms.
  - ✅ `12b376f` `fix(five_min): in-process footprint reads + Sierra TPO file load (no HTTP self-calls) [P31-02b]` — `set_footprint_system()` setter, `_footprint_state()` helper, direct `_load_sierra_tpo()` call. Graceful HTTP fallback retained. 9 new pytest cases (74/74 five_min PASS).
  - ✅ `0f5960d` `feat(main): inject FootprintSystem into FiveMinSystem at startup [P31-02b]` — wire-up in `backend/main.py:380-386` (7 lines, surgically separated from 100+ unrelated prior-session main.py changes via "Approach K" partial-staging non-interactive).
  - ❌ `43f5399` thread-leak fix (`run_coroutine_threadsafe`) — REVERTED via `04514a6` after source review showed it would deadlock the FastAPI loop on the now-removed HTTP self-calls. Re-application (P31-02c) is safe **after** P31-02b is verified live.
- **P31-PAT (bonus):** historical ZLR detection works — 2,294 ZLR signals in `v9_woodies_signals` (incl. 7 today). Michael cross-checking against Sierra.
- **Pre-LIVE position:** journal/exits/range code complete; S2 perf root cause fixed in code (commits ready, awaiting backend restart for verification); thread leak still present until P31-02c.

---

## What was built (code + tests)

### Backend services (new / extended)

| File | Purpose |
|------|---------|
| `backend/v9/services/trade_excursion.py` | `compute_trade_excursion(trade)` → `price_high`, `price_low`, `mfe_pts`, `mae_pts`, `t1_closest_pts`, `t1_at_mfe_pts`, `t1_reached`, `bars_count`. `_trade_window` uses `min(entry_ts, t1/t2/t3_hit_ts, stop_hit_ts)` so trades with late-logged entry still get the right bar window. `prefetch_bars_for_trades` runs **one** SQL query for the whole journal batch. |
| `backend/v9/services/trade_legs.py` | `extract_trade_legs(trade)` → ordered list of `{event, price, ts, reason?}` for ENTRY → T1/T2/T3 hits → STOP/EXIT. Stop-hit synthesizes exit price from `trade.stop` when `exit_price is None`. |
| `backend/v9/services/trade_context.py` (extended) | `compute_trade_pnl` → `{pnl_usd, pnl_r, pnl_mode in [closed, partial, open], contracts_pnl[]}`. Partial P&L = realized hits only; open contracts = $0. Reuses `_valid_target` to ignore `0.0`/`None` targets. |
| `backend/v9/api/journal_compat_routes.py` | `_v9_row_to_journal` adds `price_high/low`, `mfe_pts/mae_pts`, `t1_closest_pts`, `trade_legs`, `pnl_mode`, `duration_min`, `range_note`. Uses prefetched bar cache + `load_only(_JOURNAL_TRADE_COLUMNS)` to skip the ~25 KB `cross_context` blob in list view. |

### Frontend UI

| File | Change |
|------|--------|
| `frontend/v9/src/v9/types/index.ts` | Added `price_high/low`, `mfe_pts/mae_pts`, `t1_closest_pts`, `t1_at_mfe_pts`, `t1_reached`, `bars_count`, `pnl_mode`, `contracts_pnl`, `stop_initial`, `stop_note`, `stop_issue`. |
| `frontend/v9/src/v9/components/trades/tradeRowFormat.ts` | `excursionLine`, `tradePathLine`, `pnlCell`, `contractsPnlLine`, `contractHits`, `systemsAgreementLine`. |
| `frontend/v9/src/v9/components/trades/TradesTable.tsx` | New columns: Path, Range/T1, Systems S1–S6, C1–C3, Pattern, P&L (realized). Click row → expand. |
| `frontend/v9/src/v9/components/trades/TradeRowExpand.tsx` | Per-system recognition at entry (S1–S6), agree/against/neutral chip, fire highlighted. |
| `frontend/v9/src/v9/components/trades/TradesSummaryStrip.tsx` | Total P&L, partial count, wins/losses/scratch/open, by-system breakdown. |
| `frontend/v9/src/app/journal/page.tsx` | `Hi`/`Lo` columns; `MAE`/`MFE` show `—` when null; modal includes `Range Hi`, `Range Lo`, `MAE`, `MFE`, `Range source`, and a `כניסה / יציאה / פגיעות` block listing legs. |

### Tests (all passing — `pytest tests/v9/...` 14/14)

| Suite | Cases |
|-------|-------|
| `tests/v9/services/test_trade_excursion.py` | SHORT MFE/MAE/T1 proximity; window uses hit_ts when entry logged late; LONG T1 not reached → closest distance. |
| `tests/v9/services/test_trade_context.py` | extract from quality+entry_row; legacy dict cross_context; gateway top-level keys; PARTIAL pnl_mode=2 hits; insight headline + recognition list. |
| `tests/v9/api/test_journal_excursion.py` | `_v9_row_to_journal` returns range when bars exist; legs include ENTRY+T1; `mfe_pts ≥ 0`. |
| `tests/v9/api/test_journal_compat_sql.py` | mode filter applied **before** LIMIT; respects `limit`; demo excluded when `types=shadow`. |
| `tests/v9/api/test_journal_compat_routes.py` | `/trades/log?types=shadow&limit=5` returns shadow rows; `/analytics/setups/today_summary` shape. |

```text
14 passed, 4 warnings in 0.53s
```

---

## Live UAT (post-restart, 2026-05-21 צהריים)

Backend PID **45069** on `127.0.0.1:8000`. Bridge running (5min only). Frontend on `127.0.0.1:3000`.

### Four UAT axes — `/trades/log?types=shadow&limit=50`

| Axis | Measurement | Threshold | Status |
|------|-------------|-----------|--------|
| Quality | API `pnl_usd=56.25` for trade 697 ↔ DB `pnl_usd=56.25` | Equal | ✅ |
| Recency | API `max(id)=697` ↔ DB shadow `MAX(id)=697` | Equal | ✅ |
| Cardinality | API `len=21` ↔ DB `COUNT(*) WHERE LOWER(mode)='shadow' = 21` (`limit=50`, no truncation) | Equal | ✅ |
| Latency | `time curl …limit=50` → **0.02s** | < 5s | ✅ |

### Trade 697 spot-check (LONG · CLOSED · manual exit)

DB row:

```text
id=697  state=CLOSED  direction=LONG  entry_price=7429.25  stop=7426.75
t1=7433.0  t2=7436.75  t3=0.0  t1_hit=1  t2_hit=1
exit_reason=manual  pnl_usd=56.25
t1_hit_ts=2026-05-20 15:55:00   t2_hit_ts=2026-05-20 15:55:00
exit_ts=2026-05-21 07:52:53
```

API `/trades/log` row 697:

```text
direction=LONG · status=CLOSED
entry_price=7429.25 · exit_price=7429.25
pnl_usd=56.25 · pnl_mode=closed
price_high=7446.75 · price_low=7426.25      ← from v9_bars_5min in window
mfe_pts=17.5 (= 7446.75 − 7429.25)          ← LONG: high − entry
mae_pts=3.0  (= 7429.25 − 7426.25)          ← LONG: entry − low
t1_hit=True · t2_hit=True · t3_hit=False
duration_min=31.4
trade_legs (sorted by ts):
  T1    7433.00  @ 2026-05-20 15:55
  T2    7436.75  @ 2026-05-20 15:55
  ENTRY 7429.25  @ 2026-05-21 07:48
  EXIT  7429.25  @ 2026-05-21 07:52  reason=manual
```

Note: t1/t2 hit timestamps precede the entry timestamp on this trade — likely an artifact of replay/test data. The journal handles it correctly via `_trade_window = min(stamps)`, and the bar window covers the full price range.

### S2 (P31-02) — full thread, end of session 2026-05-21 15:47

**Commits this session:**

| commit | what | status |
|--------|------|--------|
| `5b75101` | `feat(day_type): extract prev_day loader to standalone module + tests [P31-09]` | ✅ kept |
| `43f5399` | `fix(bar_router): publish_threadsafe uses run_coroutine_threadsafe [P31-02]` | ❌ caused S2 silent stop |
| `04514a6` | `revert: bar_router publish_threadsafe ... (regression in S2 fire path) [P31-02]` | ✅ reverted |
| `12b376f` | `fix(five_min): in-process footprint reads + Sierra TPO file load (no HTTP self-calls) [P31-02b]` | ✅ |
| `0f5960d` | `feat(main): inject FootprintSystem into FiveMinSystem at startup [P31-02b]` | ✅ |

**Root cause of 8s SLOW handler:** `FiveMinSystem.process_bar` made 5–9 synchronous `requests.get(...)` self-calls to `localhost:8000` (timeout=2s each) — see `backend/v9/systems/five_min/five_min_system.py:290,299,344,434,480,519`. ~9 × ~0.9s = ~8s.

**Why the first fix (`43f5399`) regressed:** moving `publish_threadsafe` to schedule on the FastAPI main loop (instead of spawning a thread per bar) made `process_bar` run on that loop. The 9 synchronous `requests.get` self-calls then blocked the very loop that needed to serve the self-calls — every call timed out, returned None, and `_detect_reactive`/`_detect_initiative` early-returned `(None, 0, {})`. S2 silently stopped firing. The regression test used `AsyncMock` as the subscriber, which doesn't reproduce the production handler's blocking behavior. **Lesson:** the thread leak and the synchronous self-calls are coupled — removing the leak alone amplifies the blocking issue.

**P31-02b — root cause fix (`12b376f`):**

`FiveMinSystem` (`backend/v9/systems/five_min/five_min_system.py`):

- New `set_footprint_system(footprint_system)` setter (mirrors existing `set_gateway` pattern from Prompt 14/22-alt).
- New `_footprint_state()` helper: prefers `self._footprint_system.get_current()` if injected; falls back to legacy HTTP self-call when not injected (preserves backward compatibility for tests / pre-wire instances).
- `_get_cot_from_footprint`, `_get_amt_from_footprint`, `_get_belly_from_footprint` simplified to read from `_footprint_state()` — same return contract, single source of truth.
- `_compute_location_vs_poc` now imports and calls `backend.v9.api.v9.tpo_routes._load_sierra_tpo()` directly. HTTP fallback retained.

Tests (`backend/v9/systems/five_min/tests/test_in_process_footprint.py` — new, 9 cases):

- Injected path skips HTTP (`requests.get` patched to raise — passes if never called).
- Defensive: `get_current` raising returns empty dict; missing `belly_ratio_dominant` returns None (not False).
- Legacy path (no injection) still works via HTTP.
- Full `process_bar` with injected footprint makes zero HTTP calls.
- `_compute_location_vs_poc` prefers Sierra file over HTTP.

Result: `74/74` five_min tests pass; `86/87` broader regression (1 unrelated pre-existing failure).

**P31-02b — wire-up (`0f5960d`):**

`backend/main.py` adds 7 lines after the existing `set_gateway` block (~line 380):

```python
        # P31-02b: inject FootprintSystem into FiveMinSystem so process_bar
        # reads cot/amt/belly in-process (~1ms) instead of HTTP self-calls (~8s).
        if hasattr(app.state, 'five_min_system') and app.state.five_min_system \
           and hasattr(app.state, 'footprint_system') and app.state.footprint_system:
            app.state.five_min_system.set_footprint_system(app.state.footprint_system)
            _logger.info("[Main] S2 FiveMinSystem ← footprint_system injected (P31-02b)")
```

**Approach K — non-interactive partial staging.** `backend/main.py` had ~100 unrelated prior-session changes (extraction of inline `_load_previous_day_context` + `_missing_pd_context`, `import asyncio`, `journal_compat_router` import, …). To keep the wire-up commit clean (7 lines, no bundling), the following sequence was used:

1. `cp backend/main.py /tmp/main_PRIOR.py` — backup the prior-session state.
2. `StrReplace` on working tree → `WIRED` = `PRIOR + 7 lines`.
3. `cp backend/main.py /tmp/main_WIRED.py` — backup the wired state.
4. `git checkout HEAD -- backend/main.py` — reset main.py to HEAD baseline (set_gateway block is identical in HEAD and PRIOR — verified before the reset).
5. `StrReplace` again on baseline (same target text, same insertion) → `BASELINE + 7 lines`.
6. `git add backend/main.py && git commit` — clean commit, `1 file changed, 7 insertions(+)`.
7. `cp /tmp/main_WIRED.py backend/main.py` — restore working tree to `WIRED` (PRIOR + 7).
8. `rm /tmp/main_*.py` cleanup.

Final state: HEAD = `BASELINE + 7 wire-up lines`; working tree = `PRIOR + 7 wire-up lines`. `git diff backend/main.py` now shows only the 100 prior-session changes (the wire-up matches between HEAD and working tree). Each step verified with size + md5 + diff before proceeding.

**P31-02c (next, awaiting explicit approval) — re-apply thread-leak fix:**

Once a backend restart loads `0f5960d`, a synthetic POST `/api/v9/bars/5min` should produce `BarRouter: dispatch total <100ms for 5min` (was ~8000ms). Once verified, the `run_coroutine_threadsafe` change from reverted `43f5399` can be re-applied — at that point `process_bar` no longer blocks the FastAPI loop, so scheduling on it is safe and removes the per-bar thread leak. Net: thread leak gone + S2 fires + 100× perf — all three.

**Current state (until backend restart):** code committed; runtime still on the 8s slow path (graceful fallback) with the thread leak; daily backend restart bounds the leak to one trading session.

### S2 (P31-02) — synthetic firing 2026-05-21 14:13 (original synthetic test)

POST `/api/v9/bars/5min` with same `ts` as latest DB row (data-safe UPDATE):

```bash
curl -X POST http://127.0.0.1:8000/api/v9/bars/5min \
  -H "X-Bridge-Token: $TOKEN" \
  -d '[{"ts": 1779347100, "symbol": "MES", "o": 7433.25, "h": 7433.25, "l": 7433.25, "c": 7433.25, "vol": 14}]'
```

**Result:** `http=000 t=115s` (curl TCP-timed-out). DB row count unchanged (1469 rows; safe).

**Backend log produced:**

```text
2026-05-21 14:13:32 [WARNING] BarRouter: SLOW handler FiveMinSystem.process_bar took 8027.7ms
2026-05-21 14:13:32 [WARNING] BarRouter: dispatch total 8045.3ms for 5min
```

| Finding | Evidence | Severity |
|---------|----------|----------|
| ✅ P31-02 code path verified | BarRouter routed the UPDATE to `FiveMinSystem.process_bar` | Green |
| 🔴 `FiveMinSystem.process_bar` consistently ~8s/bar | 16 SLOW warnings in 4 minutes (8013–8062ms) | **Pre-LIVE blocker** |
| 🔴 Thread leak | 93 threads in backend; `publish_threadsafe` (`bar_router.py:42`) spawns a fresh `threading.Thread` running `asyncio.run()` per bar — accumulate when handler is slow | **Pre-LIVE blocker** |
| 🔴 Backend hung under load | `curl /api/v9/health` from CLI = `http=000 t=5.0s` ×3; PID changed 45069→50472; frontend connection-pool still 200 OK | **Pre-LIVE blocker** |
| 🔴 Stream silence | `v9_woodies_signals` newest = 10:32 IL · `v9_bars_5min` newest = 10:15 IL · clock at 14:25 IL → 4h silence | **Pre-LIVE blocker** |

**Bridge state:** running in `--bars-5min-only` mode (terminal 191521), so woodies/footprint/tpo streams aren't being pushed. Combined with `process_bar` slowness, the system can't handle even partial flow.

**Hand-off:**
- **CC** investigating bridge/backend recovery (active).
- **Michael** verifying historical ZLR signals vs Sierra (active — 2,294 ZLR detections in `v9_woodies_signals` to validate).
- **Cursor** (this section): documented the finding; not opening a fix thread.

The original P31-02 line in the executive table above (🟡 code only, awaiting RTH) is **superseded** by 🔴 process_bar perf + thread leak. P-S0 gate is now blocked on these, not just RTH.

---

## Known minor (non-blocking)

| Issue | Where | Impact | Status |
|-------|-------|--------|--------|
| Duplicate `day_type` key in dict literal | `journal_compat_routes.py:_v9_row_to_journal` (was lines 170 & 176) | Last-wins → no functional impact; cosmetic noise | ✅ Fixed this session — second occurrence removed; `pytest tests/v9/api/test_journal_*.py` 6/6 pass |
| `prefetch_bars_for_trades` returns `[]` → fallback to per-row DB query | `_v9_row_to_journal` else-branch | Performance only; current measurement 0.02s for 21 rows so not visible | Defer |
| Backend `/api/v9/cockpit/systems-snapshot` first-call latency ~2s | Pre-existing (P30) | Cockpit cold-start, not journal-related | Not P31 scope |

---

## What's still open

| Task | Owner | Blocker |
|------|-------|---------|
| Journal UI eyeball — trade 697 row + modal (Hi/Lo/MFE/MAE/legs) | Michael | None — `localhost:3000/journal` + `/trades` ready |
| Second exit UAT (T1 → real STOP) | Michael in RTH | RTH window |
| S2 fire UAT — `/api/v9/five_min/current` shows fire after a 5m bar | CC-C in RTH | RTH + Sierra |
| P31-PAT — `active_patterns` populated when Sierra shows pattern | Michael+CC in RTH | RTH + ≥20 woodies bars |
| P-S0 SHADOW soak gate | Michael sign-off | All four above |

---

## Files changed this session (committed locally, NOT pushed)

5 commits ahead of `origin/stabilize/mems26-local-truth-2026-05-16` (was 13, now 18):

| commit | files | LOC |
|--------|-------|-----|
| `5b75101` | `backend/v9/systems/day_type/prev_day.py` (new); `tests/v9/systems/test_day_type/test_prev_day.py` (new) | +248 |
| `43f5399` (reverted) | `backend/v9/services/bar_router.py`; `tests/v9/services/test_bar_router_threadsafe.py` | +84 / -5 |
| `04514a6` (revert of 43f5399) | same files | +5 / -84 |
| `12b376f` | `backend/v9/systems/five_min/five_min_system.py`; `backend/v9/systems/five_min/tests/test_in_process_footprint.py` (new) | +224 / -24 |
| `0f5960d` | `backend/main.py` (7 lines, surgically separated from 100+ unrelated prior-session changes via Approach K) | +7 |

**Uncommitted in working tree (preserved, prior session work):** `.gitignore`, `CLAUDE.md`, `backend/main.py` (100+ lines of unrelated prior-session changes — extraction of inline `_load_previous_day_context` + `_missing_pd_context` etc.), `backend/v9/api/v9/{bars,bars_5min_history,cumulative_delta_routes,tpo_routes,trades,woodies_chart_routes}.py`, `backend/v9/app.py`, `backend/v9/db/models/bars_5min.py`, `backend/v9/gateway/trading_gateway.py`, `backend/v9/services/trade_manager/{bar_level_detector,manager}.py`, `bridge/json_bridge.py`, `bridge/v9_streams/base_stream.py`, `bridge/v9_history.py`, plus many docs and frontend files. These belong to other P-IDs (P30 final, prior P31 work, etc.) and should be triaged separately.

**Untracked from this session (not yet committed):** `backend/v9/api/journal_compat_routes.py`, `backend/v9/services/{trade_excursion,trade_legs,trade_context}.py`, `frontend/v9/src/app/journal/page.tsx`, `frontend/v9/src/v9/components/trades/{TradeRowExpand,TradesSummaryStrip,tradeRowFormat}.tsx,ts`, plus their tests. These were the original P31-04 work; remain uncommitted because they bundle with the other modified main.py / trades.py changes. Triage candidate for P31-04 commit once main.py is split.

---

## Decision log

- **D-Journal-1:** Range/MFE/MAE source = `v9_bars_5min`. Bar resolution means wicks between bars can be missed. UI shows `—` (not 0) when no bars in window. Documented in `_v9_row_to_journal: range_note`.
- **D-Journal-2:** `trade_legs` prices = planned target/stop prices from `v9_trades` row, not the exact tick at hit. Pre-LIVE this matches our DB truth source (Sierra exports OHLC bars, not per-tick fills).
- **D-Journal-3:** `pnl_mode=partial` shows realized P&L of hit contracts only; open C3 contributes $0 (matches MES contract semantics with C1/C2/C3 split). Closed trades use `trade.pnl_usd` from TradeManager directly.
- **D-S2-1 (P31-02b):** FiveMinSystem reads footprint state in-process via setter injection (not via HTTP self-calls or `app.state` lookup). Justifications: (a) handler runs on BarRouter thread without `request` context, ruling out `request.app.state`; (b) setter mirrors existing `set_gateway` pattern; (c) constructor injection would require touching every `FiveMinSystem()` call site (5+) and break tests that bare-instantiate. Graceful HTTP fallback retained for backward compatibility.
- **D-S2-2 (P31-02b):** `_compute_location_vs_poc` reads Sierra `tpo.json` directly via `_load_sierra_tpo()` rather than going through `app.state.tpo_system`. Reason: the route `/api/v9/tpo/current` itself ignores `tpo_system` in favor of the Sierra file (the file is the source of truth). Direct call eliminates HTTP roundtrip + JSON serialization (~500ms saved per process_bar invocation).
- **D-S2-3 (P31-02 → 02c):** Thread-leak fix (`run_coroutine_threadsafe`) is correct in isolation but unsafe while `process_bar` does synchronous self-I/O. Sequencing locked: P31-02b (in-process reads) MUST land + verify before P31-02c (re-apply thread-leak fix).

---

## Pointers

- Code (P31-04 journal): `backend/v9/services/{trade_excursion,trade_legs,trade_context}.py`, `backend/v9/api/journal_compat_routes.py`.
- Code (P31-02b S2 perf): `backend/v9/systems/five_min/five_min_system.py`, `backend/main.py:380-386` (wire-up).
- Code (P31-09 prev_day): `backend/v9/systems/day_type/prev_day.py`.
- UI: `frontend/v9/src/app/journal/page.tsx`, `frontend/v9/src/v9/components/trades/`.
- Tests: `tests/v9/services/test_trade_*.py`, `tests/v9/api/test_journal_*.py`, `tests/v9/systems/test_day_type/test_prev_day.py`, `tests/v9/services/test_bar_router_threadsafe.py`, `backend/v9/systems/five_min/tests/test_in_process_footprint.py`.
- Board: `docs/handoff/P31_TASK_BOARD.md` (single source of truth, §6.1–§6.4 cover the S2 thread).
- Sister report: `docs/reports/PROMPT_P31_CC_B_RESTART_UAT.md` (CC-B restart steps).

---

## Verification — 2026-05-21 15:55 ✅ LIVE PASS

Restart sequence executed (after `kill` and `kill -9` failed against stuck PID 50472, `pkill -9 -f "uvicorn backend.main"` succeeded):

```bash
pkill -9 -f "uvicorn backend.main"
sleep 3   # port :8000 now free
cd /Users/michael/Downloads/mems26_web_git && set -a && source .env && set +a
nohup python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 \
  >> /tmp/backend.log 2>&1 &
disown
# wait ~30s for hydrate; backend PID = 82330
```

**4 UAT axes for `BarRouter: dispatch ... for 5min`:**

| Axis | Before (PID 50472) | After (PID 82330) | Status |
|------|--------------------|--------------------|--------|
| Quality | 16 SLOW warnings in 4min, range 8013–8062ms | 0 SLOW warnings since restart | ✅ |
| Recency | dispatches stuck at 8s steady state | 7 dispatches captured (live bridge + synthetic POSTs) | ✅ |
| Cardinality | bars accumulating in dispatcher | no backlog observed; bars processed promptly | ✅ |
| Latency | ~8000ms (16× slow vs target) | **62-231ms, mean ~106ms (75× faster)** | ✅ |

**Auxiliary live evidence:**
- Live S4 trade routed: `2026-05-21 15:56:09 [INFO] [Gateway] SHADOW trade TM id=701: SHORT GB100 system=4` — Woodies fired and gateway accepted, proving the upstream pipeline didn't break.
- 5 synthetic POSTs to `/api/v9/bars/5min` (curl timed out at 5s due to TCP accept-queue backlog under heavy frontend polling — separate issue) but backend processed all of them. 4 dispatch lines visible in log: 62.8ms, 89.0ms, 231.3ms, 78.1ms.

**Wire-up log line not visible.** The `_logger.info("[Main] S2 FiveMinSystem ← footprint_system injected (P31-02b)")` does not appear in `/tmp/backend.log`. Historical search shows this is **pre-existing** — the `[Main]` prefix from `backend/main.py:_logger` has never appeared in the log file (also true for the existing `set_gateway` lines). Logging-config drift, not a regression. The 75× empirical speedup confirms the wire-up is functional.

**Out-of-scope findings (logged for future sessions):**

- `BarRouter: SLOW handler WoodiesSystem.process_bar took 18155ms` — `WoodiesSystem` has the same pattern of synchronous self-calls. Likely a P31-02d candidate (apply the same setter-injection fix to `S4 WoodiesSystem`).
- `sqlalchemy.exc.PendingRollbackError: ... Object of type datetime is not JSON serializable` on `INSERT INTO v9_trades` (TLB trade with rich `quality.metadata`). Trade insertion fails, session needs explicit rollback. Likely a serialization bug in `Gateway` or `TradeManager` quality serialization.
- `[Main]` log prefix not visible — backend/main.py logger config drift; cosmetic for now.

## Next: P31-02c (re-apply thread-leak fix)

With process_bar verified <250ms and not blocking the FastAPI loop, the original `bar_router.publish_threadsafe` fix from reverted commit `43f5399` becomes safe to re-apply: scheduling on the main loop via `run_coroutine_threadsafe` no longer deadlocks because the handler doesn't HTTP-self-call. Net result: no thread leak + S2 fires + 75× perf — all three.

Cherry-pick (after explicit approval):

```bash
git cherry-pick 43f5399                 # re-apply the reverted fix
# or:
git diff 04514a6 43f5399 -- backend/v9/services/bar_router.py \
                            tests/v9/services/test_bar_router_threadsafe.py | git apply
git commit -m "fix(bar_router): re-apply run_coroutine_threadsafe (now safe post-P31-02b) [P31-02c]"
```

Expected post-restart: same dispatch latency (<250ms) but bar-router thread count flat over many synthetic POSTs (was leaking 1/push).
