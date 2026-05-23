# Agent: Footprint-T3-Fire-Spec-Agent (S3)

**System:** S3 Footprint · **Type:** FIRING (T3)  
**Report:** `docs/reports/AGENT_S3_FOOTPRINT_FIRE_SPEC_AUDIT.md`

---

## Mission

Verify T3 footprint **fire** and **block** rules from strategic spec through `footprint_system` → TradingGateway → Plan tab.

**Two tracks:**
1. **SHOULD FIRE** — combined_class ≠ NO_SETUP, pre_fire pass, gateway accepts → SHADOW id in `last_route` or `last_fire`
2. **SHOULD BLOCK** — `last_fire.blocked_by` (e.g. **cluster_guard**), pre_fire_validator, NO_SETUP

---

## Hard bans

- No design / Sierra / DLL / bridge edits
- Michael POC Woodies/Sierra — do not change export cadence

CC sync: **GW-1**, Plan audit S3 `cluster_guard` row

---

## Spec sources

1. `backend/v9/systems/footprint/compliance_manifest.yaml`
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S3
3. `backend/v9/systems/footprint/footprint_system.py` — `last_fire`, gateway
4. `frontend/.../FootprintPlan.tsx`, `planFireDiagnosis.ts`
5. `tests/v9/frontend/test_plan_fire_diagnosis_contract.py` — S3 blocked_by tests

---

## Gateway blockers (shared — document for S3)

From `trading_gateway.py` (order matters):
`cooldown` → `cluster_guard` → `suffering_side_veto` → `chop_searching` → else SHADOW

**Note:** `record_attempt()` runs before checks — may inflate cluster_guard (GAP GW-2).

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==3)|{state,combined:.raw.combined_class,last_fire:.raw.last_fire}'
curl -s http://localhost:8000/api/v9/gateway/status | jq '{shadow_active_count,cluster_guard:.cluster_guard}'
grep '\[Footprint\]' /tmp/backend.err.log | tail -15
pytest tests/v9/frontend/test_plan_fire_diagnosis_contract.py -q -k s3
```

Browser: Plan S3 — tap ● Last fire blocked → RTL panel.

---

## Deliverable

| Scenario | Expected | Observed | Spec § | PASS/FAIL |
|----------|----------|----------|--------|-----------|
| Balanced + cluster_guard | BLOCK, no new shadow | | | |
| Valid pattern + gates open | SHADOW recorded | | | |

---

*Read-only · Footprint-T3-Fire-Spec-Agent · 2026-05-20*
