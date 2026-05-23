# Agent: Woodies-T2-Fire-Spec-Agent (S4)

**System:** S4 Woodies CCI · **Type:** FIRING (T2) · **Priority: HIGH**  
**Report:** `docs/reports/AGENT_S4_WOODIES_FIRE_SPEC_AUDIT.md`

---

## Mission

Michael completed **POC Woodies** (Sierra real-time + time axis). This agent **only audits** that strategic spec A1–A7 + gateway rules match code and Plan UI — **no DLL/UI/Sierra changes**.

**Two tracks:**
1. **SHOULD FIRE** — pattern + A1–A7 PASS + `ready_to_route=true` + gateway clear → `last_route.shadow` set, log `[Woodies] SHADOW recorded`
2. **SHOULD BLOCK** — `failed_stages` non-empty (e.g. **A5 reject**), `blocked_by` (cluster_guard/cooldown/SSV/chop), no gateway, killzone advisory

---

## Hard bans (Michael explicit)

- **No** design / Plan layout / CSS
- **No** `sc_study/`, bridge, Sierra study settings, `woodies_5min.json` schema changes
- **No** `calculate_size` / decision tree logic changes without strategic stop

Verify only. Gaps → report, not code.

CC sync: **DLL-G1**, **GW-1**, **PERF-1**, **UI-3**, Plan #13 table

---

## Spec sources

1. `backend/v9/systems/woodies/compliance_manifest.yaml` — A1–A7, B1–B14 delegated
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S4
3. `backend/v9/systems/woodies/decision_tree.py` — `ready_to_route` formula
4. `backend/v9/systems/woodies/woodies_system.py` — `process_bar` → `route_setup`
5. `backend/v9/gateway/trading_gateway.py` — blockers before SHADOW
6. `frontend/.../WoodiesPlan.tsx`, `planFireDiagnosis.ts`, `planHelp.ts` (A5 RTL)
7. `docs/reports/PROMPT30_10b_PLAN_LIVE.md`

---

## Spec: ready_to_route (code truth)

```text
ready_to_route = no FAIL, no PENDING, patterns non-empty, sizing != reject
```

Fire path: `woodies_system.py` calls `gateway.route_setup(setup, 4)` only if above + `_gateway` set.

---

## Block matrix (mandatory rows)

| Blocker | Spec/intent | Code | Plan UI | Live |
|---------|-------------|------|---------|------|
| A5 sizing=reject | TREE_FAIL, BLOCKED | decision_tree | A5 FAIL row | |
| failed_stages=['A5'] | BLOCKED badge | | | |
| cluster_guard | gateway; **no SHADOW** | trading_gateway L86-88 | whyNotFire | curl risk |
| ready_to_route + blocked_by | UX GAP | | "מוכן לניתוב" | |
| no _gateway | skipped no_gateway | | אין Gateway | |
| A4 touch-point timeout | advisory PASS only | A4 message | A4 row | |

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==4)|{state,ready:.raw.ready_to_route,failed:.raw.failed_stages,last_route:.raw.last_route,pre_fire:[.raw.decision_tree.pre_fire[]|{stage:.stage_id,st:.status}]}'
curl -s http://localhost:8000/api/v9/gateway/risk | jq .
grep -E '\[Woodies\] (Gateway blocked|SHADOW recorded)' /tmp/backend.err.log | tail -20
pytest tests/v9/frontend/test_plan_fire_diagnosis_contract.py tests/v9/compliance/test_woodies_compliance.py -q --tb=no 2>/dev/null | tail -5
```

Browser: Plan S4 — STATE tap RTL; TO FIRE A1–A7; capture BLOCKED session if `failed_stages` live.

**Sierra (read-only):** `jq '.current_bar|{proj_hi,proj_lo,export_ts}' ~/SierraChart_Data/v9_export/woodies_5min.json` — report only, do not fix.

---

## Deliverable

1. Trace diagram: Bar → A1–A7 → ready_to_route → gateway gates → SHADOW or blocked_by  
2. **≥2 SHOULD_BLOCK** scenarios with spec citation  
3. **≥1 SHOULD_FIRE** scenario (or explain why live prevented — cluster_guard)  
4. List contradictions with CC §4 and Michael POC assumptions  

---

*Read-only · Woodies-T2-Fire-Spec-Agent · Michael POC respected · 2026-05-20*
