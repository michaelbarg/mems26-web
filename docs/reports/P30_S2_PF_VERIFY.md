# S2-PF Verify (P0.5 — no commit)

**Date:** 2026-05-20  
**Parent:** `docs/reports/P30_CURSOR_P05_REPORT.md`

## Fire path

```
five_min_system.py (process_bar FIRE block)
  → emit_t1_setup()  (setup_emitter.py)
  → validate_fire()  (setup_emitter.py:81)
  → if T1Setup returned: gateway.route_setup(gateway_setup, 2)  (five_min_system.py:556)
```

## pre_fire in path

**YES** — `backend/v9/systems/five_min/setup_emitter.py:70-85`

## P1 action needed

**NO** — VERIFIED; Diagnostic A7 ("line 556 without pre_fire") was incorrect.

## S4 reference (for comparison)

Woodies `decision_tree.py` A7 + `route_setup` when `ready_to_route`.
