# Agent: DayType-Observer-Spec-Agent (S1)

**System:** S1 Day Type · **Type:** OBSERVER — **never fires trades**  
**Report:** `docs/reports/AGENT_S1_DAYTYPE_FIRE_SPEC_AUDIT.md`

---

## Mission

Verify strategic spec vs implementation for **classification only** — what should influence other systems, and confirm S1 **cannot** route to TradingGateway.

Test **two tracks:**
1. **NO-FIRE (always)** — any path that would call `route_setup` = **SPEC VIOLATION**
2. **CONTEXT (advisory)** — when S1 should be READY/APPROACHING/SCANNING on Plan tab vs spec

---

## Hard bans

- No UI/design/CSS changes
- No `sc_study/`, bridge, Sierra export settings
- No code edits unless Michael says "go implement fix"

Michael: DLL/time-axis fixes **done** — read-only verify per inbox §7a.

Sync with **`docs/handoff/CC_STATUS_REQUEST_2026-05-20.md` §4** (rows API-1, INV-1) when CC fills.

---

## Spec sources (read in order)

1. `backend/v9/systems/day_type/compliance_manifest.yaml`
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S1
3. `backend/v9/api/v9/day_type_*` + `backend/main.py` (`day_type_machine`, `day_type_seed`)
4. `frontend/.../DayTypePlan.tsx`, `systemPlanLive.tsx` (observer lifecycle)
5. `docs/handoff/INVESTIGATE_DAY_TYPE_NONTREND_2026-05-19*.md` if present

---

## Audit checklist

| # | Spec rule | Code location | Test |
|---|-----------|---------------|------|
| 1 | 6 day types + lock after IB+5m | decision tree Q1–Q5 | `tests/v9/compliance/test_day_type_compliance.py` |
| 2 | No `route_setup` / no firing_system=1 | grep gateway calls | must be zero |
| 3 | `probability`, `trading_confidence` exposed to touch-points | snapshot systems[1] | curl |
| 4 | Plan: CONTEXT only, no TO FIRE | browser Plan S1 | SCANNING/READY rules |
| 5 | Post-restart IB seed from TPO (10b) | `day_type_seed.py` | pytest mid_session_restart |

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/day_type/v9/current | jq '{day_type,probability,trading_confidence,locked}'
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==1)'
pytest tests/v9/compliance/test_day_type_compliance.py tests/v9/systems/test_day_type/test_mid_session_restart_seed.py -q
```

---

## Deliverable template

```markdown
# S1 Day Type — Fire/Block Spec Audit
## Verdict: PASS / FAIL / PARTIAL
## Track A — Must NEVER fire: [PASS/FAIL + evidence]
## Track B — Advisory context: [spec vs Plan vs API]
## CC cross-check: [API-1, INV-1 from CC_STATUS_REQUEST]
## GAPs (no fix without Michael): ...
```

---

*Read-only · DayType-Observer-Spec-Agent · 2026-05-20*
