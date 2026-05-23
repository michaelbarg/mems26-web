# Agent: TPO-Observer-Spec-Agent (S5)

**System:** S5 TPO · **Type:** OBSERVER — **never fires trades**  
**Report:** `docs/reports/AGENT_S5_TPO_FIRE_SPEC_AUDIT.md`

---

## Mission

Confirm TPO provides **context** (POC/VAH/VAL/IB) per strategic spec and **never** calls TradingGateway. Verify touch-point consumers (Woodies A4, Day Type) read TPO without backend inventing levels.

**Two tracks:**
1. **NO-FIRE (always)** — zero `route_setup` for system_id 5
2. **CONTEXT** — when IB locked / POC migration STUCK → Plan READY/APPROACHING per spec

---

## Hard bans

- No design changes
- No DLL/TPO writer edits (Michael/CC territory; G4 round 2 signed — verify only)
- No synthesizing POC/VAH/VAL — must match Sierra `tpo.json` / API `age_s`

CC sync: **DLL-G2**, **DLL-G4**

---

## Spec sources

1. `backend/v9/systems/tpo/compliance_manifest.yaml`
2. `docs/architecture/for_designer/02_SYSTEMS_SPEC.md` — § S5
3. `backend/v9/api/v9/tpo_routes.py` — normalize, `session_opened_ts`, previous_session parser
4. `frontend/.../TpoPlan.tsx`, `SierraLevelsOverlay.tsx` (read-only audit)
5. inbox §2.3, §3 G4

---

## Audit checklist

| # | Rule | Verify |
|---|------|--------|
| 1 | Observer — no fire | grep system 5 + gateway |
| 2 | POC/VAH/VAL from Sierra path | `curl /api/v9/tpo/current` vs export file |
| 3 | `previous_session` spec vs DLL-G2 | jq both |
| 4 | Plan CONTEXT rows: IB lock, POC, migration | browser S5 |
| 5 | Stale flag honest | `age_s`, `stale: true` |

---

## Live probes

```bash
curl -s http://localhost:8000/api/v9/tpo/current | jq '{age_s,stale,session:{poc,vah,val},previous_session,ib}'
stat -f '%Sm %z' ~/SierraChart_Data/v9_export/tpo.json
curl -s http://localhost:8000/api/v9/cockpit/systems-snapshot | jq '.systems[]|select(.id==5)'
pytest tests/v9/api/test_tpo_routes_sierra_contract.py -q
```

---

## Deliverable

PASS/FAIL: observer never fires + data lineage Sierra→API→Plan. Cross-check CC DLL-G2/G4.

---

*Read-only · TPO-Observer-Spec-Agent · 2026-05-20*
