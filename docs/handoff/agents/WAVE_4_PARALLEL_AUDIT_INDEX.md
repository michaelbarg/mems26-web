# Wave 4 — Parallel Read-Only Audits (6 agents)

**Role:** Cursor Parent launches **6 subagents in parallel**  
**Precondition:** SHADOW soak review + HTTP green + Michael says **go audit**  
**Type:** READ-ONLY — no code unless Michael says implement  
**Merge deliverable:** `docs/reports/P30_SIX_SYSTEM_FIRE_SPEC_MATRIX.md`

---

## Launch pattern

Paste **one prompt per Task** — different system each.  
Do **not** assign two agents to `main.py` or gateway.

| Agent | Prompt file | Report output |
|-------|-------------|---------------|
| S1 | [`AGENT_S1_DAYTYPE_OBSERVER_SPEC.md`](./AGENT_S1_DAYTYPE_OBSERVER_SPEC.md) | `docs/reports/AGENT_S1_DAYTYPE_FIRE_SPEC_AUDIT.md` |
| S2 | [`AGENT_S2_FIVEMIN_T1_FIRE_SPEC.md`](./AGENT_S2_FIVEMIN_T1_FIRE_SPEC.md) | `docs/reports/AGENT_S2_FIVEMIN_FIRE_SPEC_AUDIT.md` |
| S3 | [`AGENT_S3_FOOTPRINT_T3_FIRE_SPEC.md`](./AGENT_S3_FOOTPRINT_T3_FIRE_SPEC.md) | `docs/reports/AGENT_S3_FOOTPRINT_FIRE_SPEC_AUDIT.md` |
| S4 | [`AGENT_S4_WOODIES_T2_FIRE_SPEC.md`](./AGENT_S4_WOODIES_T2_FIRE_SPEC.md) | `docs/reports/AGENT_S4_WOODIES_FIRE_SPEC_AUDIT.md` |
| S5 | [`AGENT_S5_TPO_OBSERVER_SPEC.md`](./AGENT_S5_TPO_OBSERVER_SPEC.md) | `docs/reports/AGENT_S5_TPO_FIRE_SPEC_AUDIT.md` |
| S6 | [`AGENT_S6_KILLZONE_OBSERVER_SPEC.md`](./AGENT_S6_KILLZONE_OBSERVER_SPEC.md) | `docs/reports/AGENT_S6_KILLZONE_FIRE_SPEC_AUDIT.md` |

---

## S3 special context (mandatory add-on)

Append to S3 agent prompt:

```text
CONTEXT: D-086 — footprint_system.py route_setup(3) VIOLATES D-082 V3 observer spec.
SHADOW: tolerated (records only). Audit must state LIVE blocker until fixed.
READ: docs/reports/P30_DECISION_D086_S3_FIRING.md
```

---

## Parent merge checklist

| Column | Source |
|--------|--------|
| System | S1–S6 |
| Spec mode | Firing / Observer |
| Verdict | PASS / FAIL / PARTIAL |
| route_setup? | grep evidence |
| SHADOW ok? | Y/N + D-086 note for S3 |
| LIVE blocker? | Y/N |
| Owner | Michael / Cursor / CC / DEFER |

---

## After Wave 4 (not parallel)

| Seq | Task | Owner |
|-----|------|-------|
| 1 | D-086 decision A/B/V4 | Michael |
| 2 | L4 risk audit | Cursor read-only + Michael sign-off |
| 3 | L5 paper dry run | Michael + CC |
| 4 | V6 §11 Analyst | Cursor Phase 4 |
| 5 | V6 §8 Pre-flight | Cursor Phase 5 |
| 6 | LIVE activation | Michael |

---

## Standard header for each subagent

```text
MODE: READ-ONLY
PRECONDITION: SHADOW_SOAK_FINAL reviewed
DO NOT: edit code, bridge, DLL, frontend
OUTPUT: docs/reports/AGENT_Sx_*.md per linked prompt
STOP: spec conflict → report GAP, ask Michael
```

---

*Index only · post-SHADOW · 2026-05-20*
