# Agent: FiveMin-T1-Fire-Spec-Agent (S2)

**System:** S2 5-Min · **Type:** FIRING (T1)  
**Report:** `docs/reports/AGENT_S2_FIVEMIN_FIRE_SPEC_AUDIT.md`

---

## Mission

Map **strategic spec** → **when S2 should fire** vs **when it must block**, and verify Plan tab + gateway path match.

**Two tracks:**
1. **SHOULD FIRE** — FIRST_HOUR_TACTICAL / DAY_TYPE_MODE + pattern + buffer≥4 + gateway open → expect `route_setup` attempt
2. **SHOULD BLOCK** — MAINTENANCE, WEEKEND, **OVERNIGHT_MODE**, no pattern, pre_fire fail, gateway blockers

---

## Hard bans

- No design / Sierra / DLL / bridge edits
- inbox §7a — Sierra data is source of truth

CC sync: **UI-2** (OVERNIGHT→BLOCKED), **GW-***, **OPS-BRIDGE**

---

## Spec sources

1. `backend/v9/systems/five_min/compliance_manifest.yaml` — REACTIVE/INITIATIVE, FIRE_ROUTE, COT_AMT
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S2
3. `backend/v9/systems/five_min/five_min_system.py` — mode, `route_setup`
4. `frontend/.../FiveMinPlan.tsx`, `planFireDiagnosis.ts` (MAINTENANCE/WEEKEND)
5. `tests/v9/frontend/test_plan_fire_diagnosis_contract.py` — S2 BLOCKED merge

---

## Spec fire/block matrix (fill with evidence)

| Condition | Spec | Code | Plan UI | Live curl |
|-----------|------|------|---------|-----------|
| mode=MAINTENANCE/WEEKEND | no fire | | BLOCKED? | |
| mode=OVERNIGHT_MODE | **verify spec** | deriveFiringLifecycle=SCANNING | Hebrew setup | |
| last_pattern set | may fire | gateway | READY? | |
| cluster_guard | block at gateway | trading_gateway.py | N/A S2 Plan | gateway/risk |

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==2)|{state,raw:{mode:.raw.mode,last_pattern:.raw.last_pattern,last_fire:.raw.last_fire}}'
curl -s http://localhost:8000/api/v9/gateway/risk | jq '{cluster_guard,cooldown}'
pytest tests/v9/frontend/test_plan_fire_diagnosis_contract.py::test_s2_maintenance_stays_blocked_not_scanning -q
```

Browser: Plan tab S2 — STATE vs mode row consistency.

---

## Deliverable

Verdict + table **SHOULD_FIRE scenario** (1 row) + **SHOULD_BLOCK scenario** (≥3 rows: overnight, maintenance, gateway) + GAPs vs spec.

---

*Read-only · FiveMin-T1-Fire-Spec-Agent · 2026-05-20*
