# Agent: Killzone-Gate-Observer-Spec-Agent (S6)

**System:** S6 Killzone · **Type:** OBSERVER — **session gate advisory**  
**Report:** `docs/reports/AGENT_S6_KILLZONE_FIRE_SPEC_AUDIT.md`

---

## Mission

Verify strategic spec: S6 defines **when Cash Hours gate is OPEN** and how firing systems (especially **S4 Woodies**) must respect it. S6 does **not** use BLOCKED lifecycle on Plan (by design) — confirm spec says gate enforcement is on **consumers**, not S6 badge.

**Two tracks:**
1. **NO-FIRE (always)** — S6 never `route_setup`
2. **GATE CLOSED** — NY_PREMARKET etc. → Woodies `diagnoseWoodies` adds whyNotFire; gateway may still block separately

---

## Hard bans

- No design / Sierra / DLL
- Do not change S6 APPROACHING vs gate CLOSED UX without Michael (G-PLAN-7 doc only)

---

## Spec sources

1. `backend/v9/systems/killzone/compliance_manifest.yaml`
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S6
3. `backend/v9/api/v9/killzone/*`
4. `frontend/.../KillzonePlan.tsx`, `planFireDiagnosis.ts` (killzoneOpen for S4)
5. `PROMPT30_10b_PLAN_LIVE.md` — S6 observer note

---

## Cross-system checks (mandatory)

| Consumer | Spec behavior when gate closed | Code | Evidence |
|----------|------------------------------|------|----------|
| S4 Woodies | whyNotFire killzone | diagnoseWoodies | snapshot A4 touchpoints.killzone |
| S2/S3 | per spec | five_min / footprint | |
| Gateway | **no killzone check** in route_setup | trading_gateway.py grep | GAP? |

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/killzone/current | jq '{zone:.current_zone,gate_open:.gate_open,clock_status}'
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==6)'
# Woodies touchpoint embed:
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==4)|.raw.decision_tree.pre_fire[]|select(.stage_id=="A4")|.details.touchpoints.killzone'
```

Browser: Plan S6 — APPROACHING + ⚠ Gate —

---

## Deliverable

1. Spec quote: who must block fire when gate closed  
2. PASS/FAIL: S6 observer + S4 consumer alignment  
3. If gateway ignores killzone → GAP with severity (logic vs UI)

---

*Read-only · Killzone-Gate-Observer-Spec-Agent · 2026-05-20*
