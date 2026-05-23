# Wave 1a — Cursor: S1-PREV (`prev_day.py`)

**Role:** Agent-S1-PREV  
**Type:** CODE — smallest correct change  
**Precondition:** G0 = CC GO + D-087 LOCKED + Michael said **go implement**  
**Deliverable:** code + tests + `docs/reports/P30_S1_PREV_DONE.md`  
**Commit:** 1 commit — only if Michael approved commit

---

## Mission

Extract **previous trading day context** for Day Type (POC/VAH/VAL/IB/shape) into  
`backend/v9/systems/day_type/prev_day.py` and unit tests.

**Do not** duplicate full TPO route logic — **reuse** `market_clock.get_previous_trading_day` and DB patterns from `tpo_routes.py` `/previous_day` where possible.

---

## Audit first (M14)

| Surface | Action |
|---------|--------|
| `backend/main.py` `_load_previous_day_context` | KEEP logic — may call into `prev_day` later |
| `backend/v9/api/v9/tpo_routes.py` `tpo_previous_day` | ADAPT — shared query helper |
| `backend/v9/services/market_clock.py` | KEEP |
| `backend/v9/systems/day_type/state_machine.py` `pd_degraded_reason` | READ — wire in Wave 1b |

Classify in report: KEEP / ADAPT / NEW.

---

## ALLOWED FILES

- `backend/v9/systems/day_type/prev_day.py` (NEW)
- `tests/v9/systems/test_day_type/test_prev_day.py` (NEW)
- `docs/reports/P30_S1_PREV_DONE.md` (NEW)

## DO NOT TOUCH

- `backend/main.py` (Wave 1b)
- `backend/v9/gateway/trading_gateway.py`
- bridge, `sc_study/`, frontend
- S3 `footprint_system.py` firing path (D-086)
- `MEMS26_REGISTRY.yaml`

---

## Requirements

1. Function(s) to load previous session summary for a given `session_date` or "yesterday trading day".
2. Clear return when missing: `found: false` + reason compatible with `missing_previous_day_context`.
3. Tests: weekend skip, missing row, happy path with fixture/mocked DB.
4. **No** `route_setup` / no gateway imports in S1 module.

---

## Verification

```bash
pytest tests/v9/systems/test_day_type/test_prev_day.py -q
```

---

## Report template

```markdown
# P30 S1-PREV Done
**Verdict:** PASS/FAIL
## KEEP/ADAPT/NEW table
## API surface (functions)
## Tests
## Blockers for S1-WIRE
```

---

## Handoff

→ Parent runs Wave 1b **only after** this PASS.

---

*Cursor subagent · Wave 1a · 2026-05-20*
