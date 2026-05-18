# Prompt 28: Replay Smoke Run — Post-P27.5 Rerun

**Date:** 2026-05-18  
**HEAD:** `2466a66`  
**Status:** GREEN — smoke PASS, full `tests/v9/` suite PASS  
**No SHADOW/DEMO/LIVE enabled. No bridge start/stop. No trade command writes.**

---

## Commands Run

| # | Command | Result |
|---|---------|--------|
| 1 | `git status --short --branch` | Branch `stabilize/mems26-local-truth-2026-05-16`, ahead 2, docs/logs dirty from this session |
| 2 | `bash scripts/run_stage.sh status_check` | PASS — health + all 6 systems 200 |
| 3 | `bash scripts/run_stage.sh prompt_26_replay_clock_smoke` | PASS — 5/5 tests, clock `REALTIME`, status `READY` |
| 4 | Post-P27.5 endpoint verification probe | PASS — bars/live_price/TPO/five_min/fire endpoints healthy |
| 5 | Gateway status probe | PASS for mode safety — `demo_enabled_systems=[]`, `live_enabled_systems=[]`, slots `None` |
| 6 | Targeted pytest suite | PASS — 33/33 |
| 7 | `bash scripts/run_stage.sh prompt_27_replay_plan` | PASS — plan exists + 11/11 integration tests |
| 8 | `python3 -m pytest tests/v9/ -q` | Initial FAIL — 9 failed, 1234 passed, 1 skipped |
| 9 | Safe triage fixes for trade schema + stream counts | PASS — targeted 5/5 |
| 10 | `python3 -m pytest tests/v9/ -q` rerun | FAIL — 4 failed, 1239 passed, 1 skipped |
| 11 | Apply Michael policy clarification for Day Type/Killzone | PASS — Day Type requires prior-day context; D-061 makes Killzone observational/tag-only |
| 12 | `python3 -m pytest tests/v9/ -q` final | PASS — 1244 passed, 1 skipped |

Stage logs:
- `docs/reports/stage_runs/status_check_20260518_112858.log`
- `docs/reports/stage_runs/prompt_26_replay_clock_smoke_20260518_112904.log`
- `docs/reports/stage_runs/prompt_27_replay_plan_20260518_113019.log`

---

## Post-P27.5 Endpoint Evidence

| Check | Evidence | Status |
|-------|----------|--------|
| `/api/v9/chart/bars5min?limit=240` | HTTP 200, latency 48.4ms, count=240, bad_count=0, `last_ts == DB MAX(ts) == 2026-05-17 16:15:00.000000` | PASS |
| `/api/v9/live_price` | HTTP 200, latency 6.3ms, price=7413.0, age_ms=704, valid JSON | PASS |
| `/api/v9/tpo/current` | HTTP 200, latency 5.2ms, `bars_processed_today=2`, `running=True`, `poc=7522.0` | PASS |
| `/api/v9/five_min/current` | HTTP 200, latency 2.1ms, `hydrated=True`, `mode=WEEKEND` | PASS |
| `/api/v9/five_min/fire` | HTTP 200, `fired=False` | PASS |
| `/api/v9/footprint/fire` | HTTP 200, `fired=False` | PASS |
| `/api/v9/woodies/fire` | HTTP 200, `fired=False` | PASS |
| `/api/v9/killzone/current` | HTTP 200, `running=True`, `clock_mode=REALTIME`, current zone `LONDON` | PASS |
| `/api/v9/clock/now` | HTTP 200, mode `REALTIME`, status `READY`, `is_rth_open=False` | PASS |
| `/api/v9/gateway/status` | HTTP 200, `demo_enabled_systems=[]`, `live_enabled_systems=[]`, `demo_slot=None`, `live_slot=None`, `shadow_active_count=0` | PASS for mode safety |

Watch item: `/api/v9/gateway/status` consistently returned in ~2.0s. This did
not violate the P28 mode-safety check, but should be tracked if gateway status
latency becomes operationally important.

---

## Pass/Fail Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | Backend health 200 | PASS |
| 2 | All 6 system current endpoints 200 | PASS |
| 3 | Replay clock smoke tests | PASS — 5/5 |
| 4 | MarketClock module state | PASS — `REALTIME`, `READY` |
| 5 | bars5min quality | PASS — bad_count=0 |
| 6 | bars5min cardinality | PASS — count=240 |
| 7 | bars5min recency | PASS — endpoint last_ts equals DB MAX(ts) |
| 8 | live_price freshness | PASS — age_ms=704 in post-P27.5 probe; P27.5b 10/10 PASS |
| 9 | TPO current responds | PASS — running=True, bars_processed_today=2 |
| 10 | five_min current uses live instance | PASS — hydrated=True |
| 11 | S2/S3/S4 fire state endpoints 200 | PASS |
| 12 | No DEMO/LIVE command path active | PASS — enabled lists empty, slots None |
| 13 | Targeted regression tests | PASS — 33/33 |
| 14 | Replay plan integration stage | PASS — 11/11 |
| 15 | Full `tests/v9/` suite | PASS — 1244 passed, 1 skipped |

**Result: P28 GREEN.**

---

## Scope Note

The repository currently exposes three stage scripts:

- `scripts/stages/status_check.sh`
- `scripts/stages/prompt_26_replay_clock_smoke.sh`
- `scripts/stages/prompt_27_replay_plan.sh`

There is no separate full-session historical replay stage script in
`scripts/stages/`. This report therefore records the completed P28 smoke rerun
against the available automation, plus the post-P27.5 endpoint checks. It does
not claim that a new full-session replay injector was created or run.

---

## Failures/Blockers

Full `tests/v9/` initially failed with 9 failures. Triage results:

| Failing area | Resolution |
|--------------|------------|
| Trade model/API compatibility | Fixed route/WebSocket mapping from legacy `dominant_system` payloads to current `firing_system` schema. |
| Stream count expectations | Aligned stream health with canonical bridge registry by adding `live_price`; tests now assert canonical count. |
| Day Type policy | Per Michael clarification: prior-day context is required for trading. Missing PD remains `A1` / `UNKNOWN` / `DEGRADED`; test updated. MatrixCell keeps V2 probabilities and supports top1 compatibility. |
| Killzone policy | Per Michael clarification: D-061 is authoritative. Killzone zones are observational/tag context, not hard blockers; hard blocks come from trading calendar, manager disable, news/risk/mode controls. |

Final full-suite result: `1244 passed, 1 skipped`.

Residual watch item:
- Gateway status latency was ~2.0s across three samples.

---

## Ready for Prompt 29

**Technically ready pending Michael's Phase 1 → Phase 2 approval.** Do not
start P29 until Michael explicitly approves the Phase 1 exit gate.

---

*No SHADOW/DEMO/LIVE enabled. No push.*
