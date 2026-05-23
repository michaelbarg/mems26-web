# Wave 2 — Cursor: P1.5 Market Clock (audit → gap-fill)

**Role:** Agent-CLOCK (single agent, **sequential** commits)  
**Precondition:** Wave 1 G1 PASS  
**Drive source:** System 1 Data Reqs V1.0 — `1KhbyAWIDswqHp6M3JiQmuKifw5cUopBYLmwuAKQ2UyI`  
**Deliverable:** `docs/reports/P30_P15_CLOCK_DONE.md` + up to 5 commits

---

## Critical: audit before building

Repo **already has** partial P1.5:

| Task | Likely status | Path |
|------|---------------|------|
| CLOCK-1 | **EXISTS** | `backend/v9/services/market_clock.py` |
| CLOCK-2 | **EXISTS** | `backend/v9/api/v9/clock_routes.py` → `GET /api/v9/clock/now` |
| CLOCK-3 | **PARTIAL** | `backend/v9/systems/day_type/open_type.py`, `opening_detector.py` |
| CLOCK-4 | **CHECK** | IB percentile / `classify_ib_width` |
| CLOCK-5 | **EXISTS** | `tpo_routes.py` `@router.get("/previous_day")` |

**First step:** Classify each CLOCK-1..5 as KEEP / ADAPT / REPLACE / DEFER.  
Only implement **gaps** vs Drive spec. Do not rewrite working clock.

---

## Sequential commits (only for gaps)

| Commit | ID | Scope |
|--------|-----|--------|
| 1 | CLOCK-1 | Gap-fill `market_clock.py` only if spec mismatch |
| 2 | CLOCK-2 | Register route in `app.py` if missing; contract test |
| 3 | CLOCK-3 | Open Type 4 types — align with Drive |
| 4 | CLOCK-4 | IB width 10-day rolling percentile |
| 5 | CLOCK-5 | Ensure `GET /api/v9/tpo/previous_day` public path + tests |

**One commit per row** — do not mix CLOCK-3 and CLOCK-4 in one commit.

---

## ALLOWED FILES (union)

- `backend/v9/services/market_clock.py`
- `backend/v9/api/v9/clock_routes.py`
- `backend/v9/api/v9/open_type_routes.py`
- `backend/v9/systems/day_type/open_type.py`
- `backend/v9/systems/day_type/opening_detector.py`
- `backend/v9/api/v9/tpo_routes.py` (previous_day only)
- `backend/v9/app.py` (router include only)
- `tests/v9/**/test_*clock*`, `test_opening*`, `test_*previous_day*`
- `docs/reports/P30_P15_CLOCK_DONE.md`

## DO NOT TOUCH

- `backend/main.py` (unless Michael explicitly expands scope)
- gateway, bridge, sc_study, frontend
- `footprint_system.py` S3 fire (D-086)

---

## UAT per new/changed endpoint

For each API touched, document four axes:

1. Quality — bad rows / null fields
2. Recency — `latest_ts` vs DB MAX
3. Cardinality — `limit` honored
4. Latency — &lt; 500ms local

---

## Verification commands

```bash
curl -s http://127.0.0.1:8000/api/v9/clock/now | jq '{status,mode,session_date,is_rth_open}'
curl -s http://127.0.0.1:8000/api/v9/tpo/previous_day | jq '{found,session_date,poc,vah,val}'
pytest tests/v9/ -k 'clock or opening or previous_day' -q
```

---

## Report template

```markdown
# P30 P1.5 Market Clock Done
**Verdict:** PASS / PARTIAL / FAIL
## CLOCK-1..5 table (KEEP/ADAPT/NEW + commit hash)
## Drive gaps closed
## Four-axis UAT table
## pytest summary
## Deferred (needs Michael)
```

---

## Handoff

→ Wave 3 SHADOW soak (Michael + CC) — optional: P1.5 not required if Michael waives for soak start.

---

*Cursor · sequential · Wave 2 · 2026-05-20*
