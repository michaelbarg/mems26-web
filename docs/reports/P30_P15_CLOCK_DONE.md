# P30 P1.5 Market Clock — Audit Done

**Date:** 2026-05-20  
**Verdict:** **PARTIAL** — soak-ready; one Drive gap deferred  
**Owner:** Cursor Parent  
**Parallel:** D-088 deploy verify — other agent (`WAVE_1B_D088_DEPLOY_VERIFY_PROMPT.md`)

---

## CLOCK-1..5 table

| ID | Item | Status | Path / notes |
|----|------|--------|----------------|
| CLOCK-1 | Market Clock service | **KEEP** | `backend/v9/services/market_clock.py` — D-068, holidays, REPLAY |
| CLOCK-2 | `GET /api/v9/clock/now` | **KEEP** | `clock_routes.py` + `app.py` include |
| CLOCK-3 | Open Type 4 types | **KEEP** | `open_type.py` + `/api/v9/open_type/current` (D-072) |
| CLOCK-4 | IB width 10-day percentile | **DEFER** | `classify_ib_width()` uses fixed 15/25 pt — not rolling percentile per Drive System 1 Data Reqs |
| CLOCK-5 | `GET /api/v9/tpo/previous_day` | **ADAPT** | Route kept; body via `prev_day.load_tpo_previous_day_summary()` |

---

## Commits (this wave)

| # | Change |
|---|--------|
| 1 | `tpo_routes.py` — CLOCK-5 dedupe → `prev_day` module |

No new `market_clock.py` rewrite (already ~250 LOC).

---

## Tests

| Suite | Result |
|-------|--------|
| `pytest tests/v9/systems/test_day_type/test_prev_day.py -q` | 5 passed |
| `backend/v9/tests/test_replay_clock_mode.py` | exists (replay clock) |
| Dedicated `/clock/now` API test | **missing** — optional P2 |

---

## Four-axis UAT (local — after backend restart)

Run when HTTP up (delegate agent post D-088):

```bash
curl -s http://127.0.0.1:8000/api/v9/clock/now | jq '{status,mode,session_date,is_rth_open}'
curl -s http://127.0.0.1:8000/api/v9/tpo/previous_day | jq '{found,session_date,poc,vah,val}'
curl -s http://127.0.0.1:8000/api/v9/open_type/current | jq '{status,type}'
```

---

## DEFER: CLOCK-4 (Michael before / after soak)

**Gap:** Drive asks 10-day rolling IB width **percentile**; code uses static thresholds in `detector.classify_ib_width`.

**Estimate:** ~50 LOC + DB query last 10 `v9_tpo_sessions.ib_width` + test.

**Does not block:** SHADOW soak (S1 already classifies IB via TPO-locked values + fixed bands).

---

## Wave status

| Wave | State |
|------|--------|
| 0 CC + D-087 | GO-WITH-NOTES + LOCKED |
| 1 S1-PREV + S1-WIRE | DONE |
| D-088 deploy | **Other agent** (Michael sent prompt) |
| 2 P1.5 CLOCK | **PARTIAL PASS** (this doc) |
| 3 SHADOW soak | After D-088 verify + Michael P-S0 |

---

*Audit-first · minimal diff · 2026-05-20*
