# Wave 0 — Michael: D-087 Registry §18 Waiver

**Role:** Michael (decision only)  
**Time:** ~5 minutes  
**Precondition:** Read `docs/reports/P30_REGISTRY_STATE.md`  
**Deliverable:** `docs/decisions/D-087_REGISTRY_WAIVER.md` (signed/LOCKED)  
**Parallel:** Safe alongside CC Wave 0 verify

---

## Question

Registry §18 gate is **FAIL** (20 CRITICAL SPECIFIED, 23 HIGH SPECIFIED).  
Does Michael **waive** formal §18 GREEN for **SHADOW soak only**, with triage scheduled post-SHADOW?

---

## Options (pick one)

| Option | Meaning |
|--------|---------|
| **A — WAIVER** | SHADOW soak may proceed; §18 triage is POST-SHADOW deliverable |
| **B — TRIAGE FIRST** | Block Wave 1 code until N CRITICAL moved to VERIFIED (Michael sets N) |
| **C — PARTIAL** | Waive CRITICAL count only; HIGH must drop below 5 before LIVE |

---

## Template (copy to `docs/decisions/D-087_REGISTRY_WAIVER.md`)

```markdown
# D-087 — Registry §18 Waiver for SHADOW Soak

**Status:** LOCKED
**Date:** 2026-05-20
**Decided by:** Michael Barg

## Context

- Source: `MEMS26_REGISTRY.yaml` — see `docs/reports/P30_REGISTRY_STATE.md`
- §18 gate: 20 CRITICAL SPECIFIED, 23 HIGH SPECIFIED → formal FAIL
- P0.5 code (GW-02, GW-CHOP, FP-SQL) is complete regardless

## Decision

Michael selects: **[ A WAIVER | B TRIAGE FIRST | C PARTIAL ]**

### If A (recommended for timeline)

- SHADOW soak (5–10 RTH days) is **not blocked** by Registry §18 counts alone.
- This waiver does **not** waive LIVE, DEMO, or risk sign-off.
- POST-SHADOW: triage backlog with owner per row; target LIVE gate = §18 GREEN or updated Drive rule.

### If B or C

- Document explicit unblock criteria and date.

## Does NOT approve

- S3 spec compliance (see D-086)
- LIVE activation
- Skipping L4/L5
- Any change to `MEMS26_REGISTRY.yaml` without a separate task

## Evidence

- Registry snapshot date: 2026-05-20
- CC Wave 0 verify: [pending / GO / link]
```

---

## After sign

1. Tell Cursor Parent: **D-087 = LOCKED (option X)**
2. CC GO + D-087 → **G0 open** → Wave 1

---

*Michael only · no agent code · 2026-05-20*
