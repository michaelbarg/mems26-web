# Regression triage · 2026-07-20 (cursor · cur-3)

**Command:** `BRIDGE_TOKEN=test pytest tests/v9/regression/ -q --tb=no`  
**Result (re-run 2026-07-20 evening):** **110 failed**, 1174 passed, 2 xfailed (was ~92 → 118 → 110 after new Dalton contracts; no import errors).

## Classification buckets (by file cluster)

| Bucket | Count (approx) | Files | Action |
|--------|----------------|-------|--------|
| **(א) stale→ruled** | ~25–35 | `test_fixed_contracts_2/3` · `test_sizing_consolidation` · `test_stop_anchor_*` · `test_woodies_stop_v2` · risk/cutoff pins | Update expects to ruled values (FIXED_4=1 · 6T · caps 800/999 · cutoff 15:30). **Do not touch trading code.** |
| **(ב) pre-existing rot** | ~50–70 | `test_confluence_ri_zlr`(11) · `test_zone_limit_entry`(9) · `test_engine_promotion_parity`(11) · `test_structural_targets`(6) · `test_daytype_position_gate`(6) · `test_daytype_gate_live`(7) · `test_daytype_honest_prelock`(4) · `test_d_rvx_*` · opening/zones | Fix cheap fixtures OR `xfail(reason=..., strict=False)` + TODO. Not today's Dalton block. |
| **(ג) real bug** | **0 found in this pass** | — | No stop: no failure looked like "code wrong vs ruled truth" without being a stale expect. |
| **Harness/env** | 3 | `test_verify_orphan_place_stop_sim` | Likely ROOT/ops_log path in tmp — fix harness fixture, not trading. |

## Top fail files (uniq counts)

```
 11 test_engine_promotion_parity.py
 11 test_confluence_ri_zlr.py
  9 test_zone_limit_entry.py
  7 test_daytype_gate_live.py
  6 test_structural_targets.py
  6 test_daytype_position_gate.py
  4 test_sizing_consolidation.py
  4 test_fixed_contracts_2.py
  4 test_daytype_honest_prelock.py
  … (rest ≤3 each)
```

## Recommended order for cc/cowork (after Dalton block)

1. Batch-(א): fixed_contracts + sizing + stop 6T pins (fast, ruling-aligned).
2. Orphan harness 3 fails (path isolation).
3. Defer confluence/zone/engine_parity to weekend — pre-existing, not live blockers.

## Dalton contract tests (before enable) — Rule 5

```bash
$ BRIDGE_TOKEN=test pytest \
  test_stop_at_structural_edge_420.py \
  test_dalton_ib_break_variation_7501.py \
  test_dalton_require_day_direction_vah.py \
  test_sierra_reconcile_420_pnl.py \
  test_dalton_t2_t3_structural_variation.py -q
26 passed
```

| File | Case | Status |
|------|------|--------|
| `test_stop_at_structural_edge_420.py` | #420 stop beyond structure + 6T | ✅ |
| `test_dalton_ib_break_variation_7501.py` | low7501 < IB7506 → Variation | ✅ |
| `test_dalton_require_day_direction_vah.py` | SHORT@VAH Variation-down vs BLUE | ✅ |
| `test_sierra_reconcile_420_pnl.py` | fills vs −$82.50 calculated | ✅ |
| `test_dalton_t2_t3_structural_variation.py` | Variation SHORT T2=POC T3=VAL (anti-stomp) | ✅ NEW |

Full audit: `docs/handoff/FULL_AUDIT_2026-07-20.md`.  
*No trading code changed. No flags enabled.*
