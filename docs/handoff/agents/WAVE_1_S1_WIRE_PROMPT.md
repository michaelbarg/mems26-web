# Wave 1b — Cursor: S1-WIRE (narrow `main.py` hook)

**Role:** Agent-S1-WIRE  
**Type:** CODE — ~30 LOC, no "7 modules" refactor  
**Precondition:** Wave 1a PASS (`P30_S1_PREV_DONE.md`)  
**Deliverable:** `docs/reports/P30_S1_WIRE_DONE.md`  
**Commit:** 1 commit — Michael approval only

---

## Mission

Wire `prev_day.py` into Day Type startup / bar path in **`main.py`** only where  
`_load_previous_day_context` or seed path already expects PD context.

**Narrow scope:** import + call + pass into `DayTypeStateMachine` / seed — **not** a full S1 rewrite.

---

## Read before edit

- `backend/main.py` — `day_type_machine`, `maybe_seed_ib_from_tpo`, `_load_previous_day_context`
- `backend/v9/api/v9/day_type_seed.py`
- `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19*.md` if present
- `docs/reports/P30_ROAD_START_TO_LIVE.md` § S1

---

## ALLOWED FILES

- `backend/main.py` (minimal diff only)
- `backend/v9/systems/day_type/state_machine.py` (only if required for PD fields)
- `backend/v9/api/v9/day_type_seed.py` (only if seed must use shared helper)
- `tests/v9/systems/test_day_type/test_mid_session_restart_seed.py` (extend if needed)
- `docs/reports/P30_S1_WIRE_DONE.md`

## DO NOT TOUCH

- gateway, footprint fire, bridge, frontend, DLL
- Other systems' `main.py` blocks (five_min, footprint, woodies injectors)

---

## Requirements

1. On startup (or first bar), load PD context via `prev_day` module.
2. Preserve existing `maybe_seed_ib_from_tpo` behavior (10b) — no regression.
3. Log at **warning** (not debug) on missing PD after RTH open.
4. S1 still **must not** call `route_setup` (grep verify in report).

---

## Verification

```bash
pytest tests/v9/systems/test_day_type/ -q
curl -s http://127.0.0.1:8000/api/v9/day_type/v9/current | jq '{day_type,locked}'
```

---

## Report template

```markdown
# P30 S1-WIRE Done
**Verdict:** PASS/FAIL
## main.py diff summary (lines)
## grep route_setup day_type: 0 expected
## pytest
## UAT note (4 axes if endpoint touched)
```

---

## Handoff

→ Parent opens Wave 2 CLOCK prompt.

---

*Cursor subagent · Wave 1b · 2026-05-20*
