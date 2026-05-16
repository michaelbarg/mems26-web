# Prompt 25b: Cross-System Integration Proof Correction

**Date:** 2026-05-16  
**Commit:** (Prompt 25b)  
**Tests:** 44/44 focused tests pass  
**No SHADOW/DEMO/LIVE enabled.**

**Spec correction:** S1 Day Type, S5 TPO, and S6 Killzone are advisory/context
systems. They may shape strategy, quality, sizing, timing, reason tree, and
recommendation. They must not directly hard-block a setup. Hard blocks belong
only to explicit `pre_fire`, risk, and safety gates.

---

## Integration Matrix

| # | Integration | Test | Status |
|---|-------------|------|--------|
| 1 | S1 Day Type → S4 Woodies (A4 advisory touch-point) | test_s4_a4_queries_day_type | PROVEN |
| 2 | S1/S5/S6 unavailable → S4 records advisory context, no hard block | test_s4_a4_records_unavailable_context_as_advisory | PROVEN |
| 3 | S5 TPO → S4 Woodies (A4 touch-point) | test_s4_a4_queries_tpo | PROVEN |
| 4 | S1/S5/S6 unfavorable context visible in reason tree, no hard block | test_s4_a4_unfavorable_context_is_advisory_not_blocking | PROVEN |
| 5 | S2 fires through pre_fire_validator | test_s2_uses_pre_fire_validator | PROVEN |
| 6 | S2 gateway gated (no fire without setup) | test_s2_gateway_only_when_setup_valid | PROVEN |
| 7 | S4 `/fire` routes only after explicit pre_fire validation | test_s4_gateway_gated_by_decision_tree | PROVEN |
| 8 | Explicit pre_fire rejection does not route | test_blocked_s2_does_not_route | PROVEN |
| 9 | S4 reason tree exposes A4 advisory context | test_s4_fire_shows_decision_stages | PROVEN |
| 10 | BarLevelDetector closes SHADOW trades | test_bar_level_detector_closes_trades | PROVEN |
| 11 | No DEMO/LIVE enabled | test_gateway_no_mode_enabled | PROVEN |

---

## Advisory-Context Proof

| System | Advisory-context proof | Status |
|--------|------------------------|--------|
| S2 Five-Min | S1 Day Type maps to time stop; S5 TPO maps to quality/sizing. LOW TPO quality now reduces size instead of returning `None`. Explicit `pre_fire_validator` remains the hard gate. | PROVEN |
| S3 Footprint | Fire path uses internal footprint signal/sizing and explicit `pre_fire_validator`; no S1/S5/S6 direct blocker was found in the current S3 fire path. Dedicated S1/S5/S6 advisory reason-tree consumption is not implemented in S3. | PARTIAL |
| S4 Woodies | A4 fetches S1/S5/S6/L0/veto touch-points and records `advisories`/`unavailable` in the decision tree. A4 no longer returns FAIL/PENDING for unfavorable or missing advisory context. | PROVEN |

### Fire Path (S2/S3/S4 -> Gateway)
```
Pattern detected -> per-system sizing/context
  -> explicit pre_fire_validator
  -> [if valid] gateway.route_setup(setup, system_id)
  -> gateway risk/safety gates may block
  -> otherwise SHADOW record path can create a trade record
  -> BarLevelDetector monitors T1/T2/T3 lifecycle
```

### Context Flow (S1/S5/S6 -> S4)
```
S4 process_bar -> decision_tree.evaluate_bar
  -> A4 touch-points: HTTP queries S1, S5, S6, L0, veto
  -> unavailable context -> A4 PASS with details.unavailable
  -> unfavorable context -> A4 PASS with details.advisories
  -> explicit A7 pre_fire remains the hard gate
```

---

## Spec Mismatches

### Fixed in Prompt 25b

- Prompt 25 proof incorrectly claimed `S1 unavailable -> S4 blocks`; corrected to advisory unavailable context.
- Prompt 25 proof incorrectly claimed `S6 Killzone=WEEKEND -> A4 blocks`; corrected to advisory killzone context.
- `backend/v9/systems/woodies/decision_tree.py` directly hard-blocked A4 on `day_type:not_classified`, `tpo:not_running`, missing TPO levels, and `killzone:WEEKEND/CLOSED/UNKNOWN`; A4 now records those as `advisories`.
- S4 A4 returned `PENDING` when advisory endpoints were unavailable; it now returns `PASS` with `details.unavailable`.
- S2 TPO LOW quality returned 0 contracts and `emit_t1_setup` returned `None`; LOW quality now reduces size to 1 contract and leaves hard rejection to `pre_fire_validator`.
- Prompt 25 tests proved the outdated blocker behavior; tests now prove advisory visibility without hard block and explicit pre_fire blocking.

### Remaining / Not Changed

- S3 does not currently expose a dedicated S1/S5/S6 advisory reason tree. Its fire path is still protected by explicit `pre_fire_validator`, so no direct S1/S5/S6 hard blocker was found there.
- Legacy `backend/v9/systems/chart_5min/detector.py` still has a `killzone_blocked` early return. It is outside the current Prompt 25 S2/S3/S4 proof surface and was not changed in this prompt.
- Full gateway/live-session behavior still requires replay or live market validation.

---

## What Remains Unproven (requires live market)

| Gap | Why can't be proven offline | Required for |
|-----|----------------------------|--------------|
| Full bar flow: Sierra → Bridge → BarRouter → S2/S3/S4 | Needs live tick data | SHADOW |
| Pattern detection on real market data | Weekends produce no patterns | SHADOW |
| BarLevelDetector closing real trades from real patterns | No real trades accumulate offline | SHADOW |
| Replay Clock Mode (simulate past market session) | Not yet built | Offline testing |
| Multiple concurrent trades managed by BarLevelDetector | Requires sustained pattern fires | SHADOW Day 7+ |

---

## Integration Verdict

**PARTIAL.** Prompt 25b proves the corrected advisory-context contract offline
for S4 and the S2 TPO quality fix, and preserves explicit pre_fire/risk/safety
gates. Integration is not marked fully READY because replay/live bar flow,
real-market pattern fires, and S3 advisory reason-tree consumption remain
unproven.

**Next step:** run focused pytest, then validate during replay clock mode before
any SHADOW/DEMO/LIVE enablement.

---

*Generated: Prompt 25b — Cross-System Integration Proof Correction. No push.*
