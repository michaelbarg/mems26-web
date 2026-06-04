# D-096 — S1 Day Type = OBSERVER enforced in code

**Status:** 🔒 LOCKED
**Date:** 2026-06-04
**Decided by:** Michael Barg (S1/S2 firing diagnosis session)
**Implements:** Systems Decisions Registry §3 (S1 = OBSERVER, output = NEVER)
**Commit:** `d785b2c` (`fix(D-090): enforce S1 OBSERVER — block Signal generation in wrappers.py`)
**Related:** D-089 (S3 Firing), Registry (`docs/reports/MEMS26_SYSTEMS_DECISIONS_REGISTRY_2026-05-23.md:80`)

---

## Context

The Systems Decisions Registry (2026-05-23) designates S1 (Day Type) as
**OBSERVER** with output = **NEVER**. However, `wrappers.py:86-102`
contained active Signal-generation code that returned `Signal(system_id=1)`
whenever `lock_state ∈ {LOCKED, LOCKED_LOW_CONF}` and `playbook ≠ None`.

In practice, the state machine reached `LOCKED_LOW_CONF` on 22 of 23
recorded states in PG (all Normal, confidence=0.68), meaning S1 was
generating Signals on every RTH session despite its OBSERVER designation.
These Signals could propagate to the gateway and downstream systems.

---

## Decision

### S1 = OBSERVER — Signal generation blocked

- **`wrappers.py:88`**: `return None` immediately after `process_bar()`
  completes. The state machine runs in full (classification, IB analysis,
  re-eval triggers, playbook generation), but no `Signal` object is
  returned to the caller.
- **Classification data remains available** via the state machine's
  internal state (accessed by other systems through the event bus /
  `day_type_classification` stream).
- **No downstream impact**: S1 Signals never reached the gateway in
  production because no consumer was wired to act on `system_id=1`
  Signals. This decision formalizes the intended behavior and prevents
  accidental consumption.

### How to re-enable S1 firing

To make S1 a firing system in the future:

1. Create a new D-decision (D-09x) that explicitly designates S1 as FIRING.
2. Update the Registry §3 row for S1: role → FIRING, output → `route_setup(1)`.
3. Remove the `return None` guard at `wrappers.py:88` and restore the
   Signal-generation block (preserved in git history at `d785b2c~1`).
4. Wire `route_setup(1)` in the gateway (does not exist today).
5. Define S1 entry/stop/T1/T2 spec (currently only playbook strategy exists,
   no concrete price levels).
6. SHADOW soak (≥20 trades, 4h green) before DEMO/LIVE.

---

## Scope — what D-096 does and does NOT change

### Does change

| Item | Before | After |
|------|--------|-------|
| `wrappers.py` S1 analyze() | Returns `Signal(system_id=1)` on lock | Returns `None` always |
| Registry compliance | Code contradicted Registry | Code matches Registry |

### Does NOT change

| Item | Status |
|------|--------|
| State machine (13 stages, A1→C3) | UNCHANGED — runs in full |
| Day type classification output | UNCHANGED — available to consumers |
| IB width / gap / behavior analysis | UNCHANGED |
| Re-eval triggers | UNCHANGED (trigger#1 separately fixed in `9cac12f`) |
| Playbook generation (C3) | UNCHANGED — still computed, just not emitted as Signal |
| `lock_state` transitions | UNCHANGED |
| Other systems (S2–S6) | UNCHANGED |

---

## Evidence (PG, 2026-06-04)

```
v9_day_type_state lock_state distribution:
  LOCKED_LOW_CONF = 22
  PENDING         =  1
  LOCKED          =  0   (confidence max 0.68, threshold 0.85)

Total: 23 rows
```

Before this fix, all 22 `LOCKED_LOW_CONF` states would have generated
Signals. After: zero Signals from S1.

---

## Linked documents

| ID | Relationship |
|----|--------------|
| D-089 | Independent — S3 firing status |
| Registry §3 | **AUTHORITY** — S1 = OBSERVER, output = NEVER |
| `9cac12f` | Companion fix — ATR fallback for re-eval triggers |
| `5343755` | Companion fix — S2 VSA volume gate enabled |

---

*End of D-096. Sign-off: Michael Barg, 2026-06-04.*
