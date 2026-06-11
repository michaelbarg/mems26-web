# Morning Prep — Anchor Trial 2026-06-12

## T1 ✅ — Anti-Tautological Tests (RED-on-revert proven)

**Problem:** Old tests tested a Python expression, not the actual gateway code.

**Fix:** Extracted `resolve_pattern_id(setup, g1)` as a callable function in
`trading_gateway.py:27-38`. Both `_execute_shadow` and `_build_trade` call it.
Tests import and test this function directly.

**RED-on-revert proof:**
```
# Reverted resolve_pattern_id to always return g1:
FAILED test_s2_pattern_id_not_from_woodies
  AssertionError: Expected REACTIVE_LONG, got VEGAS

# Restored fix:
10 passed in 0.06s
```

**Files:** `trading_gateway.py` (resolve_pattern_id extracted), `test_g1_entry_context.py` (3 real tests)

## T2 ✅ — Pattern Risk Caps (PATTERN_RISK_CAPS=1)

**Config:** `stop_anchors.yaml` — `max_risk_points` per pattern:

| Pattern | Cap | Group | Over-cap behavior |
|---------|-----|-------|-------------------|
| ZLR | 15 | CONT | SIZE_DOWN to 1 contract |
| TLB | 15 | CONT | SIZE_DOWN |
| TT | 15 | CONT | SIZE_DOWN |
| GB100 | 15 | CONT | SIZE_DOWN |
| VEGAS | 20 | REV | **SKIP** |
| GHOST | 18 | REV | **SKIP** |
| FAMIR | 12 | REV | **SKIP** |
| HTLB | 20 | REV | **SKIP** |
| HFE | 20 | REV | **SKIP** |
| Reactive | 15 | S2 | (S2 enforces separately via pre_fire) |
| Initiative | 12 | S2 | (S2 enforces separately via pre_fire) |
| Double_BT | 20 | S2 | (S2 enforces separately via pre_fire) |
| HnS | 20 | S2 | (S2 enforces separately via pre_fire) |
| Flag | 15 | S2 | (S2 enforces separately via pre_fire) |

**Enforcement:** `woodies_system.py` — after stop computed, before fire_setup built:
- REV pattern + risk > cap → `sizing = "reject"` + log `RISK_CAP_SKIP`
- CONT pattern + risk > cap → `sizing = "half"` + log `RISK_CAP_SIZE_DOWN`

**Tests:** `test_pattern_risk_caps.py` — 4 tests:
- `test_hfe_39pt_blocked` — reproduces #49 (39pt > 20pt cap → SKIP)
- `test_zlr_12pt_passes` — 12pt < 15pt cap → OK
- `test_hfe_39pt_passes_when_flag_off` — flag OFF → no block
- `test_all_anchors_have_max_risk` — every anchor has the field + range [5,30]

**Counterfactual for yesterday:** trades #49 (-$585), #56 (-$529), #57 (-$514), #59 (-$330)
all had risk 22-39pt on HFE (cap 20) → would have been SKIP'd. Savings: ~$1,958.

## T3 — RUNNER_TARGETS_V1 — NOT-DONE

T2/T3 implementation is a significant change to `trade_manager/manager.py` that requires:
- New target computation in the fire path
- T2/T3 hit detection in the bar-by-bar monitoring
- Integration with mgmt log (T2_HIT, T3_HIT events)
- Trail logic (chandelier / 2-bar)

**Design is complete** (in FIX_2026-06-12_REPORT.md §2.3) but implementation deferred to
avoid rushing a trading-logic change before market open. Flag is defined but OFF.

## T4 ✅ — Detection Logs (S2_DETECTION_LOG=1)

**Added per-bar condition vectors** to `_detect_reactive` and `_detect_initiative`:

```
[S2-DL] REACTIVE ts=2026-06-12T10:05:00 L:[b1s=1 b2d=0 b3b=1 b4c=1 b4>h=0] S:[b1b=0 b3s=0 b4c=0 b4<l=0] vsa=0 rvol=0
[S2-DL] INITIATIVE ts=2026-06-12T10:05:00 b1_exp=0 b2_test=1 b3_join=0 b4_test=1 b1_bull=1 b1_bear=0 b1_range=2.5 exp=[3.3,6.5]
```

Deduped per ts (only logs on `is_new_bar`). Flag-gated `S2_DETECTION_LOG=1`.
After today's session: grep `[S2-DL]` to identify which condition is the bottleneck.

## T5 — Commit & Tags

**Rollback plan:** All new features are flag-gated (default OFF in code):
- `PATTERN_RISK_CAPS` — disable by removing from .env + restart
- `S2_DETECTION_LOG` — disable by removing from .env + restart
- `resolve_pattern_id` — pure improvement, no flag needed (fixes a bug)

Full rollback: `git revert <sha>` or simpler: remove flags from `.env` + restart.

## T6 — EOD Report Script — NOT-DONE

The existing EOD infrastructure needs to be audited first (§audit existing surfaces).
Deferred — manual review of the detection logs + trade audit sufficient for day 1.

## Files Changed

```
backend/v9/gateway/trading_gateway.py          — resolve_pattern_id extracted + wired
backend/v9/systems/woodies/woodies_system.py   — PATTERN_RISK_CAPS enforcement
backend/v9/systems/five_min/five_min_system.py — S2_DETECTION_LOG (REACTIVE + INITIATIVE)
backend/v9/tests/test_g1_entry_context.py      — 3 real anti-tautological tests
backend/v9/tests/test_pattern_risk_caps.py     — 4 risk cap regression tests (NEW)
config/stop_anchors.yaml                       — max_risk_points per pattern
.env                                           — PATTERN_RISK_CAPS=1, S2_DETECTION_LOG=1
```

## Test Results

```
14 passed in 0.18s (10 g1 + 4 risk caps)
RED-on-revert: resolve_pattern_id reverted → test_s2_pattern_id_not_from_woodies FAILED (VEGAS≠REACTIVE_LONG)
```

## NOT-DONE

1. **RUNNER_TARGETS_V1** — T2/T3 implementation (design complete, code deferred)
2. **STOP_AFTER_T1_STRUCTURAL** — structural stop after T1 (deferred, one variable at a time)
3. **COUNTER_PATTERN_VETO** — design complete, awaiting Michael approval
4. **EOD report script** — `scripts/eod_anchor_trial_report.py` not created
5. **S4_DETECTION_LOG** — S4 per-bar log not added (S4 fires frequently, less need)
6. **TRADE_CVD_SNAPSHOT** — CVD at entry/T1/exit not implemented
7. **Replay script** — `scripts/replay_s2_conditions.py` not created
