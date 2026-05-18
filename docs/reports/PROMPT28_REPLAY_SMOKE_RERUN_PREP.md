# P28 — Replay Smoke Rerun Preparation

**Date:** 2026-05-18
**Status:** PREPARED — blocked by Michael Phase 0 → Phase 1 gate

**No replay was run in this prep prompt.**

---

## Preconditions (all must be true before running P28)

1. **P27.5b GREEN** — `bash scripts/uat_prompt_27_5b_live_price.sh` returned 10/10 PASS with fresh Sierra data.
2. **Michael approves Phase 0 → Phase 1 gate** (explicit, in writing).
3. Backend running at `127.0.0.1:8000`.
4. Bridge running (for full system validation).
5. Sierra Chart running with MES chart (for live_price and bar feed).
6. Working tree: `stabilize/mems26-local-truth-2026-05-16`.

---

## Stale Assumptions in Current P28 Report

The existing `PROMPT28_REPLAY_SMOKE_RUN.md` was written 2026-05-16 at HEAD `d8246a9`
(Prompt 27). The following are now stale:

| Assumption | Old state | Current state |
|------------|-----------|---------------|
| HEAD | `d8246a9` | `555ef45` (P27.5f) — 3 commits ahead |
| "Ready for Prompt 29" | Claimed | **Not valid** — P27.5 pipeline fixes ship after P28 report |
| bars5min integrity | Not checked | P27.5a fixed bad-bar filter + slice bug |
| BarRouter thread safety | Not checked | P27.5c added `publish_threadsafe` |
| Footprint dispatch latency | Not checked | P27.5d added persistent WAL connection |
| 5min.partial topic | Did not exist | P27.5e added 1Hz throttled partial bars |
| five_min route instance | Used module-level `_system` | P27.5f fixed to `app.state.five_min_system` |
| live_price freshness | Not in scope | P27.5b GREEN — 10/10 PASS, age_ms<1s |
| `five_min/current` in status_check | Would return from orphan instance | Now returns from live `app.state` instance |

---

## P28 Rerun Runbook (execute after preconditions met)

### Step 0: Verify environment

```bash
cd /Users/michael/Downloads/mems26_web_git
git status --short --branch
# Expect: stabilize/mems26-local-truth-2026-05-16, clean or known untracked only

# Backend check
curl -sf http://127.0.0.1:8000/api/v9/health && echo "OK" || echo "FAIL"
```

### Step 1: Status check (all 6 systems)

```bash
bash scripts/stages/status_check.sh
```

Expected: All systems 200. If five_min returns 503, the FiveMinSystem failed to
initialize — diagnose before proceeding.

### Step 2: Replay clock smoke

```bash
bash scripts/stages/prompt_26_replay_clock_smoke.sh
```

Expected: 5/5 tests pass, Mode=REALTIME, Status=READY.

### Step 3: Post-P27.5 endpoint verification

```bash
# P27.5a: bars5min integrity
curl -s "http://127.0.0.1:8000/api/v9/chart/bars5min?limit=240" | \
  python3 -c "
import sys, json
d = json.load(sys.stdin)
rows = d if isinstance(d, list) else (d.get('data') or d.get('bars') or [])
bad = [r for r in rows if not (r['low'] <= min(r['open'],r['close']) and max(r['open'],r['close']) <= r['high'])]
print(f'count={len(rows)}  bad_count={len(bad)}  last_ts={rows[-1].get(\"ts\") if rows else \"EMPTY\"}')
"

# P27.5b: live_price freshness
bash scripts/uat_prompt_27_5b_live_price.sh

# P27.5c: TPO bars_processed_today
curl -s http://127.0.0.1:8000/api/v9/tpo/current | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'bars_processed_today={d.get(\"bars_processed_today\")}')"

# P27.5f: five_min uses live instance
curl -s http://127.0.0.1:8000/api/v9/five_min/current | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'hydrated={d.get(\"hydrated\")}  buffer_size={d.get(\"buffer_size\")}  mode={d.get(\"mode\")}')"

# Gateway: no DEMO/LIVE active
curl -s http://127.0.0.1:8000/api/v9/gateway/status | python3 -m json.tool
```

### Step 4: Targeted test suite

```bash
python3 -m pytest -q \
  tests/atomic/test_replay_clock_consumers.py \
  tests/v9/api/test_chart_bars5min_integrity.py \
  tests/v9/api/test_five_min_routes.py \
  tests/v9/services/test_bar_integrity.py \
  tests/v9/services/test_bar_router_threadsafe.py \
  tests/v9/services/test_aggregator_partial_publish.py
```

### Step 5: Full replay (if Steps 1-4 pass)

This is the actual P28 rerun — replay a historical session:

```bash
bash scripts/run_stage.sh prompt_26_replay_clock_smoke
```

Or, if a full-session replay script is built for P28, use that instead.

### Step 6: Update report

Update `docs/reports/PROMPT28_REPLAY_SMOKE_RUN.md`:
- Change HEAD to current commit
- Change date to run date
- Add "Post-P27.5" column to Pass/Fail Checklist
- Add new checks: bars5min integrity, five_min instance, TPO bars increment, live_price freshness
- Remove "Ready for Prompt 29" until all checks pass

---

## Acceptance Criteria (P28 goes GREEN when ALL pass)

| # | Check | Source | Criteria |
|---|-------|--------|----------|
| 1 | Backend health | `status_check.sh` | All 6 systems 200 |
| 2 | Replay clock mode transitions | `prompt_26_replay_clock_smoke.sh` | 5/5 tests pass |
| 3 | Clock REALTIME→REPLAY→REALTIME | Python probe | Clean transitions |
| 4 | S1 Day Type responds | `/api/v9/day_type/current` | classified=True during replay |
| 5 | S5 TPO responds | `/api/v9/tpo/current` | running=True, poc present |
| 6 | S6 Killzone uses clock | `/api/v9/killzone/current` | zone correct for replay time |
| 7 | S2/S3/S4 fire endpoints 200 | `/api/v9/{five_min,footprint,woodies}/fire` | 200, no 503 |
| 8 | No DEMO/LIVE active | `/api/v9/gateway/status` | demo_enabled=[], live_enabled=[] |
| 9 | BarRouter subscribers correct | Status/log check | Expected subscriber counts |
| 10 | No BarRouter SLOW handler warnings | Log check | 0 warnings >100ms during replay |
| 11 | No `trade_command.json` writes | File check | File not modified during replay |
| 12 | **NEW** bars5min integrity | P27.5a UAT | count=240, bad_count=0 |
| 13 | **NEW** five_min uses app.state | P27.5f | hydrated=true from endpoint |
| 14 | **NEW** TPO bars_processed increments | P27.5c | bars_processed_today > 0 during replay |
| 15 | **NEW** live_price freshness (pre-req) | P27.5b | Already GREEN before P28 starts |
| 16 | **NEW** Targeted test suite | pytest | All pass (currently 36 tests) |

### Failure Stop Rules

- If status_check fails → STOP. Diagnose which system is down.
- If replay clock smoke fails → STOP. Clock infrastructure regressed.
- If any new P27.5 check fails → STOP. Pipeline regression from P27.5 series.
- If BarRouter logs SLOW warnings → STOP. P27.5d regression.
- If `trade_command.json` is written → STOP IMMEDIATELY. Mode leak.

---

## Evidence Table Template (fill during actual run)

| Check | Expected | Actual | PASS/FAIL |
|-------|----------|--------|-----------|
| Backend health | 6×200 | — | — |
| Replay clock 5/5 | 5 pass | — | — |
| Clock transitions | Clean | — | — |
| S1 classified | True | — | — |
| S5 TPO running | True | — | — |
| S6 zone correct | For replay time | — | — |
| S2/S3/S4 fire 200 | 200 | — | — |
| Gateway clean | No DEMO/LIVE | — | — |
| BarRouter subscribers | Expected counts | — | — |
| No SLOW warnings | 0 | — | — |
| No trade_command writes | Unchanged | — | — |
| bars5min quality | bad_count=0 | — | — |
| five_min hydrated | true | — | — |
| TPO bars increment | >0 | — | — |
| live_price (pre-req) | GREEN | — | — |
| Targeted tests | All pass | — | — |

---

## Current Readiness Snapshot (2026-05-18, no replay run)

| Component | Status | Evidence |
|-----------|--------|----------|
| status_check.sh | Not run in this prep report | Must be run after P27.5b GREEN and Michael Phase 0 gate approval |
| replay_clock_smoke | Not run in this prep report | Must be run as part of P28 after gate approval |
| P27.5b live_price | GREEN | 10/10 PASS, `age_ms=178-982ms`, latency `1-6ms` |
| Targeted tests | Not run in this session | Expected 36 pass based on prior runs |

---

*No replay was run. No services started/stopped. No SHADOW/DEMO/LIVE activation.*
